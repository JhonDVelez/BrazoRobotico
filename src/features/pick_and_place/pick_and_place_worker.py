"""
Módulo que orquesta el PickAndPlaceWorker utilizando la nueva secuencia de 15 pasos.
"""

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer
import threading
from src.features.pick_and_place.pick_place_states import PickPlaceState
from src.features.pick_and_place.pick_place_state_machine import PickPlaceStateMachine
from src.features.pick_and_place.logic.context import PickPlaceContext
from src.services.data.utils.conversions import robotang_angulos
import numpy as np

class PickAndPlaceWorker(QObject):
    action_request = pyqtSignal(dict)
    sequence_completed = pyqtSignal()
    sequence_failed = pyqtSignal(str)
    status_message_updated = pyqtSignal(str)
    pid_iteration = pyqtSignal(float, list, list)

    def __init__(self, kinematics_controller=None):
        super().__init__()
        self.context = PickPlaceContext()
        self.kinematics_controller = kinematics_controller
        self._sm = PickPlaceStateMachine(on_state_change=self._on_state_change)
        
        # Telemetry management
        self._telemetry_lock = threading.Lock()
        self._current_pos = [0.0] * 6
        
        # Conectar al KinematicsWorker si está disponible
        if self.kinematics_controller:
            self.kw = self.kinematics_controller.get_worker()
            self.kw.movement_finished.connect(self._on_movement_finished)
            self.kw.pid_iteration.connect(self.pid_iteration.emit)
        else:
            self.kw = None

        self._check_timer = QTimer()
        self._check_timer.setSingleShot(False)
        self.TIEMPO_PASO_GARRA = 1000

    def _read_positions(self):
        with self._telemetry_lock:
            return list(self._current_pos)


    @pyqtSlot(dict)
    def on_poses_from_camera(self, poses):
        self.context.sphere_poses.update(poses)

    def _on_state_change(self, state_name):
        print(f"[DEBUG] >>> [StateMachine] Entering State: {state_name}")
        handlers = {
            PickPlaceState.HOME1_MOVE.value: self._enter_home1_move,
            PickPlaceState.HOME1_VALIDATE.value: self._enter_home1_validate,
            PickPlaceState.HOME2_MOVE.value: self._enter_home2_move,
            PickPlaceState.HOME2_VALIDATE.value: self._enter_home2_validate,
            PickPlaceState.PID_HOME.value: self._enter_pid_home,
            PickPlaceState.PICK_APPROACH.value: self._enter_pick_approach,
            PickPlaceState.PICK_DOWN.value: self._enter_pick_down,
            PickPlaceState.PICK_GRASP.value: self._enter_pick_grasp,
            PickPlaceState.RETRACT_LIFT.value: self._enter_retract_lift,
            PickPlaceState.RETRACT_TO_PID_HOME.value: self._enter_retract_to_pid_home_pick,
            PickPlaceState.PLACE_APPROACH.value: self._enter_place_approach,
            PickPlaceState.PLACE_DOWN.value: self._enter_place_down,
            PickPlaceState.PLACE_RELEASE.value: self._enter_place_release,
            PickPlaceState.RETRACT_TO_PLACE_ABOVE.value: self._enter_retract_to_place_above,
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
            """Espera no bloqueante de 2.5 segundos antes de disparar el callback."""
            # Asegurarse de que el timer esté desconectado antes de iniciar
            try:
                self._check_timer.timeout.disconnect()
            except Exception:
                pass
                
            self._check_timer.setSingleShot(True)
            self._check_timer.timeout.connect(callback)
            self._check_timer.start(2500)

    # Funcion para abrir o cerrar la garra en la posicion actual
    def _enviar_comando_movimiento(self, apertura):
        # 1. Obtener ángulos actuales
        if self.kw:
            current_pwm = self.kw._read_positions()
        else:
            current_pwm = self._read_positions()
        
        current_angles = list(robotang_angulos(*current_pwm))
        
        # 2. Calcular nuevo ángulo de la garra
        ang_garra = self.calcular_angulo_garra(apertura)
        
        # 3. Modificar y enviar movimiento
        current_angles[5] = ang_garra
        
        if self.kw:
            self.kw.disable_gripper_control()
            self.kw.execute_direct_move(current_angles)

    def _ejecutar_paso_apertura(self, apertura_actual, apertura_final, incremento):
        nueva_apertura = min(apertura_actual + incremento, apertura_final)
        
        # Ejecutar movimiento físico sin espera de asentamiento
        self._enviar_comando_movimiento(nueva_apertura)
        
        if nueva_apertura < apertura_final:
            QTimer.singleShot(self.TIEMPO_PASO_GARRA, lambda: self._ejecutar_paso_apertura(nueva_apertura, apertura_final, incremento))
        else:
            self._sm.place_release_done()

    # ESTOS SON LOS METODOS QUE SE EJECUTAN AL ENTRAR A CADA ESTADO DE LA MAQUINA DE ESTADOS

    # Estado 1 home1_move: Mueve el brazo a la posición neutral inicial.
    def _enter_home1_move(self):
        print("[DEBUG] PickAndPlaceWorker Entering HOME1_MOVE")
        servos = [0,0,0,0,0,0]
        if self.kw:
            self.kw.execute_direct_move(servos)
        self._enter_home1_validate()
    # Validación de home1_move: Verifica que el brazo esté en la posición neutral inicial.
    def _enter_home1_validate(self):
        self._wait_for_settle(lambda: QTimer.singleShot(0, self._sm.home1_done))
        self._sm.home1_validated()

    def _enter_waiting_for_input(self):
        if self.context.ik_target is None:
            self.status_message_updated.emit("Selecciona objeto y su color")
        else:
            self.status_message_updated.emit("Selecciona destino en el plano")

    # Estado 2 home2_move: Mueve el brazo a la posición neutral de espera para pick and place.
    def _enter_home2_move(self):
        tam = self.context.tamano_seleccionado if self.context.tamano_seleccionado else 30
        angulo_garra = self.calcular_angulo_garra(tam + 20)
        servos = [0, -45, 120, 0, 30, angulo_garra]
        if self.kw:
            self.kw.execute_direct_move(servos)
        self._enter_home2_validate()
    # Validación de home2_move: Verifica que el brazo esté en la posición neutral de espera.
    def _enter_home2_validate(self):
        self._wait_for_settle(lambda: QTimer.singleShot(0, self._sm.home2_done))
        self._sm.home2_validated()
    # Estado 3 pid_home: Mueve el brazo a la posición de home usando PID.
    def _enter_pid_home(self, angulo_garra_custom=None):
        print("Ejecutando PID Home ")
        tam = self.context.tamano_seleccionado if self.context.tamano_seleccionado else 30
        print("Tamano seleccionado:", tam)
        ang_garra = angulo_garra_custom if angulo_garra_custom is not None else self.calcular_angulo_garra(tam + 20)
        print("Angulo garra calculado:", ang_garra)
        self.update_gains_from_panel()
        print("Gains actualizados desde el panel.")
        tx, ty, tz = 185, 0, 170
        tz = self.corregir_z(tx, ty, tz)
        tx, ty = self.corregir_xy(tx, ty)
        print(f"PID Home Target: x={tx}, y={ty}, z={tz}, ang_garra={ang_garra}")
        limites_home = [(-10, 10), (-50, -40), (0, 130), (0, 120)]
        print(f"Limites para PID Home: {limites_home}")
        if self.kw:
            print("Ejecutando PID Home con KinematicsWorker.")
            self.kw.execute_pid_only([tx, ty, tz], limites_home, angulo_garra=ang_garra)
    
    # Estado 4 pick_approach: Mueve el brazo sobre la esfera detectada.    
    def _enter_pick_approach(self, angulo_garra_custom=None):
        tam = self.context.tamano_seleccionado if self.context.tamano_seleccionado else 30
        ang_garra = angulo_garra_custom if angulo_garra_custom is not None else self.calcular_angulo_garra(tam + 20)
        self.update_gains_from_panel()
        x, y, z = self.context.ik_target
        x1 = y
        y1 = x
        x = x1 + 115
        y = y1 + 15
        z = z + 70
        z = self.corregir_z(x, y, z)
        x, y = self.corregir_xy(x, y)
        limites_target = [(-100, 100), (-90, 90), (-130, 130), (-90, 120)]
        print("Ejecutando Pick Approach con target:", [x, y, z], "y angulo garra:", ang_garra)
        if self.kw:
            self.kw.execute_pid_only([x, y, z], limites_target, angulo_garra=ang_garra)

    # Estado 5 pick_down: Baja el brazo hasta la esfera para recogerla.
    def _enter_pick_down(self):
        tam = self.context.tamano_seleccionado if self.context.tamano_seleccionado else 30
        ang_garra = self.calcular_angulo_garra(tam + 20)
        self.update_gains_from_panel()
        x, y, z = self.context.ik_target
        x1 = y
        y1 = x
        x = x1 + 115
        y = y1 + 15
        z = tam/2
        z = self.corregir_z(x, y, z)
        x, y = self.corregir_xy(x, y)
        limites_target = [(-100, 100), (-90, 90), (-130, 130), (-90, 120)]
        if self.kw:
            self.kw.execute_pid_only([x, y, z], limites_target, angulo_garra=ang_garra)

    # Estado 6 pick_grasp: Cierra la garra para sujetar la esfera.
    def _enter_pick_grasp(self):
        tam = self.context.tamano_seleccionado if self.context.tamano_seleccionado else 30
        apertura = tam - 20
        self._enviar_comando_movimiento(apertura)
        self._wait_for_settle(lambda: (QTimer.singleShot(0, self._sm.pick_grasp_done)))
    # Estado 7 retract_lift: Eleva el brazo con la esfera sujeta.
    def _enter_retract_lift(self):
        print("[DEBUG] Entering RETRACT_LIFT")
        tam = self.context.tamano_seleccionado if self.context.tamano_seleccionado else 30
        ang_garra = self.calcular_angulo_garra(tam - 20)
        self.update_gains_from_panel()
        x, y, z = self.context.ik_target
        x1 = y
        y1 = x
        x = x1 + 115
        y = y1 + 15
        z = z + 70
        z = self.corregir_z(x, y, z)
        x, y = self.corregir_xy(x, y)
        limites_target = [(-100, 100), (-90, 90), (-130, 130), (-90, 120)]
        if self.kw:
            self.kw.execute_pid_only([x, y, z], limites_target, angulo_garra=ang_garra)

    # Estado 8 retract_to_pid_home: Mueve el brazo a la posición de home usando PID después de recoger la esfera.
    def _enter_retract_to_pid_home_pick(self):
        print("[DEBUG] Entering RETRACT_TO_PID_HOME_PICK")
        tam = self.context.tamano_seleccionado if self.context.tamano_seleccionado else 30
        ang_garra = self.calcular_angulo_garra(tam - 20)
        self.update_gains_from_panel()
        tx, ty, tz = 185, 0, 170
        tz = self.corregir_z(tx, ty, tz)
        tx, ty = self.corregir_xy(tx, ty)
        limites_home = [(-10, 10), (-50, -40), (0, 130), (0, 120)]
        if self.kw:
            self.kw.execute_pid_only([tx, ty, tz], limites_home, angulo_garra=ang_garra)
    # Estado 9 place_approach: Mueve el brazo sobre la posición de colocación seleccionada, cabe aclarar que aqui se espera la entrada del destino (place) seleccionada por el usuario para continuar la maquina de estados.
    def _enter_place_approach(self, angulo_garra_custom=None):
        tam = self.context.tamano_seleccionado if self.context.tamano_seleccionado else 30
        ang_garra = angulo_garra_custom if angulo_garra_custom is not None else self.calcular_angulo_garra(tam - 20)
        self.update_gains_from_panel()
        if self.context.place_target_coords is None:
            print("[ERROR] place_target_coords is None in _enter_place_approach")
            self.sequence_failed.emit('No se ha seleccionado posición de colocación (place)')
            self._sm.reset()
            return
        x, y, z = self.context.place_target_coords
        x1 = y
        y1 = x
        x = x1 + 115
        y = y1 + 15
        z = z + 70
        z = self.corregir_z(x, y, z)
        x, y = self.corregir_xy(x, y)
        print("Ejecutando ")
        limites_target = [(-100, 100), (-90, 90), (-130, 130), (-90, 120)]
        if self.kw:
            self.kw.execute_pid_only([x, y, z], limites_target, angulo_garra=ang_garra)
    # Estado 10 place_down: Baja el brazo hasta la posición de colocación para soltar la esfera.
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
        x1 = y
        y1 = x
        x = x1 + 115
        y = y1 + 15
        z = tam/2
        z = self.corregir_z(x, y, z)
        x, y = self.corregir_xy(x, y)
        print(f"[DEBUG] PID Target (PLACE_DOWN): x={x}, y={y}, z={z}")
        limites_target = [(-100, 100), (-90, 90), (-130, 130), (-90, 120)]
        if self.kw:
            self.kw.execute_pid_only([x, y, z], limites_target, angulo_garra=ang_garra)
    # Estado 11 place_release: Abre la garra lentamente para soltar la esfera en la posición de colocación.
    def _enter_place_release(self):
        tam = self.context.tamano_seleccionado if self.context.tamano_seleccionado else 30
        apertura_total = tam + 20
        apertura_inicial = tam - 20
        # Iniciar la secuencia no bloqueante
        self._ejecutar_paso_apertura(apertura_inicial, apertura_total, 10)
    # Estado 12 retract_to_place_above: Eleva el brazo después de soltar la esfera.
    def _enter_retract_to_place_above(self):
        print("[DEBUG] Entering RETRACT_TO_PLACE_ABOVE")
        tam = self.context.tamano_seleccionado if self.context.tamano_seleccionado else 30
        ang_garra = self.calcular_angulo_garra(tam + 20)
        self.update_gains_from_panel()
        if self.context.place_target_coords is None:
            self._sm.reset()
            return
        x, y, z = self.context.place_target_coords
        x1 = y
        y1 = x
        x = x1 + 115
        y = y1 + 15
        z = z + 70
        z = self.corregir_z(x, y, z)
        x, y = self.corregir_xy(x, y)
        limites_target = [(-100, 100), (-90, 90), (-130, 130), (-90, 120)]
        if self.kw:
            self.kw.execute_pid_only([x, y, z], limites_target, angulo_garra=ang_garra)

    # Estado 13 retract_from_place: Mueve el brazo a la posición de home usando PID
    def _enter_retract_from_place(self):
        print("[DEBUG] Entering RETRACT_FROM_PLACE")
        tam = self.context.tamano_seleccionado if self.context.tamano_seleccionado else 30
        ang_garra = self.calcular_angulo_garra(tam + 20)
        self.update_gains_from_panel()
        tx, ty, tz = 185, 0, 170
        tz = self.corregir_z(tx, ty, tz)
        tx, ty = self.corregir_xy(tx, ty)
        limites_home = [(-10, 10), (-50, -40), (0, 130), (0, 120)]
        if self.kw:
            self.kw.execute_pid_only([tx, ty, tz], limites_home, angulo_garra=ang_garra)
    # Estado 14 final_seq_home: Mueve el brazo a la posición neutral home2
    def _enter_final_seq_home2(self):
        print("[DEBUG] Entering FINAL_SEQ_HOME2")
        tam = self.context.tamano_seleccionado if self.context.tamano_seleccionado else 30
        angulo_garra = self.calcular_angulo_garra(tam + 20)
        servos = [0, -45, 120, 0, 30, angulo_garra]
        if self.kw:
            self.kw.execute_direct_move(servos)
        self._wait_for_settle(lambda: QTimer.singleShot(0, self._sm.final_home2_done))

    # Estado 15 final_seq_home1: Mueve el brazo a la posición neutral home1
    def _enter_final_seq_home1(self):
        print("[DEBUG] Entering FINAL_SEQ_HOME1")
        servos = [0,0,0,0,0,0]
        if self.kw:
            self.kw.execute_direct_move(servos)
        self._wait_for_settle(lambda: QTimer.singleShot(0, self._sm.final_home1_done))
        self.sequence_completed.emit()

    def validar_angulos(self, destino_angulos):
        # 1. Usar la telemetría cruda directamente del KinematicsWorker
        if self.kw:
            current_pwm = self.kw._read_positions()
        else:
            current_pwm = self._read_positions()
            
        print(f"[DEBUG] Validating angles: Current PWM={current_pwm}")
        current_angles = robotang_angulos(*current_pwm)
        print(f"[DEBUG] Validating: Current={current_angles}, Target={destino_angulos}")
        
        # 2. Validar solo los primeros 5 motores (índices 0-4), ignorando el 6to (índice 5)
        return all(abs(current_angles[i] - destino_angulos[i]) < 5 for i in range(5))


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
        
        # Populating ik_target based on selected color
        if color in self.context.sphere_poses:
            pose_data = self.context.sphere_poses[color]
            if isinstance(pose_data, dict) and 'position' in pose_data:
                self.context.ik_target = pose_data['position']
                print(f"[DEBUG] Assigned ik_target: {self.context.ik_target}")
            else:
                self.context.ik_target = pose_data
                print(f"[WARNING] pose_data does not have 'position' key: {pose_data}")
        else:
            print(f"[ERROR] Color {color} not found in sphere_poses: {self.context.sphere_poses}")
        
        # Solo avanzar si la maquina de estados esta en espera de entrada o en reposo.
        if self._sm.current_state_value == PickPlaceState.WAITING_FOR_INPUT.value:
            self._sm.ready_to_home2()
        elif self._sm.current_state_value == PickPlaceState.IDLE.value:
            self._sm.start_op()
        else:
            # Si esta en otro estado (ej. HOME2_VALIDATE), ignoramos la solicitud
            # ya que la maquina de estados continuara automaticamente.
            pass

    @pyqtSlot(dict)
    def place(self, coords):
        print(f"[DEBUG] User input: Place {coords}")
        self.update_gains_from_panel()
        self.context.place_target_coords = coords
        
        # Solo avanzar si la maquina de estados esta en espera de entrada o en reposo.
        if self._sm.current_state_value == PickPlaceState.WAITING_FOR_INPUT.value:
            # Diferenciar si estamos esperando el inicio o esperando el destino de colocacion
            # Si ya pasamos por pick_grasp, deberíamos estar en estado de espera para colocar.
            # Una forma sencilla es chequear si ya tenemos un objetivo de pick asignado o si el estado anterior fue retract_to_pid_home
            # Como la maquina de estados no guarda historial, podemos inferir por el contexto.
            
            # Asumimos que si estamos en WAITING_FOR_INPUT y tenemos coordenadas de pick,
            # pero no estamos al inicio, entonces vamos a colocar.
            
            # Verificamos si es el primer input (inicio operacion) o segundo (colocacion)
            # Una forma robusta es revisar si la maquina ya pasó por el estado de agarre.
            
            # Si el robot ya ha realizado el agarre, entonces es una orden de 'place' real.
            if self.context.ik_target is not None:
                 self._sm.ready_to_place()
            else:
                 self._sm.ready_to_home2()
                 
        elif self._sm.current_state_value == PickPlaceState.IDLE.value:
            self._sm.start_op()
        else:
            pass

    @pyqtSlot()
    def _on_movement_finished(self):
        # Avanzar la maquina de estados segun el estado actual
        current = self.current_state_value
        print(f"[DEBUG] Movement finished. Current state: {current}")
        if current == PickPlaceState.PID_HOME.value:
            self._sm.pid_home_done()
        elif current == PickPlaceState.PICK_APPROACH.value:
            self._sm.pick_approach_done()
        elif current == PickPlaceState.PICK_DOWN.value:
            self._sm.pick_down_done()
        elif current == PickPlaceState.PICK_GRASP.value:
            print("[DEBUG] Pick grasp finished, triggering pick_grasp_done")
            self._sm.pick_grasp_done()
        elif current == PickPlaceState.RETRACT_LIFT.value:
            self._sm.retract_lift_done()
        elif current == PickPlaceState.RETRACT_TO_PID_HOME.value:
            self._sm.retract_done()
        elif current == PickPlaceState.PLACE_APPROACH.value:
            self._sm.place_approach_done()
        elif current == PickPlaceState.PLACE_DOWN.value:
            self._sm.place_down_done()
        elif current == PickPlaceState.RETRACT_TO_PLACE_ABOVE.value:
            self._sm.place_release_done() # place_release_done moves to RETRACT_TO_PLACE_ABOVE
        # Add more transitions if needed based on the StateMachine definitions


    @pyqtSlot(list)
    def on_target_reached(self, _positions): pass

    @pyqtSlot(dict)
    def on_ik_ready(self, result): pass
    @pyqtSlot()
    def abort(self):
        if self.current_state_value != PickPlaceState.IDLE.value:
            self._sm.reset()

    def stop_and_reset(self):
        """Detiene la secuencia y limpia el estado para un reseteo limpio."""
        if self.current_state_value != 'idle':
            self._sm.reset()
        self._check_timer.stop()
        self.context.reset()
        if self.kw:
            self.kw.execute_direct_move([0, 0, 0, 0, 0, 0])

    def update_pid_gains(self, gains):
        # gains: {"kp": [x,y,z], "ki": [x,y,z], "kd": [x,y,z]}
        if self.kw:
            self.kw.set_pid_gains(gains['kp'], gains['ki'], gains['kd'])

    def update_gains_from_panel(self):
        if self.kinematics_controller:
            widget = self.kinematics_controller.get_widget()
            gains = widget.get_pid_gains()
            self.kw.set_pid_gains(gains["kp"], gains["ki"], gains["kd"])

    def start_sequence(self):
        if self._sm.current_state_value == 'idle':
            self._sm.start_op()

    @pyqtSlot(list)
    def on_simulation_feedback_update(self, positions):
        # Simulation feedback often arrives in radians or specific units already.
        # Assuming simulation positions are already in radians for kinematics direct.
        with self._telemetry_lock:
            self._current_pos = list(positions)
        self.context.current_feedback = positions
        
    @pyqtSlot(list, list)
    def on_physical_feedback_update(self, positions, temperatures):
        # Hardware feedback arrives in raw PWM. Need to convert PWM -> Degrees -> Radians
        with self._telemetry_lock:
            self._current_pos = list(positions)
        self.context.current_feedback = positions


    @property
    def current_state_value(self):
        return self._sm.current_state_value
