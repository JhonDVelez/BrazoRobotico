"""
Módulo que orquesta el PickAndPlaceWorker utilizando composición de ejecutores.
"""

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer
from src.features.pick_and_place.pick_place_states import PickPlaceState
from src.features.pick_and_place.pick_place_state_machine import PickPlaceStateMachine
from src.features.pick_and_place.logic.context import PickPlaceContext
from src.features.pick_and_place.logic.pick_executor import PickExecutor
from src.features.pick_and_place.logic.place_executor import PlaceExecutor


class PickAndPlaceWorker(QObject):
    """Worker que coordina la secuencia completa de Pick and Place.

    Utiliza composición para delegar la lógica de ejecución a objetos especializados,
    actuando como orquestador central de señales y estados.
    """

    action_request = pyqtSignal(dict)
    sequence_completed = pyqtSignal()
    sequence_failed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        # Contexto de datos compartido
        self.context = PickPlaceContext()
        
        # Ejecutores de lógica (Composición)
        self.pick_executor = PickExecutor(self, self.context)
        self.place_executor = PlaceExecutor(self, self.context)
        
        # Maquina de estados
        self._sm = PickPlaceStateMachine(on_state_change=self._on_state_change)
        
        # Timer de estancamiento (Orquestación)
        self._state_stall_timer = QTimer()
        self._state_stall_timer.setSingleShot(True)
        self._state_stall_timer.timeout.connect(self._on_state_timeout)

    @property
    def current_state_value(self):
        return self._sm.current_state_value

    def _on_state_change(self, state_name):
        """Rutea el evento de entrada a estado al ejecutor correspondiente."""
        handlers = {
            # Pick Sequence
            PickPlaceState.HOMING.value: self.pick_executor.enter_homing,
            PickPlaceState.COMPUTING_IK_ABOVE.value: self.pick_executor.enter_computing_ik_above,
            PickPlaceState.APPROACHING_ABOVE.value: self.pick_executor.enter_approaching_above,
            PickPlaceState.OPENING_GRIPPER.value: self.pick_executor.enter_opening_gripper,
            PickPlaceState.COMPUTING_IK.value: self.pick_executor.enter_computing_ik,
            PickPlaceState.APPROACHING.value: self.pick_executor.enter_approaching,
            PickPlaceState.GRASPING.value: self.pick_executor.enter_grasping,
            PickPlaceState.LIFTING.value: self.pick_executor.enter_lifting,
            
            # Place Sequence
            PickPlaceState.COMPUTING_IK_PLACE_ABOVE.value: self.place_executor.enter_computing_ik_place_above,
            PickPlaceState.APPROACHING_PLACE_ABOVE.value: self.place_executor.enter_approaching_place_above,
            PickPlaceState.COMPUTING_IK_PLACE.value: self.place_executor.enter_computing_ik_place,
            PickPlaceState.APPROACHING_PLACE.value: self.place_executor.enter_approaching_place,
            PickPlaceState.RELEASING.value: self.place_executor.enter_releasing,
            PickPlaceState.RETURNING_HOME.value: self.place_executor.enter_returning_home,
        }
        handler = handlers.get(state_name)
        if handler:
            handler()

    # --- Triggers externos (Slots) ---

    @pyqtSlot(str)
    def pick(self, color):
        if self._sm.idle not in self._sm.configuration:
            return
        self.context.selected_color = color
        self._sm.start_pick()

    @pyqtSlot(dict)
    def place(self, coords):
        if self._sm.idle not in self._sm.configuration:
            return
        self.context.place_target_coords = coords
        self._sm.start_place()

    @pyqtSlot(list)
    def on_target_reached(self, _positions):
        self._state_stall_timer.stop()
        self._handle_movement_finished()

    @pyqtSlot(dict)
    def on_ik_ready(self, result):
        current = self.current_state_value
        computing_states = (
            PickPlaceState.COMPUTING_IK_ABOVE.value,
            PickPlaceState.COMPUTING_IK.value,
            PickPlaceState.COMPUTING_IK_PLACE_ABOVE.value,
            PickPlaceState.COMPUTING_IK_PLACE.value
        )
        if current not in computing_states:
            return

        target = result.get('target')
        if not target:
            self._fail('IK no encontro solucion valida')
            return

        self.context.ik_target = target

        if current == PickPlaceState.COMPUTING_IK_ABOVE.value:
            self._sm.ik_computed_above()
        elif current == PickPlaceState.COMPUTING_IK.value:
            self._sm.ik_computed()
        elif current == PickPlaceState.COMPUTING_IK_PLACE_ABOVE.value:
            self._sm.ik_computed_place_above()
        elif current == PickPlaceState.COMPUTING_IK_PLACE.value:
            self._sm.ik_computed_place()

    @pyqtSlot(dict)
    def on_poses_from_camera(self, poses):
        self.context.sphere_poses.update(poses)

    @pyqtSlot()
    def abort(self):
        if self.current_state_value == PickPlaceState.IDLE.value:
            return
        self._clear_state()
        self._sm.reset()
        self.sequence_failed.emit('Secuencia cancelada')

    @pyqtSlot(list)
    def on_feedback_update(self, positions):
        """Maneja la telemetría para detectar llegada a objetivo por stall o precisión."""
        if len(positions) < 6:
            return
            
        # Mapeo de feedback si es necesario
        if abs(positions[0]) < 140:
            mapped = [-x+150 if i in (4, 5) else x + 150 for i, x in enumerate(positions)]
        else:
            mapped = positions

        self.context.current_feedback = mapped

        if self.context.last_positions is not None:
            max_delta = max(abs(p - lp) for p, lp in zip(mapped, self.context.last_positions))
            if max_delta <= self.context.MOVEMENT_TOLERANCE:
                if self.context.current_target is not None:
                    max_error = max(abs(f - t) for f, t in zip(mapped, self.context.current_target))
                    if max_error < self.context.SUCCESS_THRESHOLD:
                        if self.current_state_value != PickPlaceState.GRASPING.value:
                            self._advance_state()
                            self.context.last_positions = mapped
                            return
            if max_delta > self.context.MOVEMENT_TOLERANCE:
                if self._state_stall_timer.isActive():
                    self._state_stall_timer.start(self.context.STALL_TIMEOUT_MS)

        self.context.last_positions = mapped

    # --- Orquestación Interna ---

    def _start_stall_timer(self):
        self.context.last_positions = None
        self._state_stall_timer.start(self.context.STALL_TIMEOUT_MS)

    def _on_state_timeout(self):
        self._handle_movement_finished()

    def _handle_movement_finished(self):
        current = self.current_state_value
        if current in (PickPlaceState.IDLE.value, PickPlaceState.COMPUTING_IK.value, PickPlaceState.COMPUTING_IK_PLACE.value):
            return

        if self.context.current_feedback is None or self.context.current_target is None:
            return

        fb = self.context.current_feedback
        feedback = fb.tolist() if hasattr(fb, 'tolist') else fb

        if current == PickPlaceState.GRASPING.value:
            current_gripper_rel = feedback[5] - 150.0
            if current_gripper_rel >= self.context.gripper_max_closed - 0.5:
                self._abort_to_home("Fallo al sujetar objeto: Pinza cerró completamente")
                return
            self.context.gripper_closed = current_gripper_rel
            self._advance_state()
            return

        max_error = max(abs(f - t) for f, t in zip(feedback, self.context.current_target))
        if max_error < self.context.ERROR_THRESHOLD:
            self._advance_state()
        else:
            self._abort_to_home(f"Stall crítico en {current} (Error: {max_error:.2f} deg)")

    def _advance_state(self):
        self._state_stall_timer.stop()
        current = self.current_state_value
        transitions = {
            PickPlaceState.HOMING.value: self._sm.homing_done,
            PickPlaceState.APPROACHING_ABOVE.value: self._sm.above_reached,
            PickPlaceState.OPENING_GRIPPER.value: self._sm.gripper_opened,
            PickPlaceState.APPROACHING.value: self._sm.close_gripper,
            PickPlaceState.GRASPING.value: self._sm.grasp_done,
            PickPlaceState.LIFTING.value: self._on_lift_complete,
            PickPlaceState.APPROACHING_PLACE_ABOVE.value: self._sm.above_place_reached,
            PickPlaceState.APPROACHING_PLACE.value: self._sm.place_reached,
            PickPlaceState.RELEASING.value: self._sm.gripper_released,
            PickPlaceState.RETURNING_HOME.value: self._on_home_reached,
        }
        transition = transitions.get(current)
        if transition:
            transition()

    def _on_lift_complete(self):
        self._sm.lift_complete()
        self.sequence_completed.emit()

    def _on_home_reached(self):
        self._sm.home_reached()
        self.sequence_completed.emit()

    def _fail(self, reason):
        self._clear_state()
        self._sm.reset()
        self.sequence_failed.emit(reason)

    def _clear_state(self):
        self.context.reset()
        self._state_stall_timer.stop()

    def _abort_to_home(self, reason="Error crítico"):
        self._state_stall_timer.stop()
        fb = self.context.current_feedback
        current_gripper = fb[5] if fb is not None else 150
        home_target = [float(v + 150.0) for v in [0, 0, 0, 0, 90, 0]]
        home_target[5] = current_gripper
        self.action_request.emit({
            'type': 'move',
            'target': home_target,
            'description': 'Abortando: Regresando a neutral por error crítico'
        })
        self._clear_state()
        self._sm.reset()
        self.sequence_failed.emit(reason)
