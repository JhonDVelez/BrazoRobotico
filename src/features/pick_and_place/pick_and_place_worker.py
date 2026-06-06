"""
Modulo que orquesta el PickAndPlaceWorker unificando la logica de Pick y Place.
"""

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from src.features.pick_and_place.pick_place_states import PickPlaceState
from src.features.pick_and_place.pick_place_state_machine import PickPlaceStateMachine
from src.features.pick_and_place.logic.base_worker import BasePickPlaceLogic
from src.features.pick_and_place.logic.pick_sequence import PickSequenceLogic
from src.features.pick_and_place.logic.place_sequence import PlaceSequenceLogic


class PickAndPlaceWorker(QObject, BasePickPlaceLogic, PickSequenceLogic, PlaceSequenceLogic):
    """Worker que coordina la secuencia completa de Pick and Place.

    Hereda de Mixins especializados para mantener un codigo modular y legible.
    """

    action_request = pyqtSignal(dict)
    sequence_completed = pyqtSignal()
    sequence_failed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._sm = PickPlaceStateMachine(on_state_change=self._on_state_change)
        self._init_base_logic()

    @property
    def current_state_value(self):
        return self._sm.current_state_value

    def _on_state_change(self, state_name):
        """Rutea el evento de entrada a estado al manejador correspondiente en los Mixins."""
        handlers = {
            PickPlaceState.HOMING.value: self._enter_homing,
            PickPlaceState.COMPUTING_IK_ABOVE.value: self._enter_computing_ik_above,
            PickPlaceState.APPROACHING_ABOVE.value: self._enter_approaching_above,
            PickPlaceState.OPENING_GRIPPER.value: self._enter_opening_gripper,
            PickPlaceState.COMPUTING_IK.value: self._enter_computing_ik,
            PickPlaceState.APPROACHING.value: self._enter_approaching,
            PickPlaceState.GRASPING.value: self._enter_grasping,
            PickPlaceState.LIFTING.value: self._enter_lifting,
            PickPlaceState.COMPUTING_IK_PLACE_ABOVE.value: self._enter_computing_ik_place_above,
            PickPlaceState.APPROACHING_PLACE_ABOVE.value: self._enter_approaching_place_above,
            PickPlaceState.COMPUTING_IK_PLACE.value: self._enter_computing_ik_place,
            PickPlaceState.APPROACHING_PLACE.value: self._enter_approaching_place,
            PickPlaceState.RELEASING.value: self._enter_releasing,
            PickPlaceState.RETURNING_HOME.value: self._enter_returning_home,
        }
        handler = handlers.get(state_name)
        if handler:
            handler()

    # --- Triggers externos ---

    @pyqtSlot(str)
    def pick(self, color):
        if self._sm.idle not in self._sm.configuration:
            return
        self._selected_color = color
        self._sm.start_pick()

    @pyqtSlot(dict)
    def place(self, coords):
        if self._sm.idle not in self._sm.configuration:
            return
        self._place_target_coords = coords
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

        self._ik_target = target

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
        self._sphere_poses.update(poses)

    @pyqtSlot()
    def abort(self):
        if self.current_state_value == PickPlaceState.IDLE.value:
            return
        self._clear_state()
        self._sm.reset()
        self.sequence_failed.emit('Secuencia cancelada')

    @pyqtSlot(list)
    def on_feedback_update(self, positions):
        if len(positions) < 6:
            return
        if abs(positions[0]) < 140:
            mapped = [-x+150 if i in (4, 5) else x +
                      150 for i, x in enumerate(positions)]
        else:
            mapped = positions

        self._current_feedback = mapped

        if self._last_positions is not None:
            max_delta = max(abs(p - lp)
                            for p, lp in zip(mapped, self._last_positions))
            if max_delta <= self._MOVEMENT_TOLERANCE:
                if self._current_target is not None:
                    max_error = max(abs(f - t)
                                    for f, t in zip(mapped, self._current_target))
                    if max_error < self._SUCCESS_THRESHOLD:
                        if self.current_state_value != PickPlaceState.GRASPING.value:
                            self._advance_state()
                            self._last_positions = mapped
                            return
            if max_delta > self._MOVEMENT_TOLERANCE:
                if self._state_stall_timer.isActive():
                    self._state_stall_timer.start(self._STALL_TIMEOUT_MS)

        self._last_positions = mapped

    def _handle_movement_finished(self):
        current = self.current_state_value
        if current in (PickPlaceState.IDLE.value, PickPlaceState.COMPUTING_IK.value, PickPlaceState.COMPUTING_IK_PLACE.value):
            return

        if self._current_feedback is None or self._current_target is None:
            return

        feedback = self._current_feedback.tolist() if hasattr(
            self._current_feedback, 'tolist') else self._current_feedback

        if current == PickPlaceState.GRASPING.value:
            current_gripper_rel = feedback[5] - 150.0
            if current_gripper_rel >= self._GRIPPER_MAX_CLOSED - 0.5:
                self._abort_to_home(
                    "Fallo al sujetar objeto: Pinza cerró completamente")
                return
            self._gripper_closed = current_gripper_rel
            self._advance_state()
            return

        max_error = max(abs(f - t)
                        for f, t in zip(feedback, self._current_target))
        if max_error < self._ERROR_THRESHOLD:
            self._advance_state()
        else:
            self._abort_to_home(
                f"Stall crítico en {current} (Error: {max_error:.2f} deg)")

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

    def _abort_to_home(self, reason="Error critico: Movimiento bloqueado o incompleto"):
        self._state_stall_timer.stop()
        feedback = self._current_feedback.tolist() if hasattr(
            self._current_feedback, 'tolist') else self._current_feedback
        current_gripper = feedback[5] if feedback is not None else 150
        home_target = self._relative_to_servo([0, 0, 0, 0, 90, 0])
        home_target[5] = current_gripper
        self.action_request.emit({
            'type': 'move',
            'target': home_target,
            'description': 'Abortando: Regresando a neutral por error critico'
        })
        self._clear_state()
        self._sm.reset()
        self.sequence_failed.emit(reason)
