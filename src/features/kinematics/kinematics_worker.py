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

import math
import time
import numpy as np
from PyQt6.QtCore import QThread, QTimer, pyqtSignal, pyqtSlot
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
    pid_iteration = pyqtSignal(int, list, list)

    def __init__(self):
        """
        Inicializa el worker de cinemática con las dimensiones del robot.

        Define las longitudes de los eslabones y establece el estado inicial
        del sistema de control.
        """
        super().__init__()
        self._links = [155.0, 92.0, 111.0, 8.0, 150.0]

        # Estado interno
        self._current_positions = [150.0] * 6
        self._target_pos = None
        self._target_waypoints = []
        self._waypoint_index = 0
        self._start_time = None
        self._prev_positions = list(self._current_positions)
        self._is_paused = False

        # --- PID control state (initiative) ---
        self._pid_active = False
        self._pid_target = None
        self._pid_limites = None
        self._pid_on_done = None
        self._pid_error_acumulado = np.zeros(3)
        self._pid_error_anterior = np.zeros(3)
        self._pid_primera_iteracion = True
        self._pid_contador_estabilidad = 0
        self._pid_paused = False

        # --- Prueba_controlv11: stability counter, dead band, tolerances ---
        self._stability_count = 0
        self._stability_required = 10
        self._tolerances = np.array([5.0, 5.0, 5.0])
        self._dead_band_threshold_deg = 0.5
        self._umbral_mm = 1.5
        self._integral_limit = 35.0
        self._integral_error = np.zeros(3)
        self._previous_error = np.zeros(3)
        self._first_iteration = True

    # --- Cinematica directa (Prueba_controlv11) ---

    @staticmethod
    def _cinematica_directa(q, L=None):
        if L is None:
            L = [155.0, 92.0, 111.0, 8.0, 150.0]
        t1, t2, t3, t4 = q
        L1, L2, L3, L4, L5 = L
        arg23 = t2 + t3
        arg234 = t2 + t3 + t4
        projection = (L4 * math.cos(arg23) + L3 * math.sin(arg23) +
                      L2 * math.sin(t2) + L5 * math.sin(arg234))
        px = math.cos(t1) * projection
        py = math.sin(t1) * projection
        pz = L1 + L3 * math.cos(arg23) - L4 * math.sin(arg23) + L2 * math.cos(t2) + L5 * math.cos(arg234)
        return np.array([px, py, pz])

    @staticmethod
    def _calcular_pseudoinversa(q, L=None):
        if L is None:
            L = [155.0, 92.0, 111.0, 8.0, 150.0]
        t1, t2, t3, t4 = q
        L1, L2, L3, L4, L5 = L
        s1, c1 = math.sin(t1), math.cos(t1)
        s2, c2 = math.sin(t2), math.cos(t2)
        s23, c23 = math.sin(t2 + t3), math.cos(t2 + t3)
        s234, c234 = math.sin(t2 + t3 + t4), math.cos(t2 + t3 + t4)
        f = L4 * c23 + L3 * s23 + L2 * s2 + L5 * s234
        df_dt2 = -L4 * s23 + L3 * c23 + L2 * c2 + L5 * c234
        df_dt3 = -L4 * s23 + L3 * c23 + L5 * c234
        df_dt4 = L5 * c234
        dz_dt2 = -L3 * s23 - L4 * c23 - L2 * s2 - L5 * s234
        dz_dt3 = -L3 * s23 - L4 * c23 - L5 * s234
        dz_dt4 = -L5 * s234
        J = np.array([
            [-s1 * f,  c1 * df_dt2,  c1 * df_dt3,  c1 * df_dt4],
            [ c1 * f,  s1 * df_dt2,  s1 * df_dt3,  s1 * df_dt4],
            [ 0,       dz_dt2,       dz_dt3,       dz_dt4]
        ])
        return np.linalg.pinv(J)

    def cd(self, t1, t2, t3, t4):
        return self._cinematica_directa(np.array([t1, t2, t3, t4], dtype=float))

    def ci(self, px, py, pz, max_iter=100, tol=1.0, gain=0.5):
        """
        Calcula cinematica inversa iterativa (Newton-Raphson) para un objetivo cartesiano.

        Usa la pseudoinversa del Jacobiano para converger desde el origen
        hasta las coordenadas objetivo. Fija q1 directamente de atan2(py, px).

        Args:
            px (float): Coordenada X objetivo en mm.
            py (float): Coordenada Y objetivo en mm.
            pz (float): Coordenada Z objetivo en mm.
            max_iter (int): Maximo de iteraciones.
            tol (float): Tolerancia de convergencia en mm.
            gain (float): Factor de amortiguacion (0-1) para estabilidad.

        Returns:
            np.ndarray: Angulos articulares [q1, q2, q3, q4] en radianes.
        """
        q = np.zeros(4, dtype=float)
        target = np.array([px, py, pz], dtype=float)

        for _ in range(max_iter):
            current_xyz = self._cinematica_directa(q)
            error = target - current_xyz

            if np.linalg.norm(error) < tol:
                break

            J_inv = self._calcular_pseudoinversa(q)
            dq = J_inv @ error
            q = q + dq * gain
            q = CartesianPidCompensator.apply_physical_limits(q)
            q[0] = math.atan2(py, px)

        return q

    def _apply_dead_band(self, dq_rad):
        """
        Compensa la banda muerta de los servomotores incrementando
        las ordenes pequeñas por encima del umbral.
        """
        dq_deg = np.degrees(dq_rad)
        for j in range(len(dq_deg)):
            if 0 < abs(dq_deg[j]) < self._dead_band_threshold_deg:
                dq_deg[j] += math.copysign(self._dead_band_threshold_deg, dq_deg[j])
        return np.radians(dq_deg)

    # --- Comunicacion de comandos al bus del sistema ---

    def _send_servo_command(self, q_deg_list):
        servo_positions = CartesianPidCompensator.angulos_robotang(*q_deg_list)
        self.commands_ready.emit(servo_positions)

    # --- Control PID cartesiano iniciativa (timer-driven) ---

    def _init_pid_control(self, tx, ty, tz, limites_deg, on_done=None):
        self._pid_target = np.array([tx, ty, tz], dtype=float)
        self._pid_limites = limites_deg
        self._pid_on_done = on_done
        self._pid_error_acumulado = np.zeros(3)
        self._pid_error_anterior = np.zeros(3)
        self._pid_primera_iteracion = True
        self._pid_contador_estabilidad = 0
        self._pid_iteracion = 0
        self._pid_active = True
        QTimer.singleShot(0, self._pid_tick)

    def _pid_tick(self):
        if not self._pid_active or self._pid_paused:
            return

        q_reales_deg = np.array(
            CartesianPidCompensator.robotang_angulos(*self._current_positions))
        q_actual_rad = np.radians([
            q_reales_deg[0], q_reales_deg[1],
            q_reales_deg[2], q_reales_deg[4]])
        p_actual = self._cinematica_directa(q_actual_rad)

        self._pid_iteracion += 1
        self.pid_iteration.emit(
            self._pid_iteracion, p_actual.tolist(), self._pid_target.tolist())

        error_actual = self._pid_target - p_actual
        dist_total = np.linalg.norm(error_actual)

        TOLERANCIAS = [5.0, 5.0, 5.0]
        error_abs = np.abs(error_actual)
        if (error_abs[0] < TOLERANCIAS[0] and
            error_abs[1] < TOLERANCIAS[1] and
            error_abs[2] < TOLERANCIAS[2]):
            self._pid_contador_estabilidad += 1
            self._pid_error_anterior = error_actual.copy()
            if self._pid_contador_estabilidad >= 10:
                self._pid_active = False
                print("PID converged!")
                if self._pid_on_done:
                    self._pid_on_done()
                return
            QTimer.singleShot(10, self._pid_tick)
            return
        else:
            self._pid_contador_estabilidad = 0

        if self._pid_contador_estabilidad > 0:
            QTimer.singleShot(10, self._pid_tick)
            return

        KP_EJES = np.array([1.5, 1.0, 1.38])
        KI_EJES = np.array([0.9375, 0.0, 0.69])
        KD_EJES = np.array([0.06, 0.0, 0.069])

        P = error_actual * KP_EJES

        umbral_mm = 1.5
        if dist_total < umbral_mm * 2:
            self._pid_error_acumulado *= 0.7
        else:
            self._pid_error_acumulado += error_actual * 0.01

        self._pid_error_acumulado = np.clip(
            self._pid_error_acumulado, -35, 35)
        I = self._pid_error_acumulado * KI_EJES

        if self._pid_primera_iteracion:
            D = np.zeros(3)
            self._pid_primera_iteracion = False
        else:
            d_cruda = (error_actual - self._pid_error_anterior) / 0.01
            D = d_cruda * KD_EJES

        v_control = P + I + D
        self._pid_error_anterior = error_actual.copy()

        J_inv = self._calcular_pseudoinversa(q_actual_rad)
        dq = J_inv @ v_control

        dq_deg = np.degrees(dq)
        umbral_motor = 0.5
        for j in range(len(dq_deg)):
            if 0 < abs(dq_deg[j]) < umbral_motor:
                dq_deg[j] += np.sign(dq_deg[j]) * umbral_motor
        dq = np.radians(dq_deg)

        q_next_rad = CartesianPidCompensator.apply_physical_limits(
            q_actual_rad + dq, self._pid_limites)
        q_next_rad[0] = math.atan2(
            self._pid_target[1], self._pid_target[0])
        q_out_deg = np.degrees(q_next_rad)
        q_final = [q_out_deg[0], q_out_deg[1], q_out_deg[2],
                   0, q_out_deg[3], -80]
        self._send_servo_command(q_final)

        QTimer.singleShot(10, self._pid_tick)

    # --- Secuencia de movimiento completa (home + target) ---

    def execute_target(self, tx, ty, tz):
        self._tx_target = tx
        self._ty_target = ty
        self._tz_target = tz

        home_servos = CartesianPidCompensator.angulos_robotang(
            0, -45, 120, 0, 30, 0)
        self.commands_ready.emit(home_servos)
        QTimer.singleShot(2500, self._start_home_pid)

    def _start_home_pid(self):
        from .coordinate_correction import corregir_xy, corregir_z
        tx_home, ty_home, tz_home = 185, 0, 170
        tz_home = corregir_z(tx_home, ty_home, tz_home)
        tx_home, ty_home = corregir_xy(tx_home, ty_home)
        limites_home = [(10, -10), (-40, -90), (0, 130), (-30, 120)]
        self._init_pid_control(
            tx_home, ty_home, tz_home, limites_home,
            self._go_to_final_target)

    def _go_to_final_target(self):
        limites = [(-100, 100), (-90, 90), (-130, 130), (-90, 120)]
        self._init_pid_control(
            self._tx_target, self._ty_target, self._tz_target,
            limites, None)

    # --- Gestion de Control Realimentado ---

    @pyqtSlot(list, list)
    def update_sensor_data(self, positions, temp_data=None):
        """
        Recibe telemetría del robot y recalcula el siguiente comando de control.

        Implementa el esquema PID cartesiano con anti-windup, banda muerta,
        y contador de estabilidad, segun la logica de Prueba_controlv11.

        Args:
            positions (list): Posiciones actuales de los servos (0-300 grados).
            temp_data (list, optional): Datos de temperatura de los motores.
        """
        self._current_positions = list(positions)
        if self._target_pos is None or self._is_paused:
            return

        self._prev_positions = list(self._current_positions)
        active_target = self._target_waypoints[self._waypoint_index]

        # --- Un paso del control PID cartesiano (Prueba_controlv11) ---
        q_reales_deg = np.array(
            CartesianPidCompensator.robotang_angulos(*self._current_positions))
        q_actual = np.radians([
            q_reales_deg[0], q_reales_deg[1],
            q_reales_deg[2], q_reales_deg[4]])
        current_pos = self._cinematica_directa(q_actual)
        error = active_target - current_pos
        dist = np.linalg.norm(error)

        # Comprobacion de tolerancias con contador de estabilidad
        error_abs = np.abs(error)
        if (error_abs[0] < self._tolerances[0] and
            error_abs[1] < self._tolerances[1] and
            error_abs[2] < self._tolerances[2]):

            self._stability_count += 1
        else:
            self._stability_count = 0

        # Si se alcanzaron las iteraciones requeridas de estabilidad -> waypoint completado
        if self._stability_count >= self._stability_required:
            self._stability_count = 0
            self._integral_error = np.zeros(3)
            self._previous_error = np.zeros(3)
            self._first_iteration = True
            self._waypoint_index += 1
            if self._waypoint_index >= len(self._target_waypoints):
                self._target_pos = None
                self._target_waypoints = []
                return
            return

        # Si estamos dentro de tolerancia pero aun no se cumple la estabilidad, no enviar comando
        if self._stability_count > 0:
            return

        # --- Accion PID con anti-windup ---
        dt = 0.01
        KP = np.array([1.5, 1.0, 1.38])
        KI = np.array([0.9375, 0.0, 0.69])
        KD = np.array([0.06, 0.0, 0.069])

        P = error * KP

        if dist < self._umbral_mm * 2:
            self._integral_error *= 0.7
        else:
            self._integral_error += error * dt

        self._integral_error = np.clip(self._integral_error, -self._integral_limit, self._integral_limit)
        I = self._integral_error * KI

        if self._first_iteration:
            D = np.zeros(3)
            self._first_iteration = False
        else:
            d_error = (error - self._previous_error) / dt
            D = d_error * KD

        v_control = P + I + D
        self._previous_error = error.copy()

        # Inversion cinematica mediante pseudoinversa del Jacobiano (Prueba_controlv11)
        J_inv = self._calcular_pseudoinversa(q_actual)
        dq = J_inv @ v_control

        # Compensacion de banda muerta de servomotores
        dq = self._apply_dead_band(dq)

        # Limites fisicos y fijacion directa de q1
        q_next = CartesianPidCompensator.apply_physical_limits(q_actual + dq)
        q_next[0] = math.atan2(active_target[1], active_target[0])

        # Conversion a comando de servos
        q_out_deg = np.degrees(q_next)
        command = CartesianPidCompensator.angulos_robotang(
            q_out_deg[0], q_out_deg[1], q_out_deg[2], 0, q_out_deg[3], -80)
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
            self._stability_count = 0
        else:
            self._target_pos = np.array([px, py, pz], dtype=float)
            self._target_waypoints = self._build_target_waypoints(px, py, pz)
            self._waypoint_index = 0
            self._stability_count = 0
            self._integral_error = np.zeros(3)
            self._previous_error = np.zeros(3)
            self._first_iteration = True
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
        q_reales_deg = np.array(
            CartesianPidCompensator.robotang_angulos(*self._current_positions))
        current_q = np.radians([
            q_reales_deg[0], q_reales_deg[1],
            q_reales_deg[2], q_reales_deg[4]])
        current_xyz = self._cinematica_directa(current_q)
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

    def pause_pid(self):
        """
        Pausa el lazo PID cartesiano de forma externa (ej. cambio a modo sliders).

        El estado del PID se conserva para poder reanudarse despues.
        """
        self._pid_paused = True

    def resume_pid(self):
        """
        Reanuda el lazo PID cartesiano si hay un objetivo activo.

        Solo programa el siguiente tick si `_pid_target` esta definido,
        permitiendo que el control continue desde donde se pauso.
        """
        self._pid_paused = False
        if self._pid_target is not None:
            QTimer.singleShot(0, self._pid_tick)

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
