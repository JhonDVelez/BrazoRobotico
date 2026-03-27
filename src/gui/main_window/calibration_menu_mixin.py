""" En este modulo se define el menu que se integrara a la barra de titulo y como se comporta.
"""
import os
from PyQt6.QtGui import QAction, QKeySequence, QIcon, QPixmap, QActionGroup
from PyQt6.QtWidgets import QMenuBar, QSizePolicy, QLabel, QStatusBar
from PyQt6.QtCore import Qt
from serial.tools import list_ports
from robot.openbotv_worker import RobotWorker
from data import DataFlow


class CalibrationMenuMixin:
    """ Mixin encargado de definir el menu para la ventana de calibracion, 
        las acciones que hará y su comportamiento con estas
    """

    def create_calibration_actions(self):
        """ Define las acciones que tendrá el menu asi como sus atajos, texto de la barra de estado
            e iconos utilizados como botones para la ventana de calibración de la cámara.
        """
        self.open_action = QAction("Abrir Archivo...", self)
        self.open_action.setShortcut(QKeySequence("Ctrl+O"))
        self.open_action.setStatusTip(
            "Abrir archivo de configuración de la cámara")

        self.save_action = QAction("Guardar", self)
        self.save_action.setShortcut(QKeySequence("Ctrl+S"))
        self.save_action.setStatusTip(
            "Guardar configuraciones de la cámara")

        self.exit_action = QAction("Salir", self)
        self.exit_action.setStatusTip(
            "Salir de la ventana de calibración")

    def create_calibration_menu(self):
        """ Define la estructura del menu y submenus basado en las acciones definidas.
        """
        self.create_calibration_actions()
        self.menu_bar = QMenuBar()
        self.menu_bar.setFixedHeight(32)
        self.menu_bar.setContentsMargins(0, 0, 0, 0)
        self.menu_bar.adjustSize()

        self.vista_menu = self.menu_bar.addMenu("&Archivo")
        self.vista_menu.addAction(self.open_action)
        self.vista_menu.addAction(self.save_action)
        self.vista_menu.addSeparator()
        self.vista_menu.addAction(self.exit_action)

    def create_status_bar(self):
        """ Crea la barra de estado y conecta la visualization del estado de conexión del puerto 
            serial
        """
        status_bar = QStatusBar(self)
        self.setStatusBar(status_bar)
