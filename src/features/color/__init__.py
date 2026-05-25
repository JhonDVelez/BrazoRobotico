"""
Paquete de la feature de configuracion de color.

Proporciona la interfaz para calibrar los rangos HSV de los marcadores
de color utilizados en la deteccion de elipses y esferas del robot.
"""
from .color_window import ColorWindow
from .color_controller import ColorController

__all__ = [
    "ColorWindow",
    "ColorController"
]