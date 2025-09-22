import os
from PyQt6.QtGui import QAction, QKeySequence, QIcon, QPixmap, QActionGroup
from PyQt6.QtWidgets import QMenuBar, QSizePolicy, QLabel, QStatusBar
from PyQt6.QtCore import Qt
from serial.tools import list_ports


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

        self.connect_action = QAction("Conectar", self)
        self.connect_action.setEnabled(False)

        # self.com_select_action = QAction()

    def create_menu(self):
        self.create_actions()
        self.menu_bar = QMenuBar()
        self.menu_bar.setFixedHeight(32)
        self.menu_bar.setContentsMargins(0, 0, 0, 0)
        self.menu_bar.adjustSize()

        # Logo en la equina izquierda
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

        self.robot_menu = self.menu_bar.addMenu("&Robot")
        self.com_submenu = self.robot_menu.addMenu("&Puerto")
        self.com_group = QActionGroup(self)
        self.com_group.setExclusive(True)
        self.get_com_ports()
        self.robot_menu.addAction(self.connect_action)

        self.menu_bar.setSizePolicy(
            QSizePolicy(QSizePolicy.Policy.Preferred,
                        QSizePolicy.Policy.Preferred)
        )

    def get_com_ports(self):
        available_ports = list_ports.comports()

        # 1. limpiar menú y grupo
        self.com_submenu.clear()
        for action in list(self.com_group.actions()):
            self.com_group.removeAction(action)

        if available_ports:
            for port in available_ports:
                # Acción con descripción
                com_action = self.com_submenu.addAction(port.description)
                com_action.setCheckable(True)
                com_action.setData(port.device)
                com_action.setStatusTip(f"Conectar al puerto {port.device}")

                # Añadir la acción al grupo
                self.com_group.addAction(com_action)
                self.com_submenu.setEnabled(True)

                # Conectar
                com_action.triggered.connect(self.com_checkable_change)
        else:
            self.connect_action.setEnabled(False)
            self.com = None
            self.com_submenu.setEnabled(False)
            self.com_connected_label.setText("No conectado")

    def com_checkable_change(self, checked):
        action = self.sender()
        if action and checked:  # Solo cuando queda seleccionado
            self.com = action.data()
            self.com_connected_label.setText(self.com)
            self.connect_action.setEnabled(True)

    def create_status_bar(self):
        statusBar = QStatusBar(self)
        self.com_connected_label = QLabel('No conectado')
        statusBar.addPermanentWidget(self.com_connected_label)
        self.setStatusBar(statusBar)
