"""
Módulo que define los estados de la máquina de estados para Pick and Place.

Cada estado representa una fase de la secuencia de pickup y colocación
de esferas, coordinando movimientos del brazo robótico con la apertura
y cierre de la pinza.

States:
    IDLE: Estado inicial, esperando solicitud de pick.
    HOMING: Moviendo el brazo a posición neutral antes de iniciar.
    OPENING_GRIPPER: Abriendo la pinza en posición neutral.
    COMPUTING_IK: Calculando cinemática inversa para la esfera objetivo.
    APPROACHING: Moviendo el brazo hacia la esfera detectada.
    GRASPING: Cerrando la pinza para sujetar la esfera.
    LIFTING: Regresando a posición neutral con la esfera sujetada.
"""

from enum import Enum


class PickPlaceState(Enum):
    """Estados de la máquina de estados Pick and Place.

    Cada valor representa una fase identificable de la secuencia
    de pickup y colocación. La máquina avanza secuencialmente
    desde IDLE hasta LIFTING, y regresa a IDLE al completar.
    """

    IDLE = "idle"
    HOME1_MOVE = "home1_move"
    HOME1_VALIDATE = "home1_validate"
    WAITING_FOR_INPUT = "waiting_for_input"
    HOME2_MOVE = "home2_move"
    HOME2_VALIDATE = "home2_validate"
    PID_HOME = "pid_home"
    PICK_APPROACH = "pick_approach"
    PICK_DOWN = "pick_down"
    PICK_GRASP = "pick_grasp"
    RETRACT_TO_PID_HOME = "retract_to_pid_home"
    PLACE_APPROACH = "place_approach"
    PLACE_DOWN = "place_down"
    PLACE_RELEASE = "place_release"
    RETRACT_TO_PLACE_ABOVE = "retract_to_place_above"
    RETRACT_FROM_PLACE = "retract_from_place"
    FINAL_SEQ_HOME = "final_seq_home"
    FINAL_SEQ_HOME2 = "final_seq_home2"
    FINAL_SEQ_HOME1 = "final_seq_home1"
    
    # Keeping old states for compatibility if needed, but the new sequence is mostly different
    # If the user wants to completely replace it, I will, but let's keep it safe.
    HOMING = "homing"
    OPENING_GRIPPER = "opening_gripper"
    COMPUTING_IK = "computing_ik"
    COMPUTING_IK_ABOVE = "computing_ik_above"
    APPROACHING_ABOVE = "approaching_above"
    APPROACHING = "approaching"
    GRASPING = "grasping"
    LIFTING = "lifting"
    COMPUTING_IK_PLACE = "computing_ik_place"
    COMPUTING_IK_PLACE_ABOVE = "computing_ik_place_above"
    APPROACHING_PLACE_ABOVE = "approaching_place_above"
    APPROACHING_PLACE = "approaching_place"
    RELEASING = "releasing"
    RETURNING_HOME = "returning_home"
