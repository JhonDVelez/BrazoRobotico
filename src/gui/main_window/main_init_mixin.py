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
        interfaz
    """

    def setup_ui(self, main_widget):
        """
        Configura la UI en el widget proporcionado (ya no en MainWindow directamente)

        Args:
            main_widget: El widget donde se configurará la interfaz
        """
        self.main_widget = main_widget
        self.main_widget.setObjectName("MainWidget")
        self.main_widget.setMinimumSize(QSize(400, 400))
        self.main_widget.resize(QSize(1280, 720))

        sizePolicy = QSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Preferred
        )
        sizePolicy.setHorizontalStretch(3)
        sizePolicy.setVerticalStretch(3)
        self.main_widget.setSizePolicy(sizePolicy)

        # ========== LAYOUT PRINCIPAL ==========
        self.gridLayout = QGridLayout(self.main_widget)
        self.gridLayout.setObjectName("gridLayout")
        # Añadir margen superior para evitar superposición con title bar
        self.gridLayout.setContentsMargins(5, 5, 5, 5)

        self.barContentLayout = QVBoxLayout()
        self.barContentLayout.setObjectName("barContentLayout")
        self.barContentLayout.setStretch(0, 16)

        # ========== SPLITTER PRINCIPAL ==========
        self.contentSplitter = QSplitter(parent=self.main_widget)
        self.contentSplitter.setOrientation(Qt.Orientation.Horizontal)
        self.contentSplitter.setObjectName("contentSplitter")
        self.contentSplitter.setHandleWidth(8)
        self.contentSplitter.setContentsMargins(0, 0, 0, 0)

        # ---- Visual Splitter ----
        self.visualSplitter = QSplitter(parent=self.contentSplitter)
        self.visualSplitter.setOrientation(Qt.Orientation.Vertical)
        self.visualSplitter.setObjectName("visualSplitter")
        self.visualSplitter.setHandleWidth(8)
        self.visualSplitter.setContentsMargins(0, 0, 0, 0)

        # ---- Controls Splitter ----
        self.controlSplitter = QSplitter(parent=self.contentSplitter)
        self.controlSplitter.setOrientation(Qt.Orientation.Vertical)
        self.controlSplitter.setObjectName("ControlslSplitter")
        self.controlSplitter.setHandleWidth(8)
        self.controlSplitter.setContentsMargins(0, 0, 0, 0)

        self.modelBox = QGroupBox(parent=self.visualSplitter)
        self.modelBox.setTitle("")
        self.modelBox.setObjectName("modelBox")

        self.cameraBox = QGroupBox(parent=self.visualSplitter)
        self.cameraBox.setTitle("")
        self.cameraBox.setObjectName("cameraBox")

        self.graphsBox = QGroupBox(parent=self.controlSplitter)
        self.graphsBox.setTitle("")
        self.graphsBox.setObjectName("graphsBox")
        self.graphsBox.setContentsMargins(0, 0, 0, 0)
        graphsBox_sizePolicy = QSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        graphsBox_sizePolicy.setHorizontalStretch(0)
        graphsBox_sizePolicy.setVerticalStretch(0)
        self.graphsBox.setSizePolicy(graphsBox_sizePolicy)

        self.controlsBox = QGroupBox(parent=self.controlSplitter)
        self.controlsBox.setTitle("")
        self.controlsBox.setAlignment(
            Qt.AlignmentFlag.AlignBottom |
            Qt.AlignmentFlag.AlignLeading |
            Qt.AlignmentFlag.AlignLeft
        )
        self.controlsBox.setObjectName("controlsBox")

        self.verticalLayout_2 = QGridLayout(self.controlsBox)
        self.verticalLayout_2.setSpacing(0)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")

        self.actions_widget = QWidget(parent=self.controlsBox)
        self.actions_widget.setObjectName("widget")

        self.horizontalLayout = QHBoxLayout(self.actions_widget)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")

        # Botones de control
        self.start_button = QPushButton(parent=self.actions_widget)
        sizePolicy_fixed = QSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed
        )
        self.start_button.setSizePolicy(sizePolicy_fixed)
        self.start_button.setMaximumSize(QSize(42, 42))
        self.start_button.setObjectName("start_button")
        self.horizontalLayout.addWidget(self.start_button)

        self.pause_button = QPushButton(parent=self.actions_widget)
        self.pause_button.setSizePolicy(sizePolicy_fixed)
        self.pause_button.setMaximumSize(QSize(42, 42))
        self.pause_button.setText("")
        self.pause_button.setObjectName("pause_button")
        self.horizontalLayout.addWidget(self.pause_button)

        self.stop_button = QPushButton(parent=self.actions_widget)
        self.stop_button.setSizePolicy(sizePolicy_fixed)
        self.stop_button.setMaximumSize(QSize(42, 42))
        self.stop_button.setText("")
        self.stop_button.setObjectName("stop_button")
        self.horizontalLayout.addWidget(self.stop_button)

        self.reset_button = QPushButton(parent=self.actions_widget)
        self.reset_button.setSizePolicy(sizePolicy_fixed)
        self.reset_button.setMaximumSize(QSize(42, 42))
        self.reset_button.setObjectName("reset_button")
        self.horizontalLayout.addWidget(self.reset_button)

        self.verticalLayout_2.addWidget(self.actions_widget)

        # Añadir splitter principal al layout
        self.barContentLayout.addWidget(self.contentSplitter)
        self.gridLayout.addLayout(self.barContentLayout, 0, 0, 1, 1)

        self.contentSplitter.setSizes([400, 500])
        self.visualSplitter.setSizes([100, 100])
        self.controlSplitter.setSizes([300, 100])

    def init_camera(self):
        """ Inicializa la interfaz de la cámara y agrega el widget de video
        """
        # Limpiar cameraBox y agregar layout si no existe
        if not self.cameraBox.layout():
            layout = QVBoxLayout(self.cameraBox)
            layout.setContentsMargins(0, 0, 0, 0)
            self.cameraBox.setLayout(layout)

        self.camera_interface = CameraInterface(self)
        self.cameraBox.layout().addWidget(self.camera_interface)
        self.camera_interface.video_button.hide()

    def init_controls(self):
        """ Inicializa la interfaz de controladores con sliders que indica el
           angulo objetivo de cada motor del robot
        """
        self.slider_widget = SlidersWidget(self)
        self.controlsBox.layout().addWidget(self.slider_widget, 0, 0)

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

        self.controlsBox.layout().addWidget(self.control_app_widget, 1, 0)

        self.pause_button.hide()
        self.stop_button.hide()

        # Kinematics widget moved inside SlidersWidget; no longer added here

    def init_simulation(self):
        """ Inicializa la interfaz de la simulación creando el layout y realizando ajustes para una
            correcta adición a esta.
        """
        if not self.modelBox.layout():
            self.sim_layout = QVBoxLayout(self.modelBox)
            self.sim_layout.setContentsMargins(0, 0, 0, 0)
            self.modelBox.setLayout(self.sim_layout)

        self.simulation_interface = SimInterface(
            self, self.preloaded_data, self.robot_id)
        self.simulation_interface.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.simulation_interface.setMinimumSize(QSize(0, 0))
        self.sim_layout.addWidget(self.simulation_interface)

    def init_openbotv(self, com: str):
        """ Inicializa la conexión con el microcontrolador asi como la inicialización del 
        controlador

        Args:
            com (str): Puerto de comunicación serial seleccionado
        """
        self.robot_controller = DataFlow(
            Modes.SLIDERS, Units.DEG, Domains.PHYSICAL
        )

        self.openbotv = RobotWorker(com)
        self.openbotv.start()

        self.connect_action.setEnabled(False)

    def init_graphics(self):
        """ Inicialización del contenedor para los gráficos tipo osciloscopio
        """
        if not self.graphsBox.layout():
            graph_layout = QVBoxLayout(self.graphsBox)
            graph_layout.setContentsMargins(0, 0, 0, 0)
            self.graphsBox.setLayout(graph_layout)

        self.graphsBox.setStyleSheet("""padding: 0px;""")

        self.graph_interface = GraphInterface()
        self.graphsBox.layout().addWidget(self.graph_interface)

    def center_window(self):
        """ Centra la interfaz en pantalla cuando esta se inicia en modo ventana
        """
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)
