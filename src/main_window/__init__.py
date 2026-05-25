"""
Paquete encargado de la ventana principal de la aplicacion.

Proporciona la clase MainWindow (ventana principal frameless) y los mixins
necesarios para la gestion de menus, barra de titulo e inicializacion de
los modulos funcionales.
"""

from src.main_window.app_window import MainWindow
from src.main_window import mixins

__all__ = [
    "MainWindow",
    "mixins"
]
