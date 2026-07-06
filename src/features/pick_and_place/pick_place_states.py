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
