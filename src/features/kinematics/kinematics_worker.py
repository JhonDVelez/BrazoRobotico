"""
Modulo que define el KinematicsWorker como hilo independiente.

Implementa la logica de control PID cartesiano basada en el codigo
standalone Prueba_controlv11. El worker abre su propia conexion serial,
ejecuta el lazo de control de forma autonoma y emite senales al GUI
para actualizacion de graficas y estado.

Flujo de ejecucion:
    1. Al activar modo cinematica: HOME directo sin PID (2.5s).
    2. Al recibir coordenadas del usuario:
       a. PID al HOME con compensaciones.
       b. PID al TARGET con compensaciones.
    3. Emite pid_iteration para la grafica CartesianPIDPlot.
    4. Emite status_changed para la barra de estado de la UI.
    5. Emite movement_finished al completar.
"""

import math
import time
import re
import queue
import threading
import serial
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal
from src.services.robot.robot_compensator import CartesianPidCompensator


class KinematicsWorker(QThread):
    """
    Worker independiente para control PID cartesiano en tiempo real.

    Abre su propia conexion serial y ejecuta el lazo de control
    de forma autonoma, sin depender del RobotWorker ni del DataController.

    Senales (emitidas desde el hilo worker, procesadas en el main thread):
        pid_iteration(iteracion, pos_real_xyz, pos_target_xyz):
            Para la grafica CartesianPIDPlot.
        status_changed(mensaje):
            Para la barra de estado de la UI.
        movement_finished():
            Notifica que el movimiento completo finalizo.
        input_enabled():
            Notifica que la UI puede habilitar la entrada de coordenadas.
    """
    pid_iteration = pyqtSignal(float, list, list)
    joint_update = pyqtSignal(list)
    status_changed = pyqtSignal(str)
    movement_finished = pyqtSignal()
    input_enabled = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._links = [155.0, 92.0, 111.0, 8.0, 150.0]

        self._serial = None
        self._running = False
        self._telemetry_running = False
        self._paused = False
        self._pid_abort = False
        self._t_resume_pending = False
        self._pause_event = threading.Event()
        self._pause_event.set()

        self._telemetry_lock = threading.Lock()
        self._current_pos = [150.0] * 6
        self._last_valid = [150.0] * 6
        self._jump_freeze_count = [0] * 6

        self._work_queue = queue.Queue()

        self._com_port = None
        self._kp = np.array([1.5, 1.0, 1.38])
        self._ki = np.array([0.05, 0.05, 0.6])  
        self._kd = np.array([0.01, 0.01, 0.04])   

    def set_pid_gains(self, kp, ki, kd):
        self._kp = np.array(kp, dtype=np.float64)
        self._ki = np.array(ki, dtype=np.float64)
        self._kd = np.array(kd, dtype=np.float64)

    def pause(self):
        self._paused = True
        self._pause_event.clear()

    def resume(self):
        self._paused = False
        self._t_resume_pending = True
        self._pause_event.set()

    def abort_pid(self):
        self._pid_abort = True
        if self._paused:
            self._paused = False
            self._pause_event.set()

    # ------------------------------------------------------------------ #
    #                     CINEMATICA DIRECTA Y JACOBIANO                   #
    # ------------------------------------------------------------------ #

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
        pz = (L1 + L3 * math.cos(arg23) - L4 * math.sin(arg23)
              + L2 * math.cos(t2) + L5 * math.cos(arg234))
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
            [-s1 * f, c1 * df_dt2, c1 * df_dt3, c1 * df_dt4],
            [c1 * f, s1 * df_dt2, s1 * df_dt3, s1 * df_dt4],
            [0, dz_dt2, dz_dt3, dz_dt4]
        ])
        return np.linalg.pinv(J)

    # ------------------------------------------------------------------ #
    #                     COMUNICACION SERIAL PROPIA                       #
    # ------------------------------------------------------------------ #

    def _open_serial(self, com_port):
        try:
            self._serial = serial.Serial(com_port, 9600, timeout=1)
            return True
        except (serial.SerialException, PermissionError, OSError) as e:
            print(f"Error abriendo serial {com_port}: {e}")
            self._serial = None
            return False

    def _close_serial(self):
        try:
            if self._serial and self._serial.is_open:
                self._serial.close()
        except (serial.SerialException, OSError):
            pass
        self._serial = None

    def _enviar_robot(self, q_servos):
        if self._serial is None or not self._serial.is_open:
            return
        try:
            trama = ""
            motores = ['A', 'B', 'C', 'D', 'E', 'F']
            for i, char in enumerate(motores):
                val_pwm = int(round(
                    max(0, min(300, float(q_servos[i]))) * (1023 / 300)))
                trama += f"{char}{val_pwm}"
            trama += "\n"
            self._serial.write(trama.encode('ascii'))
            self._serial.flush()
        except (serial.SerialException, OSError) as e:
            print(f"Error enviando comando: {e}")

    def _telemetry_reader(self):
        pattern = re.compile(r"([A-F])(\d+\.?\d*)T[A-F](\d+)")
        congelado_count = [0] * 6

        while self._telemetry_running:
            try:
                if self._serial is None or not self._serial.is_open:
                    time.sleep(0.01)
                    continue

                if self._serial.in_waiting > 0:
                    line = self._serial.readline().decode(
                        'ascii', errors='ignore').strip()
                    if not line:
                        continue

                    matches = pattern.findall(line)
                    if len(matches) < 6:
                        continue

                    temp_pos = [None] * 6
                    for motor_char, pos_val, _ in matches:
                        idx = ord(motor_char) - ord('A')
                        if idx < 6:
                            temp_pos[idx] = float(pos_val)

                    with self._telemetry_lock:
                        # Validacion de rango: filtrar valores fuera de rango fisico individualmente
                        for i in range(6):
                            if temp_pos[i] is not None and not (0 <= temp_pos[i] <= 300):
                                temp_pos[i] = self._last_valid[i]

                        # Deteccion de tramas nulas / caidas de tension
                        if all(v is not None and abs(v) < 0.001 for v in temp_pos[:4]):
                            continue

                        # Filtro anti-ruido electromagnetico con correccion individual
                        for i in range(6):
                            if temp_pos[i] is not None:
                                diff = abs(temp_pos[i] - self._last_valid[i])
                                if diff > 35.0:
                                    congelado_count[i] += 1
                                    if congelado_count[i] <= 4:
                                        temp_pos[i] = self._last_valid[i]
                                else:
                                    congelado_count[i] = 0

                        # Actualizacion limpia de la telemetria
                        for i in range(6):
                            if temp_pos[i] is not None:
                                self._current_pos[i] = temp_pos[i]
                                self._last_valid[i] = temp_pos[i]

            except Exception as e:
                print(f"Alerta: Hilo de telemetria interrumpido: {e}")
                break

    # ------------------------------------------------------------------ #
    #                          LECTURA SEGURA                              #
    # ------------------------------------------------------------------ #

    def _read_positions(self):
        with self._telemetry_lock:
            return list(self._current_pos)

    # ------------------------------------------------------------------ #
    #                PID CARTESIANO (port de Prueba_controlv11)            #
    # ------------------------------------------------------------------ #

    def _pid_control_loop(self, target_xyz, limites_deg,
                          max_iter=3000, tolerancias=None, t_start=None):
        TS = 0.08

        if tolerancias is None:
            tolerancias = np.array([5.0, 5.0, 5.0])

        target = np.array(target_xyz, dtype=float)
        error_acumulado = np.zeros(3)
        error_anterior = np.zeros(3)
        primera_iteracion = True
        contador_estabilidad = 0
        iteraciones_requeridas = 10
        umbral_mm = 2.5
        if t_start is None:
            t_start = time.time()
        t_anterior = t_start
        p_anterior = np.zeros(3)

        for i in range(max_iter):
            if not self._running or self._pid_abort:
                return False
            self._pause_event.wait()

            t_actual = time.time()
            t_iter_start = t_actual
            dt = t_actual - t_anterior
            if dt < 0.01: 
                dt = 0.01  # Acota el dt mínimo para evitar divisiones por cero

            if self._t_resume_pending:
                dt = TS
                self._t_resume_pending = False

            raw_pos = self._read_positions()
            q_reales_deg = np.array(
                CartesianPidCompensator.robotang_angulos(
                    *raw_pos))
            q_actual_rad = np.radians([
                q_reales_deg[0], q_reales_deg[1],
                q_reales_deg[2], q_reales_deg[4]])
            p_actual = self._cinematica_directa(q_actual_rad, self._links)

            if i > 0 and np.allclose(p_actual, p_anterior, atol=0.1):
                q_deg = np.degrees(q_actual_rad)
                self.joint_update.emit([q_deg[0], q_deg[1], q_deg[2], 0, q_deg[3], -80])
                self.pid_iteration.emit(
                    round(time.time() - t_start, 4), p_actual.tolist(), target.tolist())
                t_anterior = time.time()  # Sincroniza el tiempo antes de saltar la iteración
                elapsed = time.time() - t_iter_start
                time.sleep(max(0, TS - elapsed))
                continue
            p_anterior = p_actual.copy()

            self.pid_iteration.emit(
                round(time.time() - t_start, 4), p_actual.tolist(), target.tolist())

            error_actual = target - p_actual
            error_abs = np.abs(error_actual)

            if (error_abs[0] < tolerancias[0] and
                    error_abs[1] < tolerancias[1] and
                    error_abs[2] < tolerancias[2]):
                contador_estabilidad += 1
                error_anterior = error_actual.copy()
                if contador_estabilidad >= iteraciones_requeridas:
                    return True
                elapsed = time.time() - t_iter_start
                time.sleep(max(0, TS - elapsed))
                continue
            else:
                contador_estabilidad = 0

            dist_total = np.linalg.norm(error_actual)

            P = error_actual * self._kp

            if dist_total < umbral_mm * 2:
                error_acumulado *= 0.7
            else:
                error_acumulado += error_actual * dt

            error_acumulado = np.clip(error_acumulado, -35, 35)
            I = error_acumulado * self._ki

            if primera_iteracion:
                D = np.zeros(3)
                primera_iteracion = False
            else:
                d_cruda = (error_actual - error_anterior) / dt
                D = d_cruda * self._kd

            v_control = P + I + D
            print(f"valor de v_control: {v_control}")
            error_anterior = error_actual.copy()

            J_inv = self._calcular_pseudoinversa(q_actual_rad, self._links)
            dq = J_inv @ v_control

            dq_deg = np.degrees(dq)
            umbral_motor = 0.5
            for j in range(len(dq_deg)):
                if 0 < abs(dq_deg[j]) < umbral_motor:
                    dq_deg[j] += np.sign(dq_deg[j]) * umbral_motor
            dq = np.radians(dq_deg)

            q_next_rad = CartesianPidCompensator.apply_physical_limits(
                q_actual_rad + dq, limites_deg)
            q_next_rad[0] = math.atan2(target[1], target[0])
            q_out_deg = np.degrees(q_next_rad)
            q_final = [q_out_deg[0], q_out_deg[1], q_out_deg[2],
                       0, q_out_deg[3], -80]
            self.joint_update.emit(q_final)
            servo_positions = CartesianPidCompensator.angulos_robotang(
                *q_final)

            print(f"[PID] iter={i} "
                  f"xyz={[round(v,2) for v in p_actual.tolist()]} "
                  f"target={[round(v,2) for v in target.tolist()]} "
                  f"err={[round(e,2) for e in error_actual.tolist()]} "
                  f"servo={[round(s,1) for s in servo_positions]}")

            self._enviar_robot(servo_positions)

            t_anterior = t_actual  # Guarda el marcador de tiempo de esta iteración

            elapsed = time.time() - t_iter_start
            time.sleep(max(0, TS - elapsed))

        return False

    # ------------------------------------------------------------------ #
    #              EJECUCION DE SECUENCIA PID (en el hilo worker)          #
    # ------------------------------------------------------------------ #

    def _run_pid_sequence(self, tx, ty, tz):
        from .coordinate_correction import corregir_xy, corregir_z

        self._pid_abort = False

        tx_home, ty_home, tz_home = 185, 0, 170
        tz_home = corregir_z(tx_home, ty_home, tz_home)
        tx_home, ty_home = corregir_xy(tx_home, ty_home)
        limites_home = [(-10, 10), (-50, -40), (0, 130), (0, 120)]

        t_start = time.time()

        self.status_changed.emit("PID: Moviendo a HOME...")
        converged_home = self._pid_control_loop(
            [tx_home, ty_home, tz_home], limites_home, t_start=t_start)
        if converged_home:
            print("PID HOME convergido")
        else:
            print("PID HOME: max iteraciones alcanzadas")

        if self._pid_abort:
            self._pid_abort = False
            return

        self.status_changed.emit("PID: Moviendo a target...")
        limites_target = [(-100, 100), (-90, 90), (-130, 130), (-90, 120)]
        converged_target = self._pid_control_loop(
            [tx, ty, tz], limites_target, t_start=t_start)
        if converged_target:
            print("PID TARGET convergido")
        else:
            print("PID TARGET: max iteraciones alcanzadas")

        self.status_changed.emit("Movimiento completado")
        self.movement_finished.emit()

    # ------------------------------------------------------------------ #
    #                  API PUBLICA (llamada desde el main thread)           #
    # ------------------------------------------------------------------ #

    def send_home_direct(self, com_port):
        self._com_port = com_port
        self._running = True
        self.start()

    def execute_target(self, tx, ty, tz):
        self._work_queue.put(('execute_target', tx, ty, tz))

    def send_home(self):
        self._work_queue.put(('send_home',))

    def stop(self):
        self._running = False
        self._telemetry_running = False
        self._work_queue.put(('stop',))
        self.wait(3000)
        self._close_serial()

    # ------------------------------------------------------------------ #
    #                  FLUJO PRINCIPAL (run del QThread)                   #
    # ------------------------------------------------------------------ #

    def run(self):
        if not self._com_port:
            return

        self.status_changed.emit("Abriendo conexion serial...")
        if not self._open_serial(self._com_port):
            self.status_changed.emit("Error: No se pudo abrir serial")
            self.movement_finished.emit()
            return

        self._telemetry_running = True
        telemetry_thread = threading.Thread(
            target=self._telemetry_reader, daemon=True)
        telemetry_thread.start()

        time.sleep(1)

        self.status_changed.emit("Moviendo a HOME...")
        home_servos = CartesianPidCompensator.angulos_robotang(
            0, -45, 120, 0, 30, 0)
        self._enviar_robot(home_servos)
        self.joint_update.emit([0, -45, 120, 0, 30, 0])
        time.sleep(2.5)

        self.input_enabled.emit()

        while self._running:
            try:
                work = self._work_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if work[0] == 'execute_target':
                _, tx, ty, tz = work
                self._run_pid_sequence(tx, ty, tz)
            elif work[0] == 'send_home':
                home_servos = CartesianPidCompensator.angulos_robotang(
                    0, -45, 120, 0, 30, 0)
                self._enviar_robot(home_servos)
                self.joint_update.emit([0, -45, 120, 0, 30, 0])
            elif work[0] == 'stop':
                break

        self._telemetry_running = False
        telemetry_thread.join(timeout=2)
        self._close_serial()
