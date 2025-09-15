import os
from PyQt6.QtGui import QAction, QKeySequence, QIcon
from PyQt6.QtWidgets import QToolButton, QMenuBar, QSizePolicy
from PyQt6.QtCore import Qt


class MainMenu:

    def create_actions(self):
        self.camera_action = QAction("Ocultar Cámara", self)
        self.camera_action.setShortcut(QKeySequence("Ctrl+j"))
        self.camera_action.setStatusTip("Mostrar/Ocultar la cámara")

        self.model_action = QAction("Ocultar Modelo 3D", self)
        self.model_action.setShortcut(QKeySequence("Ctrl+k"))
        self.model_action.setStatusTip("Mostrar/Ocultar el modelo 3D")

        self.sliders_action = QAction("Sliders", self)
        self.sliders_action.setShortcut(QKeySequence("Ctrl+t"))
        self.sliders_action.setStatusTip("Modo de control con sliders")

        self.simulation_action = QAction("Desactivar simulación", self)
        self.simulation_action.setShortcut(QKeySequence("Ctrl+u"))
        self.simulation_action.setStatusTip("Activar/Desactivar simulación")

    def create_menu(self):
        self.create_actions()
        self.menubar = QMenuBar()
        self.vista_menu = self.menubar.addMenu("&Vista")
        self.vista_menu.addAction(self.camera_action)
        self.vista_menu.addAction(self.model_action)

        self.mode_menu = self.menubar.addMenu("&Modo")
        self.mode_menu.addAction(self.sliders_action)

        self.simulation_menu = self.menubar.addMenu("&Simulación")
        self.simulation_menu.addAction(self.simulation_action)

        self.theme_menu = QToolButton(self)
        self.sun_icon = QIcon(os.path.join(
            os.path.dirname(__file__), "..", "icons", "sun.png"))
        self.moon_icon = QIcon(os.path.join(
            os.path.dirname(__file__), "..", "icons", "moon.png"))
        self.theme_menu.setIcon(self.sun_icon)
        self.menubar.setCornerWidget(self.theme_menu)
        self.menubar.setSizePolicy(QSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred))
