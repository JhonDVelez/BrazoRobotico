"""
Módulo que orquesta el PickAndPlaceWorker como un QThread independiente con su propia conexión serial,
cinemática y bucle PID cartesiano.
"""

import math
import time
import re
import queue
import threading
import serial
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal, pyqtSlot, QTimer
from src.features.pick_and_place.pick_place_states import PickPlaceState
from src.features.pick_and_place.pick_place_state_machine import PickPlaceStateMachine
from src.features.pick_and_place.logic.context import PickPlaceContext
from src.services.robot.robot_compensator import CartesianPidCompensator
from src.services.robot.serial_manager import SerialPortManager
from src.services.data.utils.conversions import robotang_angulos


class PickAndPlaceWorker(QThread):
    """
    Worker independiente para Pick and Place con su propia conexión serial,
    hilo de telemetría y bucle de control PID cartesiano.
    """
    action_request = pyqtSignal(dict)
    sequence_completed = pyqtSignal()
    sequence_failed = pyqtSignal(str)
    status_message_updated = pyqtSignal(str)
    mode_change_requested = pyqtSignal(str)
    pid_iteration = pyqtSignal(float, list, list)
    joint_update = pyqtSignal(list)
    vision_search_request = pyqtSignal(bool, bool)
    movement_finished = pyqtSignal()
    worker_ready = pyqtSignal()
    port_released = pyqtSignal()

    def __init__(self, kinematics_controller=None):
        super().__init__()
        self.context = PickPlaceContext()
        self.kinematics_controller = kinematics_controller
        self._sm = PickPlaceStateMachine(on_state_change=self._on_state_change)
        
        self.skip_home = False
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
        self._serial_lock = threading.Lock()
        self._current_pos = [150.0] * 6
        self._last_valid = [150.0] * 6
        self._last_pos_for_plot = None
        self._last_target_for_plot = None
        self._last_emit_time = 0.0
        self._session_start_time = time.time()
        self._jump_freeze_count = [0] * 6

        self._work_queue = queue.Queue()
        self._com_port = None

        self._kp = np.array([0.3, 0.3, 0.198])
        self._ki = np.array([0.7261, 0.1, 0.3898])
        self._kd = np.array([0.0309, 0.01, 0.0251])

        self._claw_mm = 30
        self._last_sent_claw_angle = -999
        self._last_commanded_angles = None
        self._claw_lock = threading.Lock()

        self._check_timer = QTimer()
        self._check_timer.setSingleShot(False)
        self.TIEMPO_PASO_GARRA = 1000
        self._pending_callback = None

        self.movement_finished.connect(self._on_movement_finished)

    def set_claw_value(self, value):
        with self._claw_lock:
            self._claw_mm = value

    def set_pid_gains(self, kp, ki, kd):
        self._kp = np.array(kp, dtype=np.float64)
        self._ki = np.array(ki, dtype=np.float64)
        self._kd = np.array(kd, dtype=np.float64)

    def pause(self):
        self._paused = True
        self._pause_event.clear()
        self._check_timer.stop()

    def resume(self):
        self._paused = False
        self._t_resume_pending = True
        self._pause_event.set()
        if self._pending_callback:
            self._wait_for_settle(self._pending_callback)

    def reset_state(self):
        self._paused = False
        self._pid_abort = True
        with self._work_queue.mutex:
            self._work_queue.queue.clear()
        self._pause_event.set()
        self._t_resume_pending = False
        self._session_start_time = time.time()
        self._last_emit_time = 0.0

    def abort_pid(self):
        self.reset_state()

    def stop_and_reset(self):
        """Detiene la secuencia y limpia el estado para un reseteo limpio."""
        if self.current_state_value != 'idle':
            self._sm.reset()
        self._check_timer.stop()
        self.context.reset()
        self.reset_state()
        self.execute_direct_move([0, 0, 0, 0, 0, 0])

    def force_abort(self):
        """Forzar detención inmediata e interrupción de IO serial."""
        self._running = False
        self._telemetry_running = False
        self._pid_abort = True
        self._pause_event.set()
        
        ser = SerialPortManager.get_instance().get_serial() # o acceso propio
        if ser:
            try:
                ser.cancel_read()
                ser.cancel_write()
                ser.close()
            except:
                pass
        
        with self._work_queue.mutex:
            self._work_queue.queue.clear()
        
        self.quit()
        self.wait(1000)

    def release_and_cleanup(self):
        """Libera el puerto serial, limpia buffers y notifica."""
        SerialPortManager.get_instance().release_access("PickAndPlaceWorker")
        self.port_released.emit()

    def set_com_port(self, com_port):
        self._com_port = com_port

    def open_serial_manual(self, com_port):
        self._com_port = com_port
        return self._open_serial(com_port)

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
        return SerialPortManager.get_instance().request_access(com_port, "PickAndPlaceWorker")

    def _close_serial(self):
        SerialPortManager.get_instance().release_access("PickAndPlaceWorker")

    def _enviar_robot(self, q_servos):
        spm = SerialPortManager.get_instance()
        com = self._com_port or spm._com or "COM7"
        if not spm.is_active("PickAndPlaceWorker"):
            try:
                spm.request_access(com, "PickAndPlaceWorker")
            except Exception as e:
                print(f"[DEBUG] [PickAndPlaceWorker] Error solicitando acceso a {com}: {e}")
                return
            
        ser = spm.get_serial()
        if ser is None or not ser.is_open:
            try:
                spm.request_access(com, "PickAndPlaceWorker")
            except Exception as e:
                print(f"[DEBUG] [PickAndPlaceWorker] Error reabriendo {com}: {e}")

        if not spm.get_serial() or not spm.get_serial().is_open:
            print("[DEBUG] Serial port not open, cannot send command.")
            return

        try:
            trama = ""
            motores = ['A', 'B', 'C', 'D', 'E', 'F']
            for i, char in enumerate(motores):
                val_pwm = int(round(
                    max(0, min(300, float(q_servos[i]))) * (1023 / 300)))
                trama += f"{char}{val_pwm}"
            trama += "\n"
            spm.safe_write(trama.encode('ascii'))
        except (serial.SerialException, OSError) as e:
            print(f"Error enviando comando: {e}")

    def _telemetry_reader(self):
        print("[DEBUG] Telemetry reader thread started.")
        pattern = re.compile(r"([A-F])(\d+\.?\d*)T[A-F](\d+)")
        congelado_count = [0] * 6

        while self._telemetry_running:
            try:
                spm = SerialPortManager.get_instance()
                if not spm.is_active("PickAndPlaceWorker"):
                    time.sleep(0.1)
                    continue
                    
                ser = spm.get_serial()
                if ser is None or not ser.is_open:
                    print(f"[DEBUG] Telemetry waiting for serial")
                    time.sleep(0.1)
                    continue

                if spm.get_in_waiting() > 0:
                    raw_line = spm.safe_readline()
                    line = raw_line.decode('ascii', errors='ignore').strip()
                    if not line:
                        continue

                    matches = pattern.findall(line)
                    if len(matches) < 6:
                        # print(f"[DEBUG] Incomplete telemetry line: {line}")
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
                        print(f"[DEBUG] Updated _current_pos: {self._current_pos}")

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
    #                          PID CARTESIANO                              #
    # ------------------------------------------------------------------ #

    def _pid_control_loop(self, target_xyz, limites_deg,
                          max_iter=800, tolerancias=None, t_start=None, angulo_garra=None):
        from src.features.kinematics.coordinate_correction import apertura_de_garra
        TS = 0.08

        if angulo_garra is None:
            with self._claw_lock:
                actual_angulo_garra = apertura_de_garra(self._claw_mm)
        else:
            actual_angulo_garra = angulo_garra

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
                self.joint_update.emit([q_deg[0], q_deg[1], q_deg[2], 0, q_deg[3], actual_angulo_garra])
                if t_actual - self._last_emit_time >= 0.1:
                    self.actualizar_grafica(target.tolist(), p_actual.tolist())
                    self._last_emit_time = t_actual
                t_anterior = time.time()  # Sincroniza el tiempo antes de saltar la iteración

                elapsed = time.time() - t_iter_start
                time.sleep(max(0, TS - elapsed))
                continue
            p_anterior = p_actual.copy()

            if t_actual - self._last_emit_time >= 0.1:
                self.actualizar_grafica(target.tolist(), p_actual.tolist())
                self._last_emit_time = t_actual

            error_actual = target - p_actual
            error_abs = np.abs(error_actual)

            if (error_abs[0] < tolerancias[0] and
                    error_abs[1] < tolerancias[1] and
                    error_abs[2] < tolerancias[2]):
                contador_estabilidad += 1
                error_anterior = error_actual.copy()
                if contador_estabilidad >= iteraciones_requeridas:
                    print(f"[DEBUG] PID P&P convergido en {i} iteraciones.")
                    self.movement_finished.emit()
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
                       0, q_out_deg[3], actual_angulo_garra]
            self.joint_update.emit(q_final)
            self._last_commanded_angles = q_final # Actualizar caché
            servo_positions = CartesianPidCompensator.angulos_robotang(
                *q_final)

            print(f"[DEBUG] PID Iter {i}: Target {target}, Actual {p_actual}, Error {error_actual}, Servo Pos {servo_positions}")

            self._enviar_robot(servo_positions)

            t_anterior = t_actual  # Guarda el marcador de tiempo de esta iteración

            elapsed = time.time() - t_iter_start
            time.sleep(max(0, TS - elapsed))

        self.movement_finished.emit()
        return False

    # ------------------------------------------------------------------ #
    #              EJECUCION DE SECUENCIA PID (en el hilo worker)          #
    # ------------------------------------------------------------------ #

    def _wait_for_position(self, target, timeout=5.0):
        start_time = time.time()
        while time.time() - start_time < timeout:
            current_pos = self._read_positions()
            if all(abs(current_pos[i] - target[i]) < 5 for i in range(len(target))):
                return True
            time.sleep(0.1)
        return False

    def start_worker(self, com_port):
        self._com_port = com_port
        self._running = True
        self._pid_abort = False
        self.start()

    def execute_pid_only(self, target_xyz, limites_deg, max_iter=800, tolerancias=None, t_start=None, angulo_garra=None):
        self._work_queue.put(('execute_pid_only', target_xyz, limites_deg, max_iter, tolerancias, t_start, angulo_garra))

    def execute_direct_move(self, positions):
        self._work_queue.put(('direct_move', positions))

    def actualizar_grafica(self, target_xyz, pos_actual_xyz):
        self._last_target_for_plot = list(target_xyz)
        self._last_pos_for_plot = list(pos_actual_xyz)
        t_relativo = round(time.time() - self._session_start_time, 4)
        self.pid_iteration.emit(t_relativo, self._last_pos_for_plot, self._last_target_for_plot)

    def _update_graph_with_angles(self, target_angles_deg):
        if (target_angles_deg == [0,0,0,0,0,0]) or (target_angles_deg is None):
            target_xyz = [0,0,468]
            pos_actual_xyz = [0,0,468]
            self.actualizar_grafica(target_xyz, pos_actual_xyz)
        else:
            target_rad = np.radians([target_angles_deg[0], target_angles_deg[1], 
                                    target_angles_deg[2], target_angles_deg[4]])
            target_xyz = self._cinematica_directa(target_rad, self._links)
            
            pos_actual_deg = CartesianPidCompensator.robotang_angulos(*self._read_positions())
            pos_actual_rad = np.radians([pos_actual_deg[0], pos_actual_deg[1], 
                                        pos_actual_deg[2], pos_actual_deg[4]])
            pos_actual_xyz = self._cinematica_directa(pos_actual_rad, self._links)
            
            self.actualizar_grafica(target_xyz.tolist(), pos_actual_xyz.tolist())

    def run(self):
        ser = SerialPortManager.get_instance().get_serial()
        if ser is None or not ser.is_open:
            if not self._com_port:
                return
            if not self._open_serial(self._com_port):
                self.movement_finished.emit()
                return

        self._telemetry_running = True
        telemetry_thread = threading.Thread(
            target=self._telemetry_reader, daemon=True)
        telemetry_thread.start()

        self.worker_ready.emit()
        time.sleep(1)

        while self._running:
            try:
                work = self._work_queue.get(timeout=0.01)
            except queue.Empty:
                raw_pos = self._read_positions()
                q_reales_deg = np.array(
                    CartesianPidCompensator.robotang_angulos(
                        *raw_pos))
                
                if self._last_commanded_angles is None:
                    self._last_commanded_angles = q_reales_deg.tolist()

                for i in range(5):
                    if abs(q_reales_deg[i] - self._last_commanded_angles[i]) > 5.0:
                        self._last_commanded_angles[i] = q_reales_deg[i]

                self.joint_update.emit(self._last_commanded_angles)
                continue

            if work[0] == 'execute_pid_only':
                _, target, limites, max_iter, tol, t_start, angulo_garra = work
                if t_start is None:
                    t_start = time.time()
                self._pid_abort = False
                self._pid_control_loop(target, limites, max_iter=max_iter, tolerancias=tol, t_start=t_start, angulo_garra=angulo_garra)
            elif work[0] == 'direct_move':
                _, positions = work
                servo_positions = CartesianPidCompensator.angulos_robotang(*positions)
                self._enviar_robot(servo_positions)
                self.joint_update.emit(positions)
                self._update_graph_with_angles(positions)
                self._last_commanded_angles = positions
                self._wait_for_position(servo_positions)
                self.movement_finished.emit()
            elif work[0] == 'stop':
                break

        self._telemetry_running = False
        telemetry_thread.join(timeout=2)
        self._close_serial()

    @pyqtSlot(dict)
    def on_poses_from_camera(self, poses):
        self.context.sphere_poses.update(poses)

    def _on_state_change(self, state_name):
        print(f"[DEBUG] >>> [StateMachine] Entering State: {state_name}")
        
        if state_name == PickPlaceState.WAITING_FOR_INPUT.value:
            self.vision_search_request.emit(True, True)
        else:
            self.vision_search_request.emit(False, False)

        handlers = {
            PickPlaceState.HOME1_MOVE.value: self._enter_home1_move,
            PickPlaceState.HOME1_VALIDATE.value: self._enter_home1_validate,
            PickPlaceState.PID_HOME.value: self._enter_pid_home,
            PickPlaceState.PICK_DOWN.value: self._enter_pick_down,
            PickPlaceState.PICK_GRASP.value: self._enter_pick_grasp,
            PickPlaceState.RETRACT_LIFT.value: self._enter_retract_lift,
            PickPlaceState.RETRACT_TO_HOME1_PICK.value: self._enter_retract_to_home1_pick,
            PickPlaceState.PID_HOME_PLACE.value: self._enter_pid_home_place,
            PickPlaceState.PLACE_DOWN.value: self._enter_place_down,
            PickPlaceState.PLACE_RELEASE.value: self._enter_place_release,
            PickPlaceState.RETRACT_FROM_PLACE.value: self._enter_retract_from_place,
            PickPlaceState.FINAL_SEQ_HOME.value: self._enter_final_seq_home,
            PickPlaceState.FINAL_SEQ_HOME2.value: self._enter_final_seq_home2,
            PickPlaceState.FINAL_SEQ_HOME1.value: self._enter_final_seq_home1,
            PickPlaceState.WAITING_FOR_INPUT.value: self._enter_waiting_for_input,
        }
        handler = handlers.get(state_name)
        if handler:
            handler()
            print(f"[DEBUG] <<< [StateMachine] Finished Handler for State: {state_name}")

    def calcular_angulo_garra(self, tam):
        from src.features.kinematics.coordinate_correction import apertura_de_garra
        return apertura_de_garra(tam)

    def _wait_for_settle(self, callback):
            self._pending_callback = callback
            
            def wrapped_callback():
                self._pending_callback = None
                callback()
            
            try:
                self._check_timer.timeout.disconnect()
            except Exception:
                pass
                
            self._check_timer.setSingleShot(True)
            self._check_timer.timeout.connect(wrapped_callback)
            self._check_timer.start(2500)

    def _enviar_comando_movimiento(self, apertura):
        current_pwm = self._read_positions()
        current_angles = list(robotang_angulos(*current_pwm))
        ang_garra = self.calcular_angulo_garra(apertura)
        current_angles[5] = ang_garra
        self.execute_direct_move(current_angles)

    def _ejecutar_paso_apertura(self, apertura_actual, apertura_final, incremento):
        nueva_apertura = min(apertura_actual + incremento, apertura_final)
        self._enviar_comando_movimiento(nueva_apertura)
        if nueva_apertura < apertura_final:
            QTimer.singleShot(self.TIEMPO_PASO_GARRA, lambda: self._ejecutar_paso_apertura(nueva_apertura, apertura_final, incremento))
        else:
            self._sm.place_release_done()

    def _enter_home1_move(self):
        print("[DEBUG] PickAndPlaceWorker Entering HOME1_MOVE (Paso 1)")
        servos_paso1 = [0, 0, 130, 0, -30, 0]
        self.execute_direct_move(servos_paso1) 
        
        def ejecutar_paso_2():
            print("[DEBUG] PickAndPlaceWorker Entering HOME1_MOVE (Paso 2)")
            servos_paso2 = [0, -90, 130, 0, -30, 0]
            self.execute_direct_move(servos_paso2)
            
            def finalizar_home1():
                self._sm.home1_done()
                
            self._wait_for_settle(finalizar_home1)

        self._wait_for_settle(ejecutar_paso_2)

    def _enter_home1_validate(self):
        print("[DEBUG] Entering HOME1_VALIDATE")
        self._wait_for_settle(self._sm.home1_validated)

    def _enter_waiting_for_input(self):
        if self.context.ik_target is None:
            self.status_message_updated.emit("Selecciona objeto y su color")
            self.mode_change_requested.emit('pick')
        else:
            self.status_message_updated.emit("Selecciona destino en el plano")
            self.mode_change_requested.emit('place')

    def _enter_pid_home(self, angulo_garra_custom=None):
        print("[DEBUG] Entering PID_HOME")
        tam = self.context.tamano_seleccionado if self.context.tamano_seleccionado else 30
        ang_garra = angulo_garra_custom if angulo_garra_custom is not None else self.calcular_angulo_garra(tam + 30)
        self.update_gains_from_panel()
        tx, ty, tz = 185, 0, 170
        tz = self.corregir_z(tx, ty, tz)
        tx, ty = self.corregir_xy(tx, ty)
        limites_home = [(-10, 10), (-50, -40), (0, 130), (0, 120)]
        self.execute_pid_only([tx, ty, tz], limites_home, angulo_garra=ang_garra)

    def _enter_pick_down(self):
        print("[DEBUG] Entering PICK_DOWN")
        tam = self.context.tamano_seleccionado if self.context.tamano_seleccionado else 30
        ang_garra = self.calcular_angulo_garra(tam + 30)
        self.update_gains_from_panel()
        x, y, z = self.context.ik_target
        x1 = y
        y1 = x
        if y1 < 0:
            x = x1 + 125
            y = y1 + 35
        else:
            x = x1 + 105
            y = y1 + 30
        z_comp = round((0.1667*x1) + 22)
        z = tam/2 + z_comp 
        z = self.corregir_z(x, y, z)
        x, y = self.corregir_xy(x, y)
        limites_target = [(-100, 100), (-90, 90), (-130, 130), (-90, 120)]
        self.execute_pid_only([x, y, z], limites_target, angulo_garra=ang_garra)
       
    def _enter_pick_grasp(self):
        tam = self.context.tamano_seleccionado if self.context.tamano_seleccionado else 30
        apertura = tam - 20 
        self._enviar_comando_movimiento(apertura)

    def _enter_retract_lift(self):
        print("[DEBUG] Entering RETRACT_LIFT")
        tam = self.context.tamano_seleccionado if self.context.tamano_seleccionado else 30
        ang_garra = self.calcular_angulo_garra(tam - 20)
        self.update_gains_from_panel()
        x, y, z = self.context.ik_target
        x1 = y
        y1 = x
        if y1 < 0:
            x = x1 + 125
            y = y1 + 35
        else:
            x = x1 + 105
            y = y1 + 30
        z = 100
        z = self.corregir_z(x, y, z)
        x, y = self.corregir_xy(x, y)
        limites_target = [(-100, 100), (-90, 90), (-130, 130), (-90, 120)]
        self.execute_pid_only([x, y, z], limites_target, angulo_garra=ang_garra)

    def _enter_retract_to_home1_pick(self):
        tam = self.context.tamano_seleccionado if self.context.tamano_seleccionado else 30
        ang_garra = self.calcular_angulo_garra(tam - 20)
        print("[DEBUG] Entering RETRACT_TO_HOME1_PICK")
        servos = [0,-90,130,0,-30,ang_garra]
        self.execute_direct_move(servos)
        self._wait_for_settle(self._sm.retract_to_home1_pick_done)

    def _enter_pid_home_place(self, angulo_garra_custom=None):
        print("[DEBUG] Entering PID_HOME_PLACE")
        tam = self.context.tamano_seleccionado if self.context.tamano_seleccionado else 30
        ang_garra = angulo_garra_custom if angulo_garra_custom is not None else self.calcular_angulo_garra(tam - 20)
        self.update_gains_from_panel()
        tx, ty, tz = 185, 0, 170
        tz = self.corregir_z(tx, ty, tz)
        tx, ty = self.corregir_xy(tx, ty)
        limites_home = [(-10, 10), (-50, -40), (0, 130), (0, 120)]
        self.execute_pid_only([tx, ty, tz], limites_home, angulo_garra=ang_garra)

    def _enter_place_down(self):
        tam = self.context.tamano_seleccionado if self.context.tamano_seleccionado else 30
        ang_garra = self.calcular_angulo_garra(tam - 20)
        self.update_gains_from_panel()
        if self.context.place_target_coords is None:
            print("[ERROR] place_target_coords is None in _enter_place_down")
            self.sequence_failed.emit('No se ha seleccionado posición de colocación (place)')
            self._sm.reset()
            return
        x, y, z = self.context.place_target_coords
        x = float(self.context.place_target_coords['x'])
        y = float(self.context.place_target_coords['y'])
        z = float(self.context.place_target_coords['z'])
        x1 = y
        y1 = x
        x = x1 + 120
        if y1 < 0:
            y = y1 + 15
        else:
            y = y1 + 30
        z_comp = round((0.1667*x1) + 40)
        z = tam/2 + z_comp 
        z = self.corregir_z(x, y, z)
        x, y = self.corregir_xy(x, y)
        print(f"[DEBUG] PID Target (PLACE_DOWN): x={x}, y={y}, z={z}")
        limites_target = [(-100, 100), (-90, 90), (-130, 130), (-90, 120)]
        self.execute_pid_only([x, y, z], limites_target, angulo_garra=ang_garra)

    def _enter_place_release(self):
        tam = self.context.tamano_seleccionado if self.context.tamano_seleccionado else 30
        apertura_total = tam + 20
        self._enviar_comando_movimiento(apertura_total)

    def _enter_retract_from_place(self):
        tam = self.context.tamano_seleccionado if self.context.tamano_seleccionado else 30
        ang_garra = self.calcular_angulo_garra(tam + 20)
        self.update_gains_from_panel()
        if self.context.place_target_coords is None:
            print("[ERROR] place_target_coords is None in _enter_place_down")
            self.sequence_failed.emit('No se ha seleccionado posición de colocación (place)')
            self._sm.reset()
            return
        x, y, z = self.context.place_target_coords
        x = float(self.context.place_target_coords['x'])
        y = float(self.context.place_target_coords['y'])
        z = float(self.context.place_target_coords['z'])
        x1 = y
        y1 = x
        x = x1 + 135
        if y1 < 0:
            y = y1 + 15
        else:
            y = y1 + 30
        z = 100
        z = self.corregir_z(x, y, z)
        x, y = self.corregir_xy(x, y)
        print(f"[DEBUG] PID Target (PLACE_UP): x={x}, y={y}, z={z}")
        limites_target = [(-100, 100), (-90, 90), (-130, 130), (-90, 120)]
        self.execute_pid_only([x, y, z], limites_target, angulo_garra=ang_garra)

    def _enter_final_seq_home1(self):
        print("[DEBUG] Entering FINAL_SEQ_HOME1")
        servos = [0,-90,130,0,-30,0]
        self.execute_direct_move(servos)
        self._wait_for_settle(self._final_home1_cleanup)
    
    def _final_home1_cleanup(self):
        self.context.reset()
        self._sm.final_home1_done()
        self.sequence_completed.emit()

    def _enter_final_seq_home(self):
        print("[DEBUG] Entering FINAL_SEQ_HOME")
        self._sm.final_home_done()

    def _enter_final_seq_home2(self):
        print("[DEBUG] Entering FINAL_SEQ_HOME2")
        self._sm.final_home2_done()

    def corregir_xy(self, x, y):
        from src.features.kinematics.coordinate_correction import corregir_xy as corr_xy
        return corr_xy(x, y)

    def corregir_z(self, x, y, z):
        from src.features.kinematics.coordinate_correction import corregir_z as corr_z
        return corr_z(x, y, z)

    @pyqtSlot(str)
    def pick(self, color):
        print(f"[DEBUG] User input: Pick {color}")
        self.update_gains_from_panel()
        self.context.selected_color = color
        
        if color in self.context.sphere_poses:
            pose_data = self.context.sphere_poses[color]
            if isinstance(pose_data, dict) and 'position' in pose_data:
                self.context.ik_target = pose_data['position']
            else:
                self.context.ik_target = pose_data
        
        if self._sm.current_state_value == PickPlaceState.WAITING_FOR_INPUT.value:
            self._sm.ready_to_home2()
        elif self._sm.current_state_value == PickPlaceState.IDLE.value:
            self._sm.start_op()

    @pyqtSlot(dict)
    def place(self, coords):
        print(f"[DEBUG] >>> PickAndPlaceWorker.place() llamado con coords: {coords}")
        self.update_gains_from_panel()
        self.context.place_target_coords = coords
        
        if self._sm.current_state_value == PickPlaceState.WAITING_FOR_INPUT.value:
            if self.context.ik_target is not None:
                 self._sm.ready_to_place()
            else:
                 self._sm.ready_to_home2()
        elif self._sm.current_state_value == PickPlaceState.IDLE.value:
            self._sm.start_op()

    @pyqtSlot()
    def _on_movement_finished(self):
        current = self.current_state_value
        print(f"[DEBUG] >>> _on_movement_finished. Current state: {current}")
        if current == PickPlaceState.PID_HOME.value:
            self._sm.pid_home_done()
        elif current == PickPlaceState.PICK_DOWN.value:
            self._sm.pick_down_done()
        elif current == PickPlaceState.PICK_GRASP.value:
            self._sm.pick_grasp_done()
        elif current == PickPlaceState.RETRACT_LIFT.value:
            self._sm.retract_lift_done()
        elif current == PickPlaceState.RETRACT_TO_HOME1_PICK.value:
            self._sm.retract_to_home1_pick_done()
        elif current == PickPlaceState.PID_HOME_PLACE.value:
            self._sm.pid_home_place_done()
        elif current == PickPlaceState.PLACE_DOWN.value:
            self._sm.place_down_done()
        elif current == PickPlaceState.PLACE_RELEASE.value:
            self._sm.place_release_done()
        elif current == PickPlaceState.RETRACT_FROM_PLACE.value:
            self._sm.retract_from_place_done()
        elif current == PickPlaceState.FINAL_SEQ_HOME.value:
            self._sm.final_home_done()
        elif current == PickPlaceState.FINAL_SEQ_HOME2.value:
            self._sm.final_home2_done()
        elif current == PickPlaceState.FINAL_SEQ_HOME1.value:
            self._sm.final_home1_done()

    @pyqtSlot(list)
    def on_target_reached(self, _positions): pass

    @pyqtSlot(dict)
    def on_ik_ready(self, result): pass

    @pyqtSlot()
    def abort(self):
        if self.current_state_value != PickPlaceState.IDLE.value:
            self._sm.reset()

    def update_pid_gains(self, gains):
        self.set_pid_gains(gains['kp'], gains['ki'], gains['kd'])

    def update_gains_from_panel(self):
        if self.kinematics_controller:
            try:
                widget = self.kinematics_controller.get_widget()
                gains = widget.get_pid_gains()
                self.set_pid_gains(gains["kp"], gains["ki"], gains["kd"])
            except Exception as e:
                print(f"[DEBUG] Error actualizando ganancias desde panel: {e}")

    def start_sequence(self):
        if self._sm.current_state_value == 'idle':
            self._sm.start_op()

    @pyqtSlot(list)
    def on_simulation_feedback_update(self, positions):
        with self._telemetry_lock:
            self._current_pos = list(positions)
        self.context.current_feedback = positions
        
    @pyqtSlot(list, list)
    def on_physical_feedback_update(self, positions, temperatures):
        with self._telemetry_lock:
            self._current_pos = list(positions)
        self.context.current_feedback = positions

    @property
    def current_state_value(self):
        return self._sm.current_state.value
