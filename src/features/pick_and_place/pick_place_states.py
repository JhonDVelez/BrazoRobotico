"""
Modulo que define los estados de la maquina de estados para Pick and Place.

Cada estado representa una fase de la secuencia de pickup y colocacion
de esferas, coordinando movimientos del brazo robotico con la apertura
y cierre de la pinza.

States:
    IDLE: Estado inicial, esperando solicitud de pick.
    HOMING: Moviendo el brazo a posicion neutral before de iniciar.
    OPENING_GRIPPER: Abriendo la pinza en posicion neutral.
    COMPUTING_IK: Calculando cinematica inversa para la esfera objetivo.
    APPROACHING: Moviendo el brazo hacia la esfera detectada.
    GRASPING: Cerrando la pinza para sujetar la esfera.
    LIFTING: Regresando a posicion neutral con la esfera sujetada.
"""

from enum import Enum


class PickPlaceState(Enum):
    """Estados de la maquina de estados Pick and Place.

    Cada valor representa una fase identificable de la secuencia
    de pickup y colocacion. La maquina avanza secuencialmente
    desde IDLE hasta LIFTING, y regresa a IDLE al completar.
    """

    IDLE = "idle"
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
