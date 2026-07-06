"""
Módulo que define la máquina de estados para la secuencia Pick and Place.
"""

from statemachine import StateMachine, State
from src.features.pick_and_place.pick_place_states import PickPlaceState

class PickPlaceStateMachine(StateMachine):
    """    Máquina de estados interna para la secuencia Pick and Place.

    Gestiona las transiciones entre fases de la secuencia. Cada estado
    tiene un callback ``on_enter_*`` que notifica al worker para emitir
    la accion correspondiente.
    """

    idle = State(PickPlaceState.IDLE.value, initial=True)
    homing = State(PickPlaceState.HOMING.value)
    computing_ik_above = State(PickPlaceState.COMPUTING_IK_ABOVE.value)
    approaching_above = State(PickPlaceState.APPROACHING_ABOVE.value)
    opening_gripper = State(PickPlaceState.OPENING_GRIPPER.value)
    computing_ik = State(PickPlaceState.COMPUTING_IK.value)
    approaching = State(PickPlaceState.APPROACHING.value)
    grasping = State(PickPlaceState.GRASPING.value)
    lifting = State(PickPlaceState.LIFTING.value)
    computing_ik_place_above = State(PickPlaceState.COMPUTING_IK_PLACE_ABOVE.value)
    approaching_place_above = State(PickPlaceState.APPROACHING_PLACE_ABOVE.value)
    computing_ik_place = State(PickPlaceState.COMPUTING_IK_PLACE.value)
    approaching_place = State(PickPlaceState.APPROACHING_PLACE.value)
    releasing = State(PickPlaceState.RELEASING.value)
    returning_home = State(PickPlaceState.RETURNING_HOME.value)

    # Transiciones normales de la secuencia
    start_pick = idle.to(homing)
    homing_done = homing.to(computing_ik_above)
    ik_computed_above = computing_ik_above.to(approaching_above)
    above_reached = approaching_above.to(opening_gripper)
    gripper_opened = opening_gripper.to(computing_ik)
    ik_computed = computing_ik.to(approaching)
    close_gripper = approaching.to(grasping)
    grasp_done = grasping.to(lifting)
    lift_complete = lifting.to(idle)

    # Transiciones para la secuencia de colocación (Place)
    start_place = idle.to(computing_ik_place_above)
    ik_computed_place_above = computing_ik_place_above.to(approaching_place_above)
    above_place_reached = approaching_place_above.to(computing_ik_place)
    ik_computed_place = computing_ik_place.to(approaching_place)
    place_reached = approaching_place.to(releasing)
    gripper_released = releasing.to(returning_home)
    home_reached = returning_home.to(idle)

    # Transición de reset/cancelación desde cualquier estado no-idle
    reset = (
        homing.to(idle)
        | computing_ik_above.to(idle)
        | approaching_above.to(idle)
        | opening_gripper.to(idle)
        | computing_ik.to(idle)
        | approaching.to(idle)
        | grasping.to(idle)
        | lifting.to(idle)
        | computing_ik_place_above.to(idle)
        | approaching_place_above.to(idle)
        | computing_ik_place.to(idle)
        | approaching_place.to(idle)
        | releasing.to(idle)
        | returning_home.to(idle)
    )

    def __init__(self, on_state_change=None):
        super().__init__()
        self._on_state_change = on_state_change

    def _notify(self, state):
        if self._on_state_change:
            self._on_state_change(state.value)

    def on_enter_homing(self): self._notify(PickPlaceState.HOMING)
    def on_enter_computing_ik_above(self): self._notify(PickPlaceState.COMPUTING_IK_ABOVE)
    def on_enter_approaching_above(self): self._notify(PickPlaceState.APPROACHING_ABOVE)
    def on_enter_opening_gripper(self): self._notify(PickPlaceState.OPENING_GRIPPER)
    def on_enter_computing_ik(self): self._notify(PickPlaceState.COMPUTING_IK)
    def on_enter_approaching(self): self._notify(PickPlaceState.APPROACHING)
    def on_enter_grasping(self): self._notify(PickPlaceState.GRASPING)
    def on_enter_lifting(self): self._notify(PickPlaceState.LIFTING)
    def on_enter_computing_ik_place_above(self): self._notify(PickPlaceState.COMPUTING_IK_PLACE_ABOVE)
    def on_enter_approaching_place_above(self): self._notify(PickPlaceState.APPROACHING_PLACE_ABOVE)
    def on_enter_computing_ik_place(self): self._notify(PickPlaceState.COMPUTING_IK_PLACE)
    def on_enter_approaching_place(self): self._notify(PickPlaceState.APPROACHING_PLACE)
    def on_enter_releasing(self): self._notify(PickPlaceState.RELEASING)
    def on_enter_returning_home(self): self._notify(PickPlaceState.RETURNING_HOME)
