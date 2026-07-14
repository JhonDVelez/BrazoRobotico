"""
Módulo que define el KinematicsWorker para el cálculo de cinemática.

Este módulo contiene la lógica para el cálculo de cinemática directa (CD) e
inversa (CI) de un brazo robótico, además de gestionar el control
realimentado mediante una máquina de estados ejecutándose de forma
constante a 100 Hz dentro del hilo (QThread).

Conexiones:
    - Emite `commands_ready` cuando se calcula un nuevo comando de posición.
    - Emite `pid_iteration` en cada paso para el graficado cartesiano.
    - Emite `control_finished` al concluir la secuencia (rehabilita la UI).
    - Lee la telemetría del RobotWorker por polling (variables compartidas
      bajo cerrojo), evitando dependencias del event loop del hilo.
"""

import math
import time
import threading
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal
from src.services.robot.robot_compensator import CartesianPidCompensator


class KinematicsWorker(QThread):
    """
    Worker encargado exclusivamente del cálculo de cinemática y control.

    Esta clase implementa algoritmos de cinemática directa e inversa iterativa
    para controlar un brazo robótico de 4 grados de libertad (DOF) activos,
    gobernado por una máquina de estados a 100 Hz.

    Attributes:
        commands_ready (pyqtSignal): Señal que envía una lista de posiciones
            (float) para los servos del robot.
        error_occurred (pyqtSignal): Señal que envía un mensaje de error (str).
        pid_iteration (pyqtSignal): Señal que reporta (iter, actual, target).
        control_finished (pyqtSignal): Señal que indica fin de secuencia PID.
    """
    commands_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    pid_iteration = pyqtSignal(int, list, list)
    control_finished = pyqtSignal()

    STATE_IDLE = "idle"
    STATE_PHYSICAL_HOMING = "physical_homing"
    STATE_PID_HOMING = "pid_homing"
    STATE_PID_TARGET = "pid_target"

    def __init__(self):
        """
        Inicializa el worker de cinemática con las dimensiones del robot.

        Define las longitudes de los eslabones y establece el estado inicial
        del sistema de control (máquina de estados a 100 Hz).
        """
        super().__init__()
        self._links = [155.0, 92.0, 111.0, 8.0, 150.0]

        # Estado interno del lazo de control
        self._current_positions = [150.0] * 6
        self._last_commanded_positions = list(self._current_positions)
        self._has_real_telemetry = False
        self._target_pos = None

        # --- Máquina de estados (100 Hz) ---
        self._state = self.STATE_IDLE
        self._paused = False
        self._running = True
        self._robot_worker = None
        self._last_seen_telemetry_version = -1
        self._new_telemetry = False
        self._state_deadline = 0.0
        self._sequence_on_done = None

        # Objetivos de la secuencia
        self._tx_target = 0.0
        self._ty_target = 0.0
        self._tz_target = 0.0
        self._home_target = np.array([185.0, 0.0, 170.0], dtype=float)
        self._final_target = np.array([0.0, 0.0, 0.0], dtype=float)
        self._home_limits = [(-10, 10), (-90, -40), (0, 130), (-30, 120)]
        self._target_limits = [(-100, 100), (-90, 90), (-130, 130), (-90, 120)]

        # --- Estado del PID cartesiano ---
        self._pid_iteracion = -1
        self._pid_contador_estabilidad = 0
        self._pid_error_acumulado = np.zeros(3)
        self._pid_error_anterior = np.zeros(3)
        self._pid_primera_iteracion = True
        self._dead_band_threshold_deg = 0.5
        self._go_to_target_after_home = True

        # Cerrojo para variables compartidas entre el hilo y la UI
        self._lock = threading.Lock()

    # --- Cinemática directa ---

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
        Calcula cinemática inversa iterativa (Newton-Raphson) para un objetivo.

        Args:
            px, py, pz (float): Coordenadas objetivo en mm.
            max_iter (int): Máximo de iteraciones.
            tol (float): Tolerancia de convergencia en mm.
            gain (float): Factor de amortiguación (0-1).

        Returns:
            np.ndarray: Ángulos articulares [q1, q2, q3, q4] en radianes.
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
        las órdenes pequeñas por encima del umbral.
        """
        dq_deg = np.degrees(dq_rad)
        for j in range(len(dq_deg)):
            if 0 < abs(dq_deg[j]) < self._dead_band_threshold_deg:
                dq_deg[j] += math.copysign(self._dead_band_threshold_deg, dq_deg[j])
        return np.radians(dq_deg)

    # --- Comunicación de comandos al bus del sistema ---

    def _emit_servo_positions(self, servo_positions):
        self._last_commanded_positions = list(servo_positions)
        self.commands_ready.emit(servo_positions)

    def _send_servo_command(self, q_deg_list):
        servo_positions = CartesianPidCompensator.angulos_robotang(*q_deg_list)
        rounded = [round(p, 1) for p in servo_positions]
        print(f"[CMD] servo_positions={rounded}")
        self._emit_servo_positions(servo_positions)

    # --- Bucle principal (máquina de estados a 100 Hz) ---

    def run(self):
        """
        Bucle del hilo: sincroniza telemetría y ejecuta la máquina de
        estados a ~100 Hz (10 ms) de forma ininterrumpida.
        """
        while self._running:
            self._sync_telemetry()
            if not self._paused:
                self._state_machine_step()
            time.sleep(0.01)

    def _sync_telemetry(self):
        """
        Obtiene la telemetría más reciente del RobotWorker por polling.

        Solo marca datos nuevos cuando el contador de telemetría avanza,
        de modo que el PID ejecuta un paso por cada trama física recibida.
        """
        if self._robot_worker is None:
            return
        version = self._robot_worker.get_telemetry_counter()
        if version == self._last_seen_telemetry_version:
            return
        self._last_seen_telemetry_version = version

        pos = self._robot_worker.get_last_positions_locked()
        temps = self._robot_worker.get_last_temperatures_locked()
        if not any(p is not None for p in pos[:4]):
            return

        with self._lock:
            self._current_positions = list(pos)
            self._has_real_telemetry = True
            self._new_telemetry = True

    def _state_machine_step(self):
        """Despacho de la máquina de estados según el estado actual."""
        with self._lock:
            state = self._state
            has_tel = self._has_real_telemetry
            new_tel = self._new_telemetry
            home_t = self._home_target
            home_l = self._home_limits
            final_t = self._final_target
            final_l = self._target_limits

        if state == self.STATE_IDLE:
            return
        if not has_tel:
            return

        if state == self.STATE_PHYSICAL_HOMING:
            if time.time() >= self._state_deadline:
                self._enter_pid_home()
            return

        if not new_tel:
            return
        with self._lock:
            self._new_telemetry = False

        if state == self.STATE_PID_HOMING:
            if self._pid_step(home_t, home_l):
                if self._go_to_target_after_home:
                    self._enter_pid_target()
                else:
                    self._finish_sequence()
        elif state == self.STATE_PID_TARGET:
            if self._pid_step(final_t, final_l):
                self._finish_sequence()

    # --- Transiciones de estado ---

    def _enter_physical_home(self):
        """Envía el home angular directo y espera 2.5 s en segundo plano."""
        self._state = self.STATE_PHYSICAL_HOMING
        home_servos = CartesianPidCompensator.angulos_robotang(
            0, -45, 120, 0, 30, 0)
        self._emit_servo_positions(home_servos)
        self._state_deadline = time.time() + 2.5

    def _enter_pid_home(self):
        """Inicia el control PID hacia el Home Cartesiano [185, 0, 170]."""
        self._state = self.STATE_PID_HOMING
        from .coordinate_correction import corregir_xy, corregir_z
        tx_home, ty_home, tz_home = 185, 0, 170
        tz_home = corregir_z(tx_home, ty_home, tz_home)
        tx_home, ty_home = corregir_xy(tx_home, ty_home)
        self._home_target = np.array([tx_home, ty_home, tz_home], dtype=float)
        self._home_limits = [(-10, 10), (-90, -40), (0, 130), (-30, 120)]
        self._reset_pid_state()

    def _enter_pid_target(self):
        """Transición automática al control PID hacia el destino del usuario."""
        self._state = self.STATE_PID_TARGET
        self._final_target = np.array(
            [self._tx_target, self._ty_target, self._tz_target], dtype=float)
        self._target_limits = [(-100, 100), (-90, 90), (-130, 130), (-90, 120)]
        self._reset_pid_state()

    def _finish_sequence(self):
        """Concluye la secuencia: vuelve a IDLE y rehabilita la UI."""
        self._state = self.STATE_IDLE
        cb = self._sequence_on_done
        self._sequence_on_done = None
        self.control_finished.emit()
        if cb is not None:
            cb()

    def _reset_pid_state(self):
        """Reinicia los acumuladores del PID para una fase nueva."""
        self._pid_error_acumulado = np.zeros(3)
        self._pid_error_anterior = np.zeros(3)
        self._pid_primera_iteracion = True
        self._pid_contador_estabilidad = 0
        self._pid_iteracion = -1

    # --- Paso de control PID cartesiano ---

    def _pid_step(self, target, limits):
        """
        Ejecuta un paso del PID cartesiano hacia `target`.

        Args:
            target (np.ndarray): Objetivo cartesiano [x, y, z] en mm.
            limits (list): Límites físicos por articulación.

        Returns:
            bool: True si se alcanzó la estabilidad (fin de fase).
        """
        with self._lock:
            q_reales_deg = np.array(
                CartesianPidCompensator.robotang_angulos(*self._current_positions))
        q_actual_rad = np.radians([
            q_reales_deg[0], q_reales_deg[1],
            q_reales_deg[2], q_reales_deg[4]])
        p_actual = self._cinematica_directa(q_actual_rad)

        self._pid_iteracion += 1
        self.pid_iteration.emit(
            self._pid_iteracion, p_actual.tolist(), target.tolist())

        error_actual = target - p_actual
        dist_total = np.linalg.norm(error_actual)

        if self._pid_iteracion % 100 == 0:
            print(f"[PID] tick {self._pid_iteracion} "
                  f"actual=({p_actual[0]:.1f}, {p_actual[1]:.1f}, {p_actual[2]:.1f}) "
                  f"target=({target[0]:.1f}, {target[1]:.1f}, {target[2]:.1f}) "
                  f"error=({error_actual[0]:.1f}, {error_actual[1]:.1f}, {error_actual[2]:.1f}) "
                  f"dist={dist_total:.2f}")

        TOLERANCIAS = [5.0, 5.0, 5.0]
        error_abs = np.abs(error_actual)
        if (error_abs[0] < TOLERANCIAS[0] and
                error_abs[1] < TOLERANCIAS[1] and
                error_abs[2] < TOLERANCIAS[2]):
            self._pid_contador_estabilidad += 1
            self._pid_error_anterior = error_actual.copy()
            if self._pid_contador_estabilidad >= 10:
                print(f"[PID] CONVERGIO en iteracion {self._pid_iteracion}!")
                return True
            return False
        else:
            if self._pid_contador_estabilidad > 0:
                print(f"[PID] perdio tolerancia estabilidad={self._pid_contador_estabilidad}")
            self._pid_contador_estabilidad = 0

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
            q_actual_rad + dq, limits)
        q_next_rad[0] = math.atan2(target[1], target[0])
        q_out_deg = np.degrees(q_next_rad)
        q_final = [q_out_deg[0], q_out_deg[1], q_out_deg[2],
                   0, q_out_deg[3], -80]
        print(f"[PID] servo_cmd q_out_deg=({q_out_deg[0]:.1f}, {q_out_deg[1]:.1f}, "
              f"{q_out_deg[2]:.1f}, {q_out_deg[3]:.1f})")
        self._send_servo_command(q_final)
        return False

    # --- API de secuencia (invocada desde el controlador / UI) ---

    def set_robot_worker(self, robot_worker):
        """Inyecta la referencia al RobotWorker para el polling de telemetría."""
        self._robot_worker = robot_worker

    def start_full_sequence(self, tx, ty, tz, on_done=None):
        """
        Secuencia completa al entrar a modo Cartesiano:
        home físico (2.5 s) -> PID home -> PID target(final).
        """
        self._go_to_target_after_home = True
        self._tx_target = tx
        self._ty_target = ty
        self._tz_target = tz
        self._target_pos = np.array([tx, ty, tz], dtype=float)
        self._sequence_on_done = on_done
        self._pid_stop()
        self._enter_physical_home()

    def start_target_only(self, tx, ty, tz):
        """
        Mover al destino del usuario rehaciendo el home PID (modo ya activo).
        """
        self._go_to_target_after_home = True
        self._tx_target = tx
        self._ty_target = ty
        self._tz_target = tz
        self._target_pos = np.array([tx, ty, tz], dtype=float)
        self._pid_stop()
        self._enter_pid_home()

    def go_home_sequence(self, on_done=None):
        """
        Secuencia de home al entrar a modo Cartesiano:
        home físico (2.5 s) -> PID home, sin ir al destino.
        """
        self._go_to_target_after_home = False
        self._target_pos = None
        self._sequence_on_done = on_done
        self._pid_stop()
        self._enter_physical_home()

    def send_home_only(self):
        """Home físico sin PID — solo al cambiar a modo Cinemática."""
        self._pid_stop()
        home_servos = CartesianPidCompensator.angulos_robotang(
            0, -45, 120, 0, 30, 0)
        self._emit_servo_positions(home_servos)

    def _pid_stop(self):
        """Detiene el lazo PID y cancela la secuencia pendiente."""
        self._state = self.STATE_IDLE
        self._paused = False
        self._sequence_on_done = None
        self._target_pos = None

    def pause_pid(self):
        """Pausa el lazo PID cartesiano (sin perder el estado)."""
        self._paused = True

    def resume_pid(self):
        """Reanuda el lazo PID cartesiano."""
        self._paused = False

    def set_paused(self, paused: bool):
        """Pausa/reanuda el control (API alternativa)."""
        self._paused = paused

    def stop(self):
        """Detiene el hilo de ejecución de forma ordenada."""
        self._running = False
        self.quit()
        self.wait()

    # --- Getters / Setters ---

    def get_current_positions(self):
        """
        Obtiene las últimas posiciones conocidas de los servos.

        Returns:
            list: Lista de 6 flotantes (grados 0-300).
        """
        with self._lock:
            return list(self._current_positions)

    def get_commanded_positions(self):
        """
        Obtiene las últimas posiciones comandadas a los servos.

        A diferencia de `get_current_positions` (telemetría física del
        robot), este valor está siempre disponible una vez enviado un
        comando, por lo que es ideal para mover los sliders aunque el
        robot no esté conectado por puerto serial.

        Returns:
            list: Lista de 6 flotantes (grados 0-300).
        """
        with self._lock:
            return list(self._last_commanded_positions)

    def get_target_pos(self):
        """
        Obtiene el objetivo cartesiano actual.

        Returns:
            np.ndarray: Vector 3x1 o None si no hay objetivo.
        """
        return self._target_pos.copy() if self._target_pos is not None else None
