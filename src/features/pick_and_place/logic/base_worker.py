"""
Modulo que define la logica base y utilidades para el PickAndPlaceWorker.
"""

import math
from PyQt6.QtCore import pyqtSignal, pyqtSlot, QTimer
from src.features.pick_and_place.pick_place_states import PickPlaceState


class BasePickPlaceLogic:
    """Mixin que proporciona el estado base y metodos comunes para la secuencia."""

    def _init_base_logic(self):
        self._selected_color = None
        self._sphere_poses = {}
        self._place_target_coords = None
        self._ik_target = None
        self._gripper_open = -112
        self._gripper_closed = 7
        self._GRIPPER_MAX_CLOSED = 21.0

        self._state_stall_timer = QTimer()
        self._state_stall_timer.setSingleShot(True)
        self._state_stall_timer.timeout.connect(self._on_state_timeout)

        self._last_positions = None
        self._current_feedback = None
        self._current_target = None
        self._STALL_TIMEOUT_MS = 1500
        self._MOVEMENT_TOLERANCE = 0.5
        self._SUCCESS_THRESHOLD = 2.0
        self._ERROR_THRESHOLD = 5.0

    def _start_stall_timer(self):
        """Inicia el timer de deteccion de estancamiento."""
        self._last_positions = None
        self._state_stall_timer.start(self._STALL_TIMEOUT_MS)

    def _on_state_timeout(self):
        """Callback del timer cuando el robot deja de moverse."""
        self._handle_movement_finished()

    def _fail(self, reason):
        """Termina la secuencia con error."""
        self._clear_state()
        self._sm.reset()
        self.sequence_failed.emit(reason)

    def _clear_state(self):
        """Limpia el estado interno sin alterar la maquina."""
        self._selected_color = None
        self._place_target_coords = None
        self._ik_target = None
        self._state_stall_timer.stop()
        self._last_gripper_pos = None

    @staticmethod
    def _relative_to_servo(positions):
        """Convierte angulos relativos a posiciones absolutas de servo."""
        return [float(value + 150.0) for value in positions]

    @staticmethod
    def _with_gripper(status, gripper_degrees):
        """Copia un objetivo y establece la pinza en grados relativos."""
        updated = list(status)
        updated[-1] = float(gripper_degrees + 150.0)
        return updated
