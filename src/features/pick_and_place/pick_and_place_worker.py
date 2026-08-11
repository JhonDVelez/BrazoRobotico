"""
Módulo que orquesta el PickAndPlaceWorker utilizando la nueva secuencia de 15 pasos.
"""

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer
from src.features.pick_and_place.pick_place_states import PickPlaceState
from src.features.pick_and_place.pick_place_state_machine import PickPlaceStateMachine
from src.features.pick_and_place.logic.context import PickPlaceContext
from src.services.data.utils.conversions import angulos_robotang, robotang_angulos
from src.services.robot.pid_service import PidService
import numpy as np

class PickAndPlaceWorker(QObject):
    action_request = pyqtSignal(dict)
    sequence_completed = pyqtSignal()
    sequence_failed = pyqtSignal(str)

    def __init__(self, kinematics_controller=None):
        super().__init__()
        self.context = PickPlaceContext()
        self.kinematics_controller = kinematics_controller
        self._sm = PickPlaceStateMachine(on_state_change=self._on_state_change)
        self.pid_service = PidService(self._read_positions, self._enviar_robot, self.action_request, self._dummy_signal)
        self._check_timer = QTimer()
        self._check_timer.setSingleShot(False)

    def update_gains_from_panel(self):
        if self.kinematics_controller:
            gains = self.kinematics_controller.get_widget().get_pid_gains()
            self.update_pid_gains(gains)

    def _dummy_signal(self, *args): pass # Placeholder

    def _enviar_robot(self, servos):
        self.action_request.emit({'type': 'move', 'target': servos})

    def _read_positions(self):
        return self.context.current_feedback or [0]*6

    @pyqtSlot(dict)
    def on_poses_from_camera(self, poses):
        self.context.sphere_poses.update(poses)

    def _on_state_change(self, state_name):
        handlers = {
            PickPlaceState.HOME1_MOVE.value: self._enter_home1_move,
            PickPlaceState.HOME1_VALIDATE.value: self._enter_home1_validate,
            PickPlaceState.HOME2_MOVE.value: self._enter_home2_move,
            PickPlaceState.HOME2_VALIDATE.value: self._enter_home2_validate,
            PickPlaceState.PID_HOME.value: self._enter_pid_home,
            PickPlaceState.PICK_APPROACH.value: self._enter_pick_approach,
            PickPlaceState.PICK_DOWN.value: self._enter_pick_down,
            PickPlaceState.PICK_GRASP.value: self._enter_pick_grasp,
            PickPlaceState.RETRACT_TO_PID_HOME.value: self._enter_retract_to_pid_home,
            PickPlaceState.PLACE_APPROACH.value: self._enter_place_approach,
            PickPlaceState.PLACE_DOWN.value: self._enter_place_down,
            PickPlaceState.PLACE_RELEASE.value: self._enter_place_release,
            PickPlaceState.RETRACT_TO_PLACE_ABOVE.value: self._enter_retract_to_place_above,
            PickPlaceState.RETRACT_FROM_PLACE.value: self._enter_retract_from_place,
            PickPlaceState.FINAL_SEQ_HOME.value: self._enter_final_seq_home,
            PickPlaceState.FINAL_SEQ_HOME2.value: self._enter_final_seq_home2,
            PickPlaceState.FINAL_SEQ_HOME1.value: self._enter_final_seq_home1,
        }
        handler = handlers.get(state_name)
        if handler: handler()

    def _enter_home1_move(self):
        servos = angulos_robotang(0,0,0,0,0,0)
        self._enviar_robot(servos)
        self._sm.home1_done()

    def _enter_home1_validate(self):
        self._check_timer.timeout.connect(self._check_home1)
        self._check_timer.start(500)
    
    def _check_home1(self):
        if self.validar_angulos([0,0,0,0,0,0]):
            self._check_timer.stop()
            self._check_timer.timeout.disconnect(self._check_home1)
            self._sm.home1_validated()
            
    def _enter_home2_move(self):
        tam = self.context.tamano_seleccionado if self.context.tamano_seleccionado else 30
        angulo_garra = self.calcular_angulo_garra(tam)
        servos = angulos_robotang(0, -45, 120, 0, 30, angulo_garra)
        self._enviar_robot(servos)
        self._sm.home2_done()

    def _enter_home2_validate(self):
        self._check_timer.timeout.connect(self._check_home2)
        self._check_timer.start(500)
    
    def _check_home2(self):
        tam = self.context.tamano_seleccionado if self.context.tamano_seleccionado else 30
        ang_garra = self.calcular_angulo_garra(tam)
        if self.validar_angulos([0,-45,120,0,30,ang_garra]):
            self._check_timer.stop()
            self._check_timer.timeout.disconnect(self._check_home2)
            self._sm.home2_validated()

    def _enter_pid_home(self):
        tx, ty, tz = 185, 0, 170
        tz = self.corregir_z(tx, ty, tz)
        tx, ty = self.corregir_xy(tx, ty)
        self.pid_service.pid_control_loop([tx, ty, tz], [(-10, 10), (-50, -40), (0, 130), (0, 120)])
        self._sm.pid_home_done()
        
    def _enter_pick_approach(self):
        x, y, z = self.context.pick_target
        z += 50
        self.pid_service.pid_control_loop([x, y, z], [(-100, 100), (-90, 90), (-130, 130), (-90, 120)])
        self._sm.pick_approach_done()
    
    def _enter_pick_down(self):
        x, y, z = self.context.pick_target
        self.pid_service.pid_control_loop([x, y, z], [(-100, 100), (-90, 90), (-130, 130), (-90, 120)])
        self._sm.pick_down_done()

    def _enter_pick_grasp(self):
        from src.features.kinematics.coordinate_correction import apertura_de_garra
        ang = apertura_de_garra(20)
        self.pid_service.set_claw_value(20)
        self._sm.pick_grasp_done()

    def _enter_retract_to_pid_home(self):
        self._enter_pid_home()
        self._sm.retract_done()
    
    def _enter_place_approach(self):
        x, y, z = self.context.place_target_coords
        z += 50
        self.pid_service.pid_control_loop([x, y, z], [(-100, 100), (-90, 90), (-130, 130), (-90, 120)])
        self._sm.place_approach_done()
    
    def _enter_place_down(self):
        x, y, z = self.context.place_target_coords
        self.pid_service.pid_control_loop([x, y, z], [(-100, 100), (-90, 90), (-130, 130), (-90, 120)])
        self._sm.place_down_done()

    def _enter_place_release(self):
        tam = self.context.tamano_seleccionado if self.context.tamano_seleccionado else 30
        target_ang = tam + 15
        self._sm.place_release_done()

    def _enter_retract_to_place_above(self):
        x, y, z = self.context.place_target_coords
        z += 50
        self.pid_service.pid_control_loop([x, y, z], [(-100, 100), (-90, 90), (-130, 130), (-90, 120)])
        self._sm.place_release_done()

    def _enter_retract_from_place(self):
        self._enter_pid_home()
        self._sm.retract_from_place_to_pid()
    
    def _enter_final_seq_home(self):
        self._enter_home2_move()
        self._sm.final_home_done()
    
    def _enter_final_seq_home2(self):
        self._enter_home2_validate()
    
    def _enter_final_seq_home1(self):
        self._enter_home1_move()
        self._sm.final_home1_done()

    def validar_angulos(self, destino_angulos):
        current_pwm = self._read_positions()
        current_angles = robotang_angulos(*current_pwm)
        return all(abs(current_angles[i] - destino_angulos[i]) < 5 for i in range(len(destino_angulos)))

    def corregir_xy(self, x, y):
        from src.features.kinematics.coordinate_correction import corregir_xy as corr_xy
        return corr_xy(x, y)

    def corregir_z(self, x, y, z):
        from src.features.kinematics.coordinate_correction import corregir_z as corr_z
        return corr_z(x, y, z)

    @pyqtSlot(str)
    def pick(self, color):
        self.update_gains_from_panel()
        self.context.selected_color = color
        self._sm.start_op()

    @pyqtSlot(dict)
    def place(self, coords):
        self.update_gains_from_panel()
        self.context.place_target_coords = coords
        self._sm.start_op()

    @pyqtSlot(list)
    def on_target_reached(self, _positions): pass
    @pyqtSlot(dict)
    def on_ik_ready(self, result): pass
    @pyqtSlot()
    def abort(self):
        if self.current_state_value != PickPlaceState.IDLE.value:
            self._sm.reset()
    def update_pid_gains(self, gains):
        # gains: {"kp": [x,y,z], "ki": [x,y,z], "kd": [x,y,z]}
        self.pid_service.set_pid_gains(gains['kp'], gains['ki'], gains['kd'])

    @pyqtSlot(list)
    def on_feedback_update(self, positions):
        self.context.current_feedback = positions
        # Emitir señal para graficación en tiempo real
        # Calculo rapido de cinematica directa para actualizar target de grafica
        from src.services.data.utils.conversions import robotang_angulos
        q_reales_deg = robotang_angulos(*positions)
        q_actual_rad = np.radians([q_reales_deg[0], q_reales_deg[1], q_reales_deg[2], q_reales_deg[4]])
        
        # Usamos el método de cinemática del PidService
        p_actual = self.pid_service._cinematica_directa(q_actual_rad)
        
        target = self.context.current_target or p_actual.tolist()
        self.action_request.emit({'type': 'graph_update', 'pos': p_actual.tolist(), 'target': target})

    @property
    def current_state_value(self):
        return self._sm.current_state_value
