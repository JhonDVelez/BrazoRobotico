"""
Compensadores matematicos para comandos del robot fisico.

El modulo mantiene ``RobotCompensator`` como fachada transparente para el
servicio serial y añade ``CartesianPidCompensator`` para el control cartesiano
realimentado que consume la cinematica validada en ``Codigos_test/p1.py``.

Conexiones:
    - RobotWorker usa ``RobotCompensator.process_data`` antes del envio serial.
    - KinematicsWorker usa ``CartesianPidCompensator`` para transformar
      telemetria fisica en comandos de servos mediante PID cartesiano.
"""

import math
import time

import numpy as np


class CartesianPidCompensator:
    """Controlador PID cartesiano con modelo cinematico del robot real.

    Encapsula la cinematica directa, pseudoinversa del Jacobiano, limites
    fisicos y memoria PID. No conoce el puerto serial ni emite señales; solo
    calcula el siguiente comando de servos a partir del objetivo cartesiano y
    la telemetria fisica actual.
    """

    _KP_AXES = np.array([1.38, 1.0, 1.38])
    _KI_AXES = np.array([0.627, 0.0, 0.8625])
    _KD_AXES = np.array([0.0759, 0.0, 0.0552])
    _LIMITS_DEG = [(-100.0, 100.0), (-90.0, 90.0),
                   (-130.0, 130.0), (-90.0, 120.0)]

    def __init__(self, links=None):
        """Inicializa el modelo cinematico y la memoria del PID.

        Args:
            links (list, optional): Longitudes ``[L1, L2, L3, L4, L5]`` en mm.
        """
        self._links = links or [155.0, 92.0, 111.0, 8.0, 150.0]
        self.reset()

    def reset(self):
        """Reinicia la memoria integral, derivativa y temporal del PID."""
        self._integral_error = np.zeros(3)
        self._previous_error = np.zeros(3)
        self._filtered_derivative = np.zeros(3)
        self._first_iteration = True
        self._previous_time = None

    def servo_to_joint_angles(self, positions: list) -> np.ndarray:
        """Convierte posiciones absolutas de servos a angulos articulares.

        Args:
            positions (list): Posiciones de servos en grados absolutos 0-300.

        Returns:
            np.ndarray: Angulos ``[q1, q2, q3, q4]`` en radianes.
        """
        return np.radians([
            positions[0] - 150.0,
            150.0 - positions[1],
            150.0 - positions[2],
            positions[4] - 150.0,
        ])

    def joint_to_servo_angles(self, q_rad: np.ndarray,
                              current_positions: list | None = None) -> list:
        """Convierte angulos articulares a comandos absolutos de servos.

        Args:
            q_rad (np.ndarray): Angulos ``[q1, q2, q3, q4]`` en radianes.
            current_positions (list | None): Estado actual para preservar
                muñeca rotacional y pinza, que no participan en el PID XYZ.

        Returns:
            list: Comando de 6 servos en grados absolutos 0-300.
        """
        q_deg = np.degrees(q_rad)
        servos = list(current_positions) if current_positions else [150.0] * 6
        servos[0] = q_deg[0] + 150.0
        servos[1] = 150.0 - q_deg[1]
        servos[2] = 150.0 - q_deg[2]
        servos[4] = q_deg[3] + 150.0
        return [max(0.0, min(300.0, float(value))) for value in servos]

    def forward_kinematics(self, q_rad: np.ndarray) -> np.ndarray:
        """Calcula la posicion cartesiana del efector final.

        Args:
            q_rad (np.ndarray): Angulos ``[q1, q2, q3, q4]`` en radianes.

        Returns:
            np.ndarray: Posicion cartesiana ``[x, y, z]`` en milimetros.
        """
        t1, t2, t3, t4 = q_rad
        l1, l2, l3, l4, l5 = self._links
        arg23 = t2 + t3
        arg234 = t2 + t3 + t4
        projection = (
            l4 * math.cos(arg23)
            + l3 * math.sin(arg23)
            + l2 * math.sin(t2)
            + l5 * math.sin(arg234)
        )
        px = math.cos(t1) * projection
        py = math.sin(t1) * projection
        pz = (
            l1
            + l3 * math.cos(arg23)
            - l4 * math.sin(arg23)
            + l2 * math.cos(t2)
            + l5 * math.cos(arg234)
        )
        return np.array([px, py, pz])

    def inverse_kinematics_step(self, q_rad: np.ndarray,
                                cartesian_velocity: np.ndarray) -> np.ndarray:
        """Calcula un incremento articular por pseudoinversa del Jacobiano.

        Args:
            q_rad (np.ndarray): Angulos articulares actuales en radianes.
            cartesian_velocity (np.ndarray): Accion de control ``[vx, vy, vz]``.

        Returns:
            np.ndarray: Incremento articular ``dq`` en radianes.
        """
        jacobian_inverse = np.linalg.pinv(self._jacobian(q_rad))
        return jacobian_inverse @ cartesian_velocity

    def compute_command(self, target_position: np.ndarray,
                        current_positions: list):
        """Calcula el siguiente comando PID hacia un objetivo cartesiano.

        Args:
            target_position (np.ndarray): Objetivo ``[x, y, z]`` en mm.
            current_positions (list): Telemetria actual de servos 0-300.

        Returns:
            tuple: ``(command, reached, current_position, error)`` donde
            ``command`` es una lista de 6 servos o ``None`` si ya llego.
        """
        now = time.time()
        dt = 0.01 if self._previous_time is None else now - self._previous_time
        dt = max(dt, 0.01)

        q_actual = self.servo_to_joint_angles(current_positions)
        current_position = self.forward_kinematics(q_actual)
        error = target_position - current_position

        if np.all(np.abs(error) < [3.0, 3.0, 5.0]):
            self._previous_time = now
            return None, True, current_position, error

        control = self._pid_control(error, current_position, dt)
        dq = self.inverse_kinematics_step(q_actual, control)
        q_next = self.apply_physical_limits(q_actual + dq)
        q_next[0] = math.atan2(target_position[1], target_position[0])

        self._previous_error = error.copy()
        self._previous_time = now
        command = self.joint_to_servo_angles(q_next, current_positions)
        return command, False, current_position, error

    def _pid_control(self, error: np.ndarray, current_position: np.ndarray,
                     dt: float) -> np.ndarray:
        """Calcula la accion PID cartesiana con anti-windup y soporte Z."""
        proportional = error * self._KP_AXES   
        dist_total = np.linalg.norm(error)   
        umbral = 1.0
        ALPHA_D = 0.25        

        if dist_total < umbral*2:
            self._integral_error *= 0.7
        else:
            self._integral_error += error * dt

        self._integral_error = np.clip(self._integral_error, -30.0, 30.0)

        integral = self._integral_error * self._KI_AXES

        if self._first_iteration:
            derivative = np.zeros(3)
            self._first_iteration = False
        else:
            raw_derivative = (error - self._previous_error) / dt
            self._filtered_derivative = (ALPHA_D * raw_derivative) + ((1 - ALPHA_D) * self._filtered_derivative)
            derivative = self._filtered_derivative * self._KD_AXES

        radius = np.sqrt(current_position[0] ** 2 + current_position[1] ** 2)
        gravity_support = (0.1373 * radius) - 16.066
        control = proportional + integral + derivative
        control[2] += gravity_support
        return control

    def apply_physical_limits(self, q_rad: np.ndarray) -> np.ndarray:
        """Satura cada articulacion segun los limites fisicos del robot."""
        limited = []
        for index, angle in enumerate(q_rad):
            angle_deg = math.degrees(angle)
            low, high = self._LIMITS_DEG[index]
            limited.append(math.radians(max(low, min(angle_deg, high))))
        return np.array(limited)

    def _jacobian(self, q_rad: np.ndarray) -> np.ndarray:
        """Calcula el Jacobiano analitico usado por la pseudoinversa."""
        t1, t2, t3, t4 = q_rad
        _, l2, l3, l4, l5 = self._links
        s1, c1 = math.sin(t1), math.cos(t1)
        s2, c2 = math.sin(t2), math.cos(t2)
        s23, c23 = math.sin(t2 + t3), math.cos(t2 + t3)
        s234, c234 = math.sin(t2 + t3 + t4), math.cos(t2 + t3 + t4)

        f = l4 * c23 + l3 * s23 + l2 * s2 + l5 * s234
        df_dt2 = -l4 * s23 + l3 * c23 + l2 * c2 + l5 * c234
        df_dt3 = -l4 * s23 + l3 * c23 + l5 * c234
        df_dt4 = l5 * c234
        dz_dt2 = -l3 * s23 - l4 * c23 - l2 * s2 - l5 * s234
        dz_dt3 = -l3 * s23 - l4 * c23 - l5 * s234
        dz_dt4 = -l5 * s234

        return np.array([
            [-s1 * f, c1 * df_dt2, c1 * df_dt3, c1 * df_dt4],
            [c1 * f, s1 * df_dt2, s1 * df_dt3, s1 * df_dt4],
            [0.0, dz_dt2, dz_dt3, dz_dt4],
        ])


class RobotCompensator(CartesianPidCompensator):
    """Compensador de comandos usado por el servicio serial del robot.

    Hereda las utilidades cinematicas para reutilizacion, pero ``process_data``
    permanece transparente: los modos sliders, pick-and-place y cinematica ya
    entregan comandos absolutos 0-300 al bus global.
    """

    def process_data(self, positions: list) -> list:
        """Retorna una copia de las posiciones sin alterar la funcionalidad.

        Args:
            positions (list): Lista de posiciones originales 0-300.

        Returns:
            list: Lista de posiciones para enviar al microcontrolador.
        """
        return positions.copy()
