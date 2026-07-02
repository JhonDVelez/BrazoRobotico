"""
Módulo que define el KinematicsWorker para el cálculo de cinemática.

Este módulo contiene la lógica para el cálculo de cinemática directa (CD) e
inversa (CI) de un brazo robótico, además de gestionar el control
realimentado mediante el uso de hilos (QThread).

Conexiones:
    - Emite `commands_ready` cuando se calcula un nuevo comando de posición.
    - Emite `error_occurred` en caso de fallos en el cálculo.
    - Se conecta con `RobotWorker` (indirectamente a través de señales) para
      recibir telemetría y enviar comandos.
"""

import time
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal, pyqtSlot
from src.services.robot.robot_compensator import CartesianPidCompensator


class KinematicsWorker(QThread):
    """
    Worker encargado exclusivamente del cálculo de cinemática y control.

    Esta clase implementa algoritmos de cinemática directa e inversa iterativa
    para controlar un brazo robótico de 4 grados de libertad (DOF) activos.

    Attributes:
        commands_ready (pyqtSignal): Señal que envía una lista de posiciones
            (float) para los servos del robot.
        error_occurred (pyqtSignal): Señal que envía un mensaje de error (str)
            en caso de fallas críticas.
    """
    commands_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self):
        """
        Inicializa el worker de cinemática con las dimensiones del robot.

        Define las longitudes de los eslabones y establece el estado inicial
        del sistema de control.
        """
        super().__init__()
        # Dimensiones de los eslabones (mm) - Valores originales
        self._L1, self._L2, self._L3, self._L4 = 155, 92, 111, 155
        self._cartesian_pid = CartesianPidCompensator()

        # Estado interno
        self._current_positions = [150.0] * 6
        self._target_pos = None
        self._target_waypoints = []
        self._waypoint_index = 0
        self._start_time = None
        self._prev_positions = list(self._current_positions)
        self._is_paused = False

    # --- Métodos Matemáticos (DH y Transformaciones) ---

    def _h_dh(self, H):
        """
        Extrae la rotación y traslación de una matriz de transformación homogénea.

        Args:
            H (np.ndarray): Matriz de transformación homogénea de 4x4.

        Returns:
            tuple: Contiene (R, vect_d, zero_array, scale) donde:
                - R (np.ndarray): Matriz de rotación 3x3.
                - vect_d (np.ndarray): Vector de traslación 3x1.
                - zero_array (np.ndarray): Array de ceros para compatibilidad.
                - scale (int): Factor de escala (siempre 1).
        """
        R = H[:3, :3]
        vect_d = H[:3, 3].reshape((3, 1))
        return R, vect_d, np.array([0, 0, 0]), 1

    def _hrx(self, theta):
        """
        Genera una matriz de rotación en el eje X.

        Args:
            theta (float): Ángulo de rotación en radianes.

        Returns:
            np.ndarray: Matriz de transformación de 4x4.
        """
        c, s = np.cos(theta), np.sin(theta)
        return np.array([[1, 0, 0, 0], [0, c, -s, 0], [0, s, c, 0], [0, 0, 0, 1]])

    def _hrz(self, theta):
        """
        Genera una matriz de rotación en el eje Z.

        Args:
            theta (float): Ángulo de rotación en radianes.

        Returns:
            np.ndarray: Matriz de transformación de 4x4.
        """
        c, s = np.cos(theta), np.sin(theta)
        return np.array([[c, -s, 0, 0], [s, c, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])

    def _htx(self, d):
        """
        Genera una matriz de traslación en el eje X.

        Args:
            d (float): Distancia de traslación.

        Returns:
            np.ndarray: Matriz de transformación de 4x4.
        """
        return np.array([[1, 0, 0, d], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])

    def _htz(self, d):
        """
        Genera una matriz de traslación en el eje Z.

        Args:
            d (float): Distancia de traslación.

        Returns:
            np.ndarray: Matriz de transformación de 4x4.
        """
        return np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, d], [0, 0, 0, 1]])

    def _t_matrices(self, t1, t2, t3, t4):
        """
        Calcula las matrices de transformación sucesivas para cada eslabón.

        Utiliza los parámetros DH (Denavit-Hartenberg) personalizados para el robot.

        Args:
            t1 (float): Ángulo de la articulación 1 (Base) en radianes.
            t2 (float): Ángulo de la articulación 2 (Hombro) en radianes.
            t3 (float): Ángulo de la articulación 3 (Codo) en radianes.
            t4 (float): Ángulo de la articulación 4 (Muñeca) en radianes.

        Returns:
            list: Lista de 5 matrices np.ndarray (4x4) desde la base hasta el efector final.
        """
        # A1: Base a Hombro
        A1 = self._hrz(t1 + np.pi) @ self._htz(self._L1) @ self._htx(0) @ self._hrx(np.pi/2)
        # A2: Hombro a Codo
        A2 = self._hrz(t2 + np.pi/2) @ self._htz(0) @ self._htx(self._L2) @ self._hrx(0)
        # A3: Codo a Muñeca
        A3 = self._hrz(t3) @ self._htz(0) @ self._htx(self._L3) @ self._hrx(0)
        # A4: Muñeca a Pinza
        A4 = self._hrz(t4) @ self._htz(0) @ self._htx(self._L4) @ self._hrx(0)

        T01 = A1
        T02 = T01 @ A2
        T03 = T02 @ A3
        T04 = T03 @ A4
        return [np.identity(4), T01, T02, T03, T04]

    def cd(self, t1, t2, t3, t4):
        """
        Calcula la cinemática directa para obtener la posición del efector final.

        Args:
            t1 (float): Ángulo articular 1 en radianes.
            t2 (float): Ángulo articular 2 en radianes.
            t3 (float): Ángulo articular 3 en radianes.
            t4 (float): Ángulo articular 4 en radianes.

        Returns:
            np.ndarray: Vector de posición [x, y, z] en milímetros.
        """
        return self._cartesian_pid.forward_kinematics(
            np.array([t1, t2, t3, t4], dtype=float)
        )

    def ci(self, px, py, pz, phi):
        """
        Calcula la cinemática inversa iterativa para alcanzar una posición.

        Utiliza el método de Newton-Raphson con el Jacobiano analítico para
        encontrar los ángulos articulares que minimizan el error de posición.

        Args:
            px (float): Posición deseada en X (mm).
            py (float): Posición deseada en Y (mm).
            pz (float): Posición deseada en Z (mm).
            phi (float): Ángulo de aproximación inicial para la muñeca (grados).

        Returns:
            tuple: Contiene (q, error) donde:
                - q (np.ndarray): Vector de ángulos articulares 4x1 en radianes.
                - error (np.ndarray): Vector de error de posición residual 3x1.
        """
        q = np.deg2rad(np.array([40, 60, 90, phi], dtype=float)).reshape((4, 1))
        lambda_val, tol, max_iter = 0.5, 0.1, 100
        P_deseada = np.array([px, py, pz], dtype=float)
        for _ in range(max_iter):
            P_actual = self.cd(q[0, 0], q[1, 0], q[2, 0], q[3, 0])
            error = P_deseada - P_actual
            if np.linalg.norm(error) < tol:
                break
            dq = self._cartesian_pid.inverse_kinematics_step(q.flatten(), error)
            q = self._cartesian_pid.apply_physical_limits(
                q.flatten() + lambda_val * dq
            ).reshape((4, 1))
        return q, error.reshape((3, 1))

    def _jacobiano_analitico(self, q_flat):
        """
        Calcula el Jacobiano analítico del robot para la posición actual.

        El Jacobiano relaciona las velocidades articulares con las velocidades
        lineales del efector final (Jv).

        Args:
            q_flat (array-like): Ángulos articulares actuales [t1, t2, t3, t4] en radianes.

        Returns:
            np.ndarray: Matriz Jacobiana de 3x4.
        """
        t1, t2, t3, t4 = q_flat
        T_list = self._t_matrices(t1, t2, t3, t4)
        Pn = T_list[-1][:3, 3].reshape((3, 1))
        Jv = np.zeros((3, 4))
        for j in range(4):
            T_prev = T_list[j]
            P_prev = T_prev[:3, 3].reshape((3, 1))
            Z_prev = T_prev[:3, 2].reshape((3, 1))
            vector_d = Pn - P_prev
            # Jv_j = z_{j-1} x (P_n - P_{j-1}) para articulaciones de revolucion
            Jv[:, j] = np.cross(Z_prev.flatten(), vector_d.flatten())
        return Jv

    # --- Gestion de Control Realimentado ---

    @pyqtSlot(list, list)
    def update_sensor_data(self, positions, temp_data=None):
        """
        Recibe telemetría del robot y recalcula el siguiente comando de control.

        Este método implementa un esquema de control incremental (Damped Least Squares)
        para mover el robot hacia el objetivo definido en `set_target`. También
        incluye detección de bloqueos mecánicos.

        Args:
            positions (list): Posiciones actuales de los servos (0-300 grados).
            temp_data (list, optional): Datos de temperatura de los motores.
        """
        self._current_positions = list(positions)
        if self._target_pos is None or self._is_paused:
            return

        self._prev_positions = list(self._current_positions)

        active_target = self._target_waypoints[self._waypoint_index]
        command, reached, _, _ = self._cartesian_pid.compute_command(
            active_target, self._current_positions
        )

        if reached:
            self._waypoint_index += 1
            self._cartesian_pid.reset()
            if self._waypoint_index >= len(self._target_waypoints):
                self._target_pos = None
                self._target_waypoints = []
                return
            active_target = self._target_waypoints[self._waypoint_index]
            command, reached, _, _ = self._cartesian_pid.compute_command(
                active_target, self._current_positions
            )
            if reached:
                return

        if command is not None:
            self.commands_ready.emit(command)

    # --- Getters / Setters ---

    def set_target(self, px, py, pz):
        """
        Define un nuevo objetivo cartesiano para el robot.

        Args:
            px (float): Objetivo X en mm.
            py (float): Objetivo Y en mm.
            pz (float): Objetivo Z en mm.
        """
        if px is None or py is None or pz is None:
            self._target_pos = None
            self._target_waypoints = []
        else:
            self._target_pos = np.array([px, py, pz], dtype=float)
            self._target_waypoints = self._build_target_waypoints(px, py, pz)
            self._waypoint_index = 0
            self._cartesian_pid.reset()
            self._start_time = time.time()
            self._prev_positions = list(self._current_positions)
            self.update_sensor_data(self._current_positions)

    def _build_target_waypoints(self, px, py, pz):
        """
        Construye una secuencia desacoplada de movimiento X, Y y Z.

        Args:
            px (float): Objetivo final X en mm.
            py (float): Objetivo final Y en mm.
            pz (float): Objetivo final Z en mm.

        Returns:
            list: Waypoints cartesianos para elevar, desplazar y descender.
        """
        current_q = self._cartesian_pid.servo_to_joint_angles(
            self._current_positions
        )
        current_xyz = self._cartesian_pid.forward_kinematics(current_q)
        safe_z = pz + 30.0
        return [
            np.array([current_xyz[0], current_xyz[1], safe_z], dtype=float),
            np.array([px, current_xyz[1], safe_z], dtype=float),
            np.array([px, py, safe_z], dtype=float),
            np.array([px, py, pz], dtype=float),
        ]

    def set_paused(self, paused: bool):
        """
        Pausa o reanuda el proceso de control.

        Args:
            paused (bool): True para pausar, False para reanudar.
        """
        self._is_paused = paused

    def get_current_positions(self):
        """
        Obtiene las últimas posiciones conocidas de los servos.

        Returns:
            list: Lista de 6 flotantes (grados).
        """
        return list(self._current_positions)

    def get_target_pos(self):
        """
        Obtiene el objetivo cartesiano actual.

        Returns:
            np.ndarray: Vector 3x1 o None si no hay objetivo.
        """
        return self._target_pos.copy() if self._target_pos is not None else None
