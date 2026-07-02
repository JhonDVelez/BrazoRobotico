"""
Paquete encargado de la ventana principal de la aplicación.

Proporciona la clase MainWindow (ventana principal frameless) y los mixins
necesarios para la gestión de menús, barra de título e inicialización de
los módulos funcionales.
"""

from src.main_window.app_window import MainWindow
from src.main_window import mixins

__all__ = [
    "MainWindow",
    "mixins"
]
