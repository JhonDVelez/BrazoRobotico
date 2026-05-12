""" En este modulo se define el menu que se integrara a la barra de titulo y como se comporta.
"""
import os
from PyQt6.QtGui import QAction, QKeySequence, QIcon
from PyQt6.QtWidgets import QMenuBar, QStatusBar
from src.main_window.mixins.main_menu_mixin import MainMenuMixin


class CalibrationMenuMixin(MainMenuMixin):
    """ Mixin encargado de definir el menu para la ventana de calibración, 
        las acciones que hará y su comportamiento con estas
    """

    def __init__(self):
        super().__init__()

    def create_calibration_menu(self):
        """ Define la estructura del menu y submenus basado en las acciones definidas.
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
        """ Crea la barra de estado y conecta la visualization del estado de conexión del puerto 
            serial
        """
        status_bar = QStatusBar(self)
        self.setStatusBar(status_bar)
