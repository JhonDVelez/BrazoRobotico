"""
Módulo que define la máquina de estados para la secuencia Pick and Place.
"""

from statemachine import StateMachine, State
from src.features.pick_and_place.pick_place_states import PickPlaceState

class PickPlaceStateMachine(StateMachine):
    """
    Máquina de estados interna para la secuencia Pick and Place.
    """

    idle = State(PickPlaceState.IDLE.value, initial=True)
    home1_move = State(PickPlaceState.HOME1_MOVE.value)
    home1_validate = State(PickPlaceState.HOME1_VALIDATE.value)
    waiting_for_input = State(PickPlaceState.WAITING_FOR_INPUT.value)
    home2_move = State(PickPlaceState.HOME2_MOVE.value)
    home2_validate = State(PickPlaceState.HOME2_VALIDATE.value)
    pid_home = State(PickPlaceState.PID_HOME.value)
    pick_approach = State(PickPlaceState.PICK_APPROACH.value)
    pick_down = State(PickPlaceState.PICK_DOWN.value)
    pick_grasp = State(PickPlaceState.PICK_GRASP.value)
    retract_to_pid_home = State(PickPlaceState.RETRACT_TO_PID_HOME.value)
    place_approach = State(PickPlaceState.PLACE_APPROACH.value)
    place_down = State(PickPlaceState.PLACE_DOWN.value)
    place_release = State(PickPlaceState.PLACE_RELEASE.value)
    retract_to_place_above = State(PickPlaceState.RETRACT_TO_PLACE_ABOVE.value)
    retract_from_place = State(PickPlaceState.RETRACT_FROM_PLACE.value)
    final_seq_home = State(PickPlaceState.FINAL_SEQ_HOME.value)
    final_seq_home2 = State(PickPlaceState.FINAL_SEQ_HOME2.value)
    final_seq_home1 = State(PickPlaceState.FINAL_SEQ_HOME1.value)

    start_op = idle.to(home1_move)
    home1_done = home1_move.to(home1_validate)
    home1_validated = home1_validate.to(waiting_for_input)
    
    # After input (pick/place)
    ready_to_home2 = waiting_for_input.to(home2_move)
    home2_done = home2_move.to(home2_validate)
    home2_validated = home2_validate.to(pid_home)
    
    pid_home_done = pid_home.to(pick_approach)
    pick_approach_done = pick_approach.to(pick_down)
    pick_down_done = pick_down.to(pick_grasp)
    pick_grasp_done = pick_grasp.to(retract_to_pid_home)
    
    retract_done = retract_to_pid_home.to(place_approach)
    place_approach_done = place_approach.to(place_down)
    place_down_done = place_down.to(place_release)
    place_release_done = place_release.to(retract_to_place_above)
    
    retract_from_place_done = retract_to_place_above.to(retract_from_place)
    retract_from_place_to_pid = retract_from_place.to(final_seq_home)
    
    final_home_done = final_seq_home.to(final_seq_home2)
    final_home2_done = final_seq_home2.to(final_seq_home1)
    final_home1_done = final_seq_home1.to(waiting_for_input)

    reset = (
        home1_move.to(idle)
        | home1_validate.to(idle)
        | waiting_for_input.to(idle)
        | home2_move.to(idle)
        | home2_validate.to(idle)
        | pid_home.to(idle)
        | pick_approach.to(idle)
        | pick_down.to(idle)
        | pick_grasp.to(idle)
        | retract_to_pid_home.to(idle)
        | place_approach.to(idle)
        | place_down.to(idle)
        | place_release.to(idle)
        | retract_to_place_above.to(idle)
        | retract_from_place.to(idle)
        | final_seq_home.to(idle)
        | final_seq_home2.to(idle)
        | final_seq_home1.to(idle)
    )

    def __init__(self, on_state_change=None):
        super().__init__()
        self._on_state_change = on_state_change

    def _notify(self, state):
        if self._on_state_change:
            self._on_state_change(state.value)

    def on_enter_home1_move(self): self._notify(PickPlaceState.HOME1_MOVE)
    def on_enter_home1_validate(self): self._notify(PickPlaceState.HOME1_VALIDATE)
    def on_enter_waiting_for_input(self): self._notify(PickPlaceState.WAITING_FOR_INPUT)
    def on_enter_home2_move(self): self._notify(PickPlaceState.HOME2_MOVE)
    def on_enter_home2_validate(self): self._notify(PickPlaceState.HOME2_VALIDATE)
    def on_enter_pid_home(self): self._notify(PickPlaceState.PID_HOME)
    def on_enter_pick_approach(self): self._notify(PickPlaceState.PICK_APPROACH)
    def on_enter_pick_down(self): self._notify(PickPlaceState.PICK_DOWN)
    def on_enter_pick_grasp(self): self._notify(PickPlaceState.PICK_GRASP)
    def on_enter_retract_to_pid_home(self): self._notify(PickPlaceState.RETRACT_TO_PID_HOME)
    def on_enter_place_approach(self): self._notify(PickPlaceState.PLACE_APPROACH)
    def on_enter_place_down(self): self._notify(PickPlaceState.PLACE_DOWN)
    def on_enter_place_release(self): self._notify(PickPlaceState.PLACE_RELEASE)
    def on_enter_retract_to_place_above(self): self._notify(PickPlaceState.RETRACT_TO_PLACE_ABOVE)
    def on_enter_retract_from_place(self): self._notify(PickPlaceState.RETRACT_FROM_PLACE)
    def on_enter_final_seq_home(self): self._notify(PickPlaceState.FINAL_SEQ_HOME)
    def on_enter_final_seq_home2(self): self._notify(PickPlaceState.FINAL_SEQ_HOME2)
    def on_enter_final_seq_home1(self): self._notify(PickPlaceState.FINAL_SEQ_HOME1)
