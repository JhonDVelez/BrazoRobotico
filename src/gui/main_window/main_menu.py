import os
from PyQt6.QtGui import QAction, QKeySequence, QIcon, QPixmap
from PyQt6.QtWidgets import QMenuBar, QSizePolicy, QLabel, QStatusBar
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
        self.simulation_action.setShortcut(QKeySequence("Ctrl+y"))
        self.simulation_action.setStatusTip("Activar/Desactivar simulación")

        self.sun_icon = QIcon(os.path.join(
            os.path.dirname(__file__), "..", "icons", "sun.png"))
        self.moon_icon = QIcon(os.path.join(
            os.path.dirname(__file__), "..", "icons", "moon.png"))

        self.theme_action = QAction(
            self.sun_icon, "Cambiar tema", self)
        self.theme_action.setShortcut(QKeySequence("Ctrl+l"))
        self.theme_action.setStatusTip("Cambiar tema")

    def create_menu(self):
        self.create_actions()
        self.menu_bar = QMenuBar()
        self.menu_bar.setFixedHeight(32)
        self.menu_bar.setContentsMargins(0, 0, 0, 0)
        self.menu_bar.adjustSize()

        self.logo_label = QLabel()
        self.laser_w = QPixmap(os.path.join(
            os.path.dirname(__file__), "..", "img", "laser_w.png")).scaledToHeight(20, Qt.TransformationMode.SmoothTransformation)
        self.laser_b = QPixmap(os.path.join(
            os.path.dirname(__file__), "..", "img", "laser_b.png")).scaledToHeight(20, Qt.TransformationMode.SmoothTransformation)
        self.logo_label.setPixmap(self.laser_w)
        self.logo_label.setContentsMargins(8, 0, 5, 0)

        self.menu_bar.setCornerWidget(self.logo_label, Qt.Corner.TopLeftCorner)

        # Menús normales
        self.vista_menu = self.menu_bar.addMenu("&Vista")
        self.vista_menu.addAction(self.camera_action)
        self.vista_menu.addAction(self.model_action)

        self.mode_menu = self.menu_bar.addMenu("&Modo")
        self.mode_menu.addAction(self.sliders_action)

        self.simulation_menu = self.menu_bar.addMenu("&Simulación")
        self.simulation_menu.addAction(self.simulation_action)

        self.menu_bar.setSizePolicy(
            QSizePolicy(QSizePolicy.Policy.Preferred,
                        QSizePolicy.Policy.Preferred)
        )

    def create_status_bar(self):
        statusBar = QStatusBar(self)
        # statusBar.addWidget(QLabel('row 1'))
        # statusBar.addWidget(QLabel('column 1'))
        self.setStatusBar(statusBar)
