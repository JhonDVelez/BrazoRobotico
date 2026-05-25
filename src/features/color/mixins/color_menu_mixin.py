"""
Modulo que define los componentes de menu y barra de estado para el modulo de color.

Este modulo contiene el ColorMenuMixin, el cual extiende las capacidades
de la ventana de color permitiendo la creacion de una barra de menus y
una barra de estado personalizada.
"""

import os
from PyQt6.QtGui import QAction, QKeySequence, QIcon
from PyQt6.QtWidgets import QMenuBar, QStatusBar
from src.main_window.mixins.main_menu_mixin import MainMenuMixin


class ColorMenuMixin(MainMenuMixin):
    """
    Mixin encargado de definir el menu para la ventana de calibracion de color.

    Proporciona metodos para configurar la barra de menus, las acciones
    (como el cambio de tema) y la barra de estado de la ventana.
    """

    def __init__(self):
        """
        Inicializa el mixin de menu de color.
        """
        super().__init__()

    def create_calibration_menu(self):
        """
        Define la estructura de la barra de menus y sus acciones asociadas.

        Crea acciones para el control del tema visual y configura atajos de teclado.
        """
        self.menu_bar = QMenuBar()
        self.menu_bar.setFixedHeight(32)
        self.menu_bar.setContentsMargins(0, 0, 0, 0)
        self.menu_bar.adjustSize()

        self.sun_icon = QIcon(os.path.join("icons:sun.png"))
        self.moon_icon = QIcon(os.path.join("icons:moon.png"))

        self.theme_action = QAction("", self)
        self.theme_action.setShortcut(QKeySequence("Ctrl+t"))
        self.theme_action.setStatusTip("Cambiar tema")

    def create_status_bar(self):
        """
        Crea e integra una barra de estado en la ventana.
        """
        status_bar = QStatusBar(self)
        self.setStatusBar(status_bar)
