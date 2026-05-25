"""
Modulo que define los tipos enumerados fundamentales del sistema.

Este modulo contiene las definiciones de modos de operacion, unidades
de medida y dominios de ejecucion utilizados para parametrizar el flujo
de datos y la logica de control.
"""

from enum import Enum


class Modes(Enum):
    """
    Define el origen de los datos de control en la interfaz.

    Attributes:
        SLIDERS: Control manual motor a motor.
        KINEMATIC: Control cartesiano mediante cinematica inversa.
    """
    SLIDERS = 1
    KINEMATIC = 2


class Units(Enum):
    """
    Define las unidades de medida para las articulaciones.

    Attributes:
        DEG: Grados sexagesimales (usado principalmente en UI y hardware).
        RAD: Radianes (usado principalmente en calculos y PyBullet).
    """
    DEG = 1
    RAD = 2


class Domains(Enum):
    """
    Identifica el entorno de ejecucion activo para el controlador.

    Attributes:
        SIMULATION: Los comandos se dirigen al motor de fisica PyBullet.
        PHYSICAL: Los comandos se dirigen al hardware real via serial.
    """
    SIMULATION = 1
    PHYSICAL = 2
