""" Paquete encargado de la calibración de colores HSV.
    Permite ajustar los rangos de color para la detección de objetos.
"""

from .color_window import ColorWindow
from .color_controller import ColorController

__all__ = [
    "ColorWindow",
    "ColorController"
]
