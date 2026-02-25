""" En este modulo se definen los widgets y secciones de la interfaz principal, contenedores, 
    comportamiento de estos, tamaño y conexiones, asi como la inicializaron de algunas de estas
    como por ejemplo la inicializaron de la cámara
"""
import os
from PyQt6.QtWidgets import QVBoxLayout, QGridLayout, QSplitter, QGroupBox, QPushButton, QApplication
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QSizePolicy
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QSize, Qt
from data import Modes, Units, Domains
from data import DataFlow
from robot import RobotWorker
from ..camera_interface import CameraInterface
from ..sliders_interface import SlidersWidget
from ..simulation_interface import SimInterface
from ..graph_interface import GraphInterface


class MainInitMixin:
    """ Mixin donde se tienen las funciones de inicialización de las distintas partes de la 
        interfaz. Separa la lógica de construcción de la GUI de la lógica de eventos.
    """

    def setup_ui(self, main_widget):
        """
        Configura la jerarquía de widgets y layouts en el widget contenedor proporcionado.
        """
        self.main_widget = main_widget
        self.main_widget.setObjectName("MainWidget")
        self.main_widget.setMinimumSize(QSize(400, 400))
        self.main_widget.resize(QSize(1280, 720))

        # Configuración de política de tamaño
        sizePolicy = QSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Preferred
        )
        sizePolicy.setHorizontalStretch(3)
        sizePolicy.setVerticalStretch(3)
        self.main_widget.setSizePolicy(sizePolicy)

        # ========== LAYOUT PRINCIPAL (Rejilla) ==========
        self.gridLayout = QGridLayout(self.main_widget)
        self.gridLayout.setObjectName("gridLayout")
        self.gridLayout.setContentsMargins(5, 5, 5, 5)

        self.barContentLayout = QVBoxLayout()
        self.barContentLayout.setObjectName("barContentLayout")
        self.barContentLayout.setStretch(0, 16)

        # ========== SPLITTER PRINCIPAL (División Horizontal) ==========
        self.contentSplitter = QSplitter(parent=self.main_widget)
        self.contentSplitter.setOrientation(Qt.Orientation.Horizontal)
        self.contentSplitter.setObjectName("contentSplitter")
        self.contentSplitter.setHandleWidth(8)
        self.contentSplitter.setContentsMargins(0, 0, 0, 0)

        # ---- Visual Splitter (División Vertical Izquierda) ----
        self.visualSplitter = QSplitter(parent=self.contentSplitter)
        self.visualSplitter.setOrientation(Qt.Orientation.Vertical)
        self.visualSplitter.setObjectName("visualSplitter")
        self.visualSplitter.setHandleWidth(8)
        self.visualSplitter.setContentsMargins(0, 0, 0, 0)

        # Contenedores (GroupBoxes)
        self.modelBox = QGroupBox(parent=self.visualSplitter)
        self.modelBox.setTitle("")
        self.modelBox.setObjectName("modelBox")

        self.cameraBox = QGroupBox(parent=self.visualSplitter)
        self.cameraBox.setTitle("")
        self.cameraBox.setObjectName("cameraBox")

        # Contenedor de Telemetría (Gráficas)
        self.graphsBox = QGroupBox(parent=self.contentSplitter)
        self.graphsBox.setTitle("")
        self.graphsBox.setObjectName("graphsBox")
        self.graphsBox.setContentsMargins(0, 0, 0, 0)
        graphsBox_sizePolicy = QSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.graphsBox.setSizePolicy(graphsBox_sizePolicy)

        # Contenedor de Mandos
        self.controlsBox = QGroupBox(parent=self.contentSplitter)
        self.controlsBox.setTitle("")
        self.controlsBox.setObjectName("controlsBox")

        self.verticalLayout_2 = QVBoxLayout(self.controlsBox)
        self.verticalLayout_2.setSpacing(0)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        
        self.widget = QWidget(parent=self.controlsBox)
        self.widget.setObjectName("widget")

        self.horizontalLayout = QHBoxLayout(self.widget)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)

        # Botones de Control
        self.start_button = QPushButton(parent=self.widget)
        sizePolicy_fixed = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.start_button.setSizePolicy(sizePolicy_fixed)
        self.start_button.setMaximumSize(QSize(42, 42))
        self.start_button.setObjectName("start_button")
        self.horizontalLayout.addWidget(self.start_button)

        self.pause_button = QPushButton(parent=self.widget)
        self.pause_button.setMaximumSize(QSize(42, 42))
        self.pause_button.setObjectName("pause_button")
        self.horizontalLayout.addWidget(self.pause_button)

        self.stop_button = QPushButton(parent=self.widget)
        self.stop_button.setMaximumSize(QSize(42, 42))
        self.stop_button.setObjectName("stop_button")
        self.horizontalLayout.addWidget(self.stop_button)

        self.reset_button = QPushButton(parent=self.widget)
        self.reset_button.setMaximumSize(QSize(42, 42))
        self.reset_button.setObjectName("reset_button")
        self.horizontalLayout.addWidget(self.reset_button)

        self.verticalLayout_2.addWidget(self.widget)

        self.barContentLayout.addWidget(self.contentSplitter)
        self.gridLayout.addLayout(self.barContentLayout, 0, 0, 1, 1)

        self.contentSplitter.setSizes([500, 500, 200])
        self.visualSplitter.setSizes([100, 100])

    def init_camera(self):
        if not self.cameraBox.layout():
            layout = QVBoxLayout(self.cameraBox)
            layout.setContentsMargins(0, 0, 0, 0)
            self.cameraBox.setLayout(layout)

        self.camera_interface = CameraInterface(self)
        self.cameraBox.layout().addWidget(self.camera_interface)
        self.camera_interface.video_button.hide()

    def init_controls(self):
        self.slider_widget = SlidersWidget(self)
        self.controlsBox.layout().addWidget(self.slider_widget)

        self.control_app_widget = QWidget()
        if not self.control_app_widget.layout():
            layout = QHBoxLayout(self.control_app_widget)
            layout.setContentsMargins(0, 0, 0, 0)
            self.control_app_widget.setLayout(layout)

        # Iconos
        self.start_icon = QIcon(os.path.join(os.path.dirname(__file__), "..", "icons", "play.png"))
        self.pause_icon = QIcon(os.path.join(os.path.dirname(__file__), "..", "icons", "pause.png"))
        self.stop_icon = QIcon(os.path.join(os.path.dirname(__file__), "..", "icons", "stop.png"))
        self.reset_icon = QIcon(os.path.join(os.path.dirname(__file__), "..", "icons", "refresh.png"))

        self.start_button.setIcon(self.start_icon)
        self.start_button.setStyleSheet("background-color: #3B963F")
        self.reset_button.setIcon(self.reset_icon)
        self.stop_button.setIcon(self.stop_icon)
        self.stop_button.setStyleSheet("background-color: #F74220")
        self.pause_button.setIcon(self.pause_icon)

        self.control_app_widget.layout().addWidget(self.start_button)
        self.control_app_widget.layout().addWidget(self.pause_button)
        self.control_app_widget.layout().addWidget(self.stop_button)
        self.control_app_widget.layout().addWidget(self.reset_button)
        self.controlsBox.layout().addWidget(self.control_app_widget)

        self.pause_button.hide()
        self.stop_button.hide()

    def init_simulation(self):
        if not self.modelBox.layout():
            self.sim_layout = QVBoxLayout(self.modelBox)
            self.sim_layout.setContentsMargins(0, 0, 0, 0)
            self.modelBox.setLayout(self.sim_layout)

        self.simulation_interface = SimInterface(self, self.preloaded_data, self.robot_id)
        self.simulation_interface.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.sim_layout.addWidget(self.simulation_interface)

    def init_graphics(self):
        """ Configura el módulo de visualización de datos en tiempo real. """
        # CAMBIO: Definir self.graphLayout para que sea accesible desde app_interface.py
        if not self.graphsBox.layout():
            self.graphLayout = QVBoxLayout(self.graphsBox)
            self.graphLayout.setContentsMargins(0, 0, 0, 0)
            self.graphsBox.setLayout(self.graphLayout)

        self.graphsBox.setStyleSheet("""padding: 0px;""")

        # Instanciación del widget de gráficos original
        self.graph_interface = GraphInterface()
        
        # Lo añadimos al layout. Nota: app_interface.py añadirá el canvas aquí también.
        self.graphLayout.addWidget(self.graph_interface)

    def center_window(self):
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)