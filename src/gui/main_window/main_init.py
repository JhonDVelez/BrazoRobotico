import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QSizePolicy
from PyQt6.QtGui import QScreen, QIcon
from PyQt6.QtCore import QSize
from PyQt6 import uic
from data.control_utils import modes, units, domains
from data.controller import dataFlow
from gui.camera_interface import VideoOverlayWidget
from gui.sliders_interface import SlidersWidget
from gui.simulation_interface import SimInterface
from robot.openbotv_worker import robotWorker


class MainInit:
    def init_main_window(self):
        """ Inicializa la ventana principal de la aplicación y configura su diseño
        """
        self.ui = uic.loadUi(os.path.join(
            os.path.dirname(__file__), "..", "app_interface.ui"), self)

        # Centra la ventana en la pantalla
        window = QMainWindow()
        screen_center = QScreen.availableGeometry(
            QApplication.primaryScreen()).center()
        window_geometry = window.frameGeometry()
        window_geometry.moveCenter(screen_center)
        window.move(window_geometry.topLeft())

        # Configura el tamaño por defecto de las ventanas
        self.contentSplitter.setSizes([500, 500, 300])
        self.visualSplitter.setSizes([100, 100])

    def init_camera(self):
        """ Inicializa la interfaz de la cámara y agrega el widget de video
        """
        # Limpiar cameraBox y agregar layout si no existe
        if not self.cameraBox.layout():
            layout = QVBoxLayout(self.cameraBox)
            layout.setContentsMargins(0, 0, 0, 0)
            self.cameraBox.setLayout(layout)

        self.camera_interface = VideoOverlayWidget(self.ui)
        self.cameraBox.layout().addWidget(self.camera_interface)
        self.camera_interface.videoButton.hide()

    def init_controls(self):
        """ Inicializa la interfaz de controladores con sliders que indica el
           angulo objetivo de cada motor del robot
        """
        self.slider_widget = SlidersWidget(self.ui)
        self.controlsBox.layout().addWidget(self.slider_widget)

        self.control_app_widget = QWidget()
        if not self.control_app_widget.layout():
            layout = QHBoxLayout(self.control_app_widget)
            layout.setContentsMargins(0, 0, 0, 0)
            self.control_app_widget.setLayout(layout)

        self.start_icon = QIcon(os.path.join(os.path.dirname(__file__),
                                             "..", "icons", "play.png"))
        self.pause_icon = QIcon(os.path.join(os.path.dirname(__file__),
                                             "..", "icons", "pause.png"))
        self.stop_icon = QIcon(os.path.join(os.path.dirname(__file__),
                                            "..", "icons", "stop.png"))
        self.reset_icon = QIcon(os.path.join(os.path.dirname(__file__),
                                             "..", "icons", "refresh.png"))

        self.start_button.setIcon(self.start_icon)
        self.start_button.setStyleSheet(
            "background-color: #3B963F")  # Boton color verde

        self.reset_button.setIcon(self.reset_icon)
        self.reset_button.setStyleSheet(
            "background-color: #777777")  # Boton color gris

        self.stop_button.setIcon(self.stop_icon)
        self.stop_button.setStyleSheet(
            "background-color: #F74220")  # Boton color rojo

        self.pause_button.setIcon(self.pause_icon)
        self.pause_button.setStyleSheet(
            "background-color: #777777")  # Boton color gris

        self.control_app_widget.layout().addWidget(self.start_button)
        self.control_app_widget.layout().addWidget(self.pause_button)
        self.control_app_widget.layout().addWidget(self.stop_button)
        self.control_app_widget.layout().addWidget(self.reset_button)

        self.controlsBox.layout().addWidget(self.control_app_widget)

        self.pause_button.hide()
        self.stop_button.hide()

    def init_simulation(self):
        """ Inicializa la interfaz de la simulacion creando el layout y realizando ajustes para una
            correcta adicion a esta.
        """
        if not self.modelBox.layout():
            self.sim_layout = QVBoxLayout(self.modelBox)
            self.sim_layout.setContentsMargins(0, 0, 0, 0)
            self.modelBox.setLayout(self.sim_layout)

        self.simulation_interface = SimInterface(self.ui)
        self.simulation_interface.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.simulation_interface.setMinimumSize(QSize(0, 0))
        self.sim_layout.addWidget(self.simulation_interface)

    def init_openbotv(self):
        self.robot_controller = dataFlow(
            modes.SLIDERS, units.DEG, domains.PHYSICAL)
        self.robot_controller.start()

        self.openbotv = robotWorker()
        self.openbotv.start()
