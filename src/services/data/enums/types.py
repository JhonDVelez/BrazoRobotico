"""
Módulo que define los tipos enumerados fundamentales del sistema.

Este módulo contiene las definiciones de modos de operación, unidades
de medida y dominios de ejecución utilizados para parametrizar el flujo
de datos y la lógica de control.
"""

from enum import Enum


class Modes(Enum):
    """
    Define el origen de los datos de control en la interfaz.

    Attributes:
        SLIDERS: Control manual motor a motor.
        KINEMATIC: Control cartesiano mediante cinemática inversa.
    """
    SLIDERS = 1
    KINEMATIC = 2
    PICK_PLACE = 3


class Units(Enum):
    """
    Define las unidades de medida para las articulaciones.

    Attributes:
        DEG: Grados sexagesimales (usado principalmente en UI y hardware).
        RAD: Radianes (usado principalmente en cálculos y PyBullet).
    """
    DEG = 1
    RAD = 2


class Domains(Enum):
    """
    Identifica el entorno de ejecución activo para el controlador.

    Attributes:
        SIMULATION: Los comandos se dirigen al motor de física PyBullet.
        PHYSICAL: Los comandos se dirigen al hardware real vía serial.
    """
    SIMULATION = 1
    PHYSICAL = 2


class NotificationType(Enum):
    """
    Define cómo se presenta una notificación al usuario.

    Attributes:
        TOAST_INFO: Toast transitorio con estilo informativo.
        TOAST_SUCCESS: Toast transitorio con estilo de éxito.
        TOAST_WARNING: Toast transitorio con estilo de advertencia.
        TOAST_ERROR: Toast transitorio con estilo de error.
        DIALOG_INFO: Diálogo modal con icono de información.
        DIALOG_WARNING: Diálogo modal con icono de advertencia.
        DIALOG_ERROR: Diálogo modal con icono de error crítico.
        DIALOG_QUESTION: Diálogo modal con icono de pregunta y botones Sí/No.
    """
    TOAST_INFO = 1
    TOAST_SUCCESS = 2
    TOAST_WARNING = 3
    TOAST_ERROR = 4
    DIALOG_INFO = 5
    DIALOG_WARNING = 6
    DIALOG_ERROR = 7
    DIALOG_QUESTION = 8
