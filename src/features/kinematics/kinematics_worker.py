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
        self.skip_home = False # Nueva bandera
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
        self._last_pos_for_plot = None
        self._last_target_for_plot = None
        self._session_start_time = time.time()
        self._jump_freeze_count = [0] * 6

        self._work_queue = queue.Queue()

        self._com_port = None
        self._kp = np.array([1.5, 1.0, 1.38])
        self._ki = np.array([0.25, 0.1, 0.6])  
        self._kd = np.array([0.02, 0.01, 0.04])   

        self._claw_mm = 30 # Valor por defecto
        self._last_sent_claw_angle = -999 # Valor inicial para forzar envío
        self._last_commanded_angles = None # Caché de posiciones enviadas
        self._claw_lock = threading.Lock()
        self.gripper_control_enabled = True

    def enable_gripper_control(self):
        self.gripper_control_enabled = True

    def disable_gripper_control(self):
        self.gripper_control_enabled = False

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

    def resume(self):
        self._paused = False
        self._t_resume_pending = True
        self._pause_event.set()

    def reset_state(self):
        self._paused = False
        self._pid_abort = True  # Asegura la salida del bucle PID
        # Vaciar la cola de tareas para descartar objetivos previos
        with self._work_queue.mutex:
            self._work_queue.queue.clear()
        self._pause_event.set()
        self._t_resume_pending = False

    def abort_pid(self):
        self.reset_state()

    def stop_and_reset(self):
        """Detiene el movimiento, limpia el estado y regresa al HOME."""
        self.reset_state()
        self._last_commanded_angles = None
        with self._claw_lock:
            self._claw_mm = 30
            self._last_sent_claw_angle = -999
        self.send_home()

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
            print("[DEBUG] Serial port not open, cannot send command.")
            return
        try:
            trama = ""
            # ... resto del código sin cambios ...
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
        print("[DEBUG] Telemetry reader thread started.")
        pattern = re.compile(r"([A-F])(\d+\.?\d*)T[A-F](\d+)")
        congelado_count = [0] * 6

        while self._telemetry_running:
            try:
                if self._serial is None or not self._serial.is_open:
                    time.sleep(0.1)
                    continue

                if self._serial.in_waiting > 0:
                    line = self._serial.readline().decode('ascii', errors='ignore').strip()
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
                        # print(f"[DEBUG] Updated _current_pos: {self._current_pos}")

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
                          max_iter=3000, tolerancias=None, t_start=None, angulo_garra=None):
        from .coordinate_correction import apertura_de_garra
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
        self._session_start_time = t_start
        t_anterior = t_start
        p_anterior = np.zeros(3)
        update_counter = 0

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

            update_counter += 1
            if i > 0 and np.allclose(p_actual, p_anterior, atol=0.1):
                q_deg = np.degrees(q_actual_rad)
                self.joint_update.emit([q_deg[0], q_deg[1], q_deg[2], 0, q_deg[3], actual_angulo_garra])
                if update_counter % 3 == 0:
                    self.actualizar_grafica(target.tolist(), p_actual.tolist())
                t_anterior = time.time()  # Sincroniza el tiempo antes de saltar la iteración

                elapsed = time.time() - t_iter_start
                time.sleep(max(0, TS - elapsed))
                continue
            p_anterior = p_actual.copy()

            if update_counter % 3 == 0:
                self.actualizar_grafica(target.tolist(), p_actual.tolist())

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


            self._enviar_robot(servo_positions)

            t_anterior = t_actual  # Guarda el marcador de tiempo de esta iteración

            elapsed = time.time() - t_iter_start
            time.sleep(max(0, TS - elapsed))

        return False

    # ------------------------------------------------------------------ #
    #              EJECUCION DE SECUENCIA PID (en el hilo worker)          #
    # ------------------------------------------------------------------ #

    def _run_pid_sequence(self, tx, ty, tz):
        from .coordinate_correction import corregir_xy, corregir_z, apertura_de_garra

        self._pid_abort = False

        with self._claw_lock:
            angulo_garra = apertura_de_garra(self._claw_mm)

        tx_home, ty_home, tz_home = 185, 0, 170
        tz_home = corregir_z(tx_home, ty_home, tz_home)
        tx_home, ty_home = corregir_xy(tx_home, ty_home)
        limites_home = [(-10, 10), (-50, -40), (0, 130), (0, 120)]

        t_start = time.time()

        self.status_changed.emit("PID: Moviendo a HOME...")
        converged_home = self._pid_control_loop(
            [tx_home, ty_home, tz_home], limites_home, t_start=t_start, angulo_garra=angulo_garra)
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
            [tx, ty, tz], limites_target, t_start=t_start, angulo_garra=angulo_garra)
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

    def start_worker(self, com_port):
        self._com_port = com_port
        self._running = True
        self.start()

    def execute_target(self, tx, ty, tz):
        self._work_queue.put(('execute_target', tx, ty, tz))

    def execute_pid_only(self, target_xyz, limites_deg, max_iter=3000, tolerancias=None, t_start=None, angulo_garra=None):
        self._work_queue.put(('execute_pid_only', target_xyz, limites_deg, max_iter, tolerancias, t_start, angulo_garra))

    def execute_direct_move(self, positions):
        """Encola un movimiento directo de servos (0-300)."""
        self._work_queue.put(('direct_move', positions))


    def _wait_for_position(self, target, timeout=5.0):
        """Espera a que el robot llegue a la posición objetivo dentro de una tolerancia."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            current_pos = self._read_positions()
            # Asumimos que current_pos y target están en el rango 0-300
            # Tolerancia de 5 unidades según validaciones previas
            if all(abs(current_pos[i] - target[i]) < 5 for i in range(len(target))):
                return True
            time.sleep(0.1)
        print("Timeout esperando posición:", target)
        return False

    def send_home(self):
        self._work_queue.put(('send_home',))

    def stop(self):
        self._running = False
        self._telemetry_running = False
        self._work_queue.put(('stop',))
        self.wait(3000)
        self._close_serial()

    def set_com_port(self, com_port):
        self._com_port = com_port

    def open_serial_manual(self, com_port):
        """Abre el puerto serial sin iniciar el bucle de ejecución o el movimiento HOME."""
        self._com_port = com_port
        return self._open_serial(com_port)

    def actualizar_grafica(self, target_xyz, pos_actual_xyz):
        """Emite la señal pid_iteration para actualizar la gráfica y guarda el estado."""
        self._last_target_for_plot = list(target_xyz)
        self._last_pos_for_plot = list(pos_actual_xyz)
        
        # Tiempo relativo al inicio de la sesión
        t_relativo = round(time.time() - self._session_start_time, 4)
        
        self.pid_iteration.emit(t_relativo, self._last_pos_for_plot, self._last_target_for_plot)

    def _update_graph_with_angles(self, target_angles_deg):
        """Calcula cinemática para target y actual y actualiza la gráfica."""
        # Convertir ángulos objetivo a radianes (considerando los 4 DOF usados en _pid_control_loop)
        # target_angles_deg tiene 6 elementos (incluyendo garra)
        if (target_angles_deg == [0,0,0,0,0,0]) or (target_angles_deg is None):

            target_xyz = [0,0,468]  # Posición por defecto si los ángulos son nulos
            pos_actual_xyz = [0,0,468]  # Posición por defecto si los ángulos son nulos
            self.actualizar_grafica(target_xyz, pos_actual_xyz)
        else:
            target_rad = np.radians([target_angles_deg[0], target_angles_deg[1], 
                                    target_angles_deg[2], target_angles_deg[4]])
            target_xyz = self._cinematica_directa(target_rad, self._links)
            
            # Posición actual
            pos_actual_deg = CartesianPidCompensator.robotang_angulos(*self._read_positions())
            pos_actual_rad = np.radians([pos_actual_deg[0], pos_actual_deg[1], 
                                        pos_actual_deg[2], pos_actual_deg[4]])
            pos_actual_xyz = self._cinematica_directa(pos_actual_rad, self._links)
            
            self.actualizar_grafica(target_xyz.tolist(), pos_actual_xyz.tolist())


    # ------------------------------------------------------------------ #
    #                  FLUJO PRINCIPAL (run del QThread)                   #
    # ------------------------------------------------------------------ #

    def run(self):
        if self._serial is None or not self._serial.is_open:
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

        if not self.skip_home:
            self.status_changed.emit("Moviendo a HOME...")
            
            from .coordinate_correction import apertura_de_garra
            with self._claw_lock:
                angulo_garra = apertura_de_garra(self._claw_mm)
                
            home_pos = [0, -45, 120, 0, 30, angulo_garra]
            servo_positions = CartesianPidCompensator.angulos_robotang(*home_pos)
            self._enviar_robot(servo_positions)
            rad_home_pos = np.radians([home_pos[0], home_pos[1], home_pos[2], home_pos[4]])
            target_home_xyz = self._cinematica_directa(rad_home_pos, self._links)
            pos_actual = CartesianPidCompensator.robotang_angulos(*self._read_positions())
            rad_actual = np.radians([pos_actual[0], pos_actual[1], pos_actual[2], pos_actual[4]])
            pos_actual_xyz = self._cinematica_directa(rad_actual, self._links)
            self.actualizar_grafica(target_home_xyz.tolist(), pos_actual_xyz.tolist())
            self.joint_update.emit(home_pos)
            self._wait_for_position(servo_positions)

            self.input_enabled.emit()

        # Bucle de espera / actualización manual fuera de PID
        from .coordinate_correction import apertura_de_garra
        while self._running:
            # Intentar obtener trabajo de la cola
            try:
                work = self._work_queue.get(timeout=0.01)
            except queue.Empty:
                # Actualización de garra fuera de PID
                raw_pos = self._read_positions()
                q_reales_deg = np.array(
                    CartesianPidCompensator.robotang_angulos(
                        *raw_pos))
                
                # Inicializar caché si es None (primera vez que entra al bucle)
                if self._last_commanded_angles is None:
                    self._last_commanded_angles = q_reales_deg.tolist()
                else:
                    # Actualizar las primeras 5 articulaciones con telemetría real
                    for i in range(5):
                        self._last_commanded_angles[i] = q_reales_deg[i]
                
                if self.gripper_control_enabled:
                    with self._claw_lock:
                        angulo_garra = apertura_de_garra(self._claw_mm)
                        
                    # Actualizar garra en el caché
                    self._last_commanded_angles[5] = angulo_garra
                        
                    # Enviar físicamente al robot si cambió significativamente
                    if abs(angulo_garra - self._last_sent_claw_angle) > 1.0:
                        servo_positions = CartesianPidCompensator.angulos_robotang(*self._last_commanded_angles)
                        self._enviar_robot(servo_positions)
                        self._update_graph_with_angles(self._last_commanded_angles)
                        self._last_sent_claw_angle = angulo_garra

                self.joint_update.emit(self._last_commanded_angles)
                continue 

            # Procesar el trabajo
            print(f"[DEBUG] Procesando trabajo: {work}")
            if work[0] == 'execute_target':
                _, tx, ty, tz = work
                self._run_pid_sequence(tx, ty, tz)
            elif work[0] == 'execute_pid_only':
                _, target, limites, max_iter, tol, t_start, angulo_garra = work
                if t_start is None:
                    t_start = time.time()
                self._pid_control_loop(target, limites, max_iter=max_iter, tolerancias=tol, t_start=t_start, angulo_garra=angulo_garra)
                self.movement_finished.emit()
            elif work[0] == 'direct_move':
                print(f"[DEBUG] Ejecutando movimiento directo a {work[1]}")
                _, positions = work
                # Emitir ángulos para la simulación antes de convertir a PWM
                self.joint_update.emit(positions)
                servo_positions = CartesianPidCompensator.angulos_robotang(*positions)
                self._enviar_robot(servo_positions)
                self._update_graph_with_angles(positions)
                self._last_commanded_angles = positions

            elif work[0] == 'send_home':
                home_pos = [0, -45, 120, 0, 30, 0]
                # Emitir ángulos para la simulación antes de convertir a PWM
                self.joint_update.emit(home_pos)
                home_servos = CartesianPidCompensator.angulos_robotang(*home_pos)
                self._enviar_robot(home_servos)
                self._update_graph_with_angles(home_pos)
                self._last_commanded_angles = home_pos
                # Emitir señal para re-habilitar inputs tras el reinicio
                self.input_enabled.emit()

            elif work[0] == 'stop':
                break

        self._telemetry_running = False
        telemetry_thread.join(timeout=2)
        self._close_serial()
