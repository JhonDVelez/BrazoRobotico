""" Paquete encargado de la gestión de la interfaz tanto la interfaz principal como los widget y
    el manejo que se le dan a estos.
"""

from src.main_window.app_window import MainWindow
from src.main_window import mixins

__all__ = [
    "MainWindow",
    "mixins"
]
