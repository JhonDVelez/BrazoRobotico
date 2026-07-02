"""
Paquete de la feature de configuración de color.

Proporciona la interfaz para calibrar los rangos HSV de los marcadores
de color utilizados en la detección de elipses y esferas del robot.
"""
from .color_window import ColorWindow
from .color_controller import ColorController

__all__ = [
    "ColorWindow",
    "ColorController"
]