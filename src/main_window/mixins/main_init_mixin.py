"""
Modulo que define la estructura e inicializacion de la interfaz principal.

Contiene el mixin MainInitMixin, responsable de crear los contenedores
graficos (splitters, group boxes), inicializar los controladores de
camara, simulacion, graficos y controles, y configurar la toolbar
con las acciones de flujo de trabajo.
"""

import os
from PyQt6.QtWidgets import QVBoxLayout, QGridLayout, QSplitter, QGroupBox, QApplication
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QSizePolicy, QToolBar
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QSize, Qt
from src.services.data.enums import Modes, Units, Domains
from src.services.data import DataController
from src.services.data.signals import ConfigSignalManager
from src.services.robot import RobotController
from src.features.camera import CameraController
from src.features.sliders import SlidersController
from src.features.kinematics import KinematicsController
from src.features.simulation.simulation_controller import SimulationController
from src.features.graph import GraphController


class MainInitMixin:
    """
    Mixin responsable de la inicializacion de la interfaz principal.

    Proporciona metodos para configurar los layouts, splitters y group boxes,
    asi como para inicializar los controladores de los modulos funcionales
    (camara, simulacion, graficos, sliders, cinematica).
    """

    def setup_ui(self, main_widget):
        """
        Configura la UI completa en el widget proporcionado.

        Crea los splitters horizontal y vertical, los group boxes para
        los paneles y establece las politicas de tamano iniciales.

        Args:
            main_widget (QWidget): Widget contenedor principal.
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

        self.gridLayout = QGridLayout(self.main_widget)
        self.gridLayout.setObjectName("gridLayout")
        self.gridLayout.setContentsMargins(5, 5, 5, 5)

        self.barContentLayout = QHBoxLayout()
        self.barContentLayout.setObjectName("barContentLayout")
        self.barContentLayout.setContentsMargins(0, 0, 0, 0)
        self.barContentLayout.setSpacing(0)

        self.contentSplitter = QSplitter(parent=self.main_widget)
        self.contentSplitter.setOrientation(Qt.Orientation.Horizontal)
        self.contentSplitter.setObjectName("contentSplitter")
        self.contentSplitter.setHandleWidth(8)
        self.contentSplitter.setContentsMargins(0, 0, 0, 0)

        self.visualSplitter = QSplitter(parent=self.contentSplitter)
        self.visualSplitter.setOrientation(Qt.Orientation.Vertical)
        self.visualSplitter.setObjectName("visualSplitter")
        self.visualSplitter.setHandleWidth(8)
        self.visualSplitter.setContentsMargins(0, 0, 0, 0)

        self.controlSplitter = QSplitter(parent=self.contentSplitter)
        self.controlSplitter.setOrientation(Qt.Orientation.Vertical)
        self.controlSplitter.setObjectName("ControlslSplitter")
        self.controlSplitter.setHandleWidth(8)
        self.controlSplitter.setContentsMargins(0, 0, 0, 0)

        box_size_policy = QSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.modelBox = QGroupBox(parent=self.visualSplitter)
        self.modelBox.setTitle("")
        self.modelBox.setObjectName("modelBox")
        self.modelBox.setContentsMargins(0, 0, 0, 0)
        self.modelBox.setSizePolicy(box_size_policy)

        self.cameraBox = QGroupBox(parent=self.visualSplitter)
        self.cameraBox.setTitle("")
        self.cameraBox.setObjectName("cameraBox")
        self.cameraBox.setContentsMargins(0, 0, 0, 0)
        self.cameraBox.setSizePolicy(box_size_policy)

        self.graphsBox = QGroupBox(parent=self.controlSplitter)
        self.graphsBox.setTitle("")
        self.graphsBox.setObjectName("graphsBox")
        self.graphsBox.setContentsMargins(0, 0, 0, 0)
        box_size_policy.setHorizontalStretch(0)
        box_size_policy.setVerticalStretch(0)
        self.graphsBox.setSizePolicy(box_size_policy)

        self.controlsBox = QGroupBox(parent=self.controlSplitter)
        self.controlsBox.setTitle("")
        self.controlsBox.setAlignment(
            Qt.AlignmentFlag.AlignBottom |
            Qt.AlignmentFlag.AlignLeading |
            Qt.AlignmentFlag.AlignLeft
        )
        self.controlsBox.setObjectName("controlsBox")
        self.controlsBox.setSizePolicy(box_size_policy)

        self.verticalLayout_2 = QVBoxLayout(self.controlsBox)
        self.verticalLayout_2.setSpacing(0)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")

        self.barContentLayout.addWidget(self.contentSplitter)
        self.gridLayout.addLayout(self.barContentLayout, 0, 0, 1, 1)

        self.contentSplitter.setSizes([400, 500])
        self.visualSplitter.setSizes([100, 100])
        self.controlSplitter.setSizes([300, 100])

    def init_camera(self):
        """
        Inicializa el modulo de camara y lo agrega a su contenedor.
        """
        if not self.cameraBox.layout():
            layout = QVBoxLayout(self.cameraBox)
            layout.setContentsMargins(0, 0, 0, 0)
            self.cameraBox.setLayout(layout)

        self.camera_controller = CameraController(self)
        self.cameraBox.layout().addWidget(self.camera_controller.get_widget())

        self.camera_controller.status_changed.connect(
            self.camera_connected_label.setText)
        self.camera_controller.active_state_changed.connect(
            lambda active: self.camera_interval_submenu.setEnabled(active)
            if hasattr(self, 'camera_interval_submenu') else None
        )

    def init_controls(self):
        """
        Inicializa los paneles de control (sliders y cinematica).

        Crea los controladores de sliders y cinematica, los agrega a un
        contenedor compartido y configura la visibilidad inicial.
        """
        self.kinematics_controller = KinematicsController(self)
        self.sliders_controller = SlidersController(self)
        self.modes_widget = QWidget()

        if not self.modes_widget.layout():
            layout = QHBoxLayout(self.modes_widget)
            layout.setContentsMargins(0, 0, 0, 0)
            self.modes_widget.setLayout(layout)

        self.modes_widget.layout().addWidget(
            self.sliders_controller.get_widget())
        self.modes_widget.layout().addWidget(
            self.kinematics_controller.get_widget())
        self.modes_widget.setMaximumSize(QSize(1050, 300))

        self.kinematics_controller.get_widget().hide()

        self.controlsBox.layout().addStretch(1)
        self.controlsBox.layout().addWidget(self.modes_widget)

    def init_tool_bar(self):
        """
        Crea la barra de herramientas lateral con las acciones de la aplicacion.

        Incluye botones de visibilidad de paneles (modelo 3D, camara,
        graficos, controles), activacion de busqueda visual (ChArUco,
        esferas) y controles de flujo (start, pause, stop, reset).
        """
        self.actions_toolbar = QToolBar()
        self.actions_toolbar.setObjectName("actions_toolbar")
        self.actions_toolbar.setOrientation(Qt.Orientation.Vertical)
        self.actions_toolbar.setIconSize(QSize(24, 24))
        self.actions_toolbar.setMinimumHeight(30)
        self.actions_toolbar.setMinimumWidth(30)
        self.actions_toolbar.setContentsMargins(0, 0, 0, 0)
        self.actions_toolbar.setMovable(True)
        self.actions_toolbar.setFloatable(True)

        self.toolbar_spacer = QWidget()
        self.toolbar_spacer.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        self.toolbar_spacer.setObjectName("toolbar_spacer")

        self.sim_view_icon = QIcon(os.path.join("icons:armView.png"))
        self.camera_view_icon = QIcon(os.path.join("icons:cameraView.png"))
        self.graphs_view_icon = QIcon(os.path.join("icons:graphView.png"))
        self.controls_view_icon = QIcon(
            os.path.join("icons:controlsView.png"))

        self.model_action = self.actions_toolbar.addAction(
            self.sim_view_icon, "Vista de simulación")
        self.model_action.setObjectName("simulation_view_button")
        self.model_action.setStatusTip(
            "Mostrar/Ocultar el modelo 3D de la simulación")
        self.model_action.setCheckable(True)

        self.camera_action = self.actions_toolbar.addAction(
            self.camera_view_icon, "Vista de cámara")
        self.camera_action.setObjectName("camera_view_button")
        self.camera_action.setStatusTip("Mostrar/Ocultar la cámara")
        self.camera_action.setCheckable(True)

        self.graphs_action = self.actions_toolbar.addAction(
            self.graphs_view_icon, "Vista de gráficas")
        self.graphs_action.setObjectName("graph_view_button")
        self.graphs_action.setStatusTip("Mostrar/Ocultar las gráficas")
        self.graphs_action.setCheckable(True)

        self.controls_action = self.actions_toolbar.addAction(
            self.controls_view_icon, "Vista de controles")
        self.controls_action.setObjectName("controls_view_button")
        self.controls_action.setStatusTip("Mostrar/Ocultar los controles")
        self.controls_action.setCheckable(True)

        self.actions_toolbar.widgetForAction(self.model_action)
        self.actions_toolbar.widgetForAction(self.camera_action)
        self.actions_toolbar.widgetForAction(self.graphs_action)
        self.actions_toolbar.widgetForAction(self.controls_action)

        self.actions_toolbar.addSeparator()
        self.actions_toolbar.addWidget(self.toolbar_spacer)
        self.actions_toolbar.addSeparator()

        self.charuco_icon = QIcon(os.path.join("icons:gridSearch.png"))
        self.sphere_icon = QIcon(os.path.join("icons:geometrySearch.png"))

        self.charuco_action = self.actions_toolbar.addAction(
            self.charuco_icon, "Tablero ChArUco")
        self.charuco_action.setObjectName("charuco_action")
        self.charuco_action.setStatusTip(
            "Activa/Desactiva la deteccion del tablero")
        self.charuco_action.setCheckable(True)

        self.sphere_action = self.actions_toolbar.addAction(
            self.sphere_icon, "Activar Objetos")
        self.sphere_action.setObjectName("sphere_action")
        self.sphere_action.setStatusTip(
            "Activa/Desactiva la deteccion de las esferas de colores")
        self.sphere_action.setCheckable(True)

        config_manager = ConfigSignalManager.get_instance()
        settings = config_manager.get_param("settings.json", default={})
        camera_config = settings.get("camera", {})
        if "charuco" in camera_config:
            self.charuco_action.setChecked(camera_config.get("charuco"))
        if "circle" in camera_config:
            self.sphere_action.setChecked(camera_config.get("circle"))

        self.actions_toolbar.addSeparator()

        self.start_icon = QIcon(os.path.join("icons:play.png"))
        self.pause_icon = QIcon(os.path.join("icons:pause.png"))
        self.stop_icon = QIcon(os.path.join("icons:stop.png"))
        self.reset_icon = QIcon(os.path.join("icons:refresh.png"))

        self.start_action = self.actions_toolbar.addAction(
            self.start_icon, "Iniciar")
        self.start_action.setObjectName("start_button")
        self.start_action.setStatusTip("Iniciar la ejecución")
        self.start_action.setCheckable(True)

        self.pause_action = self.actions_toolbar.addAction(
            self.pause_icon, "Pausar")
        self.pause_action.setObjectName("pause_button")
        self.pause_action.setStatusTip("Pausar la ejecución")
        self.pause_action.setEnabled(False)
        self.pause_action.setCheckable(True)

        self.stop_action = self.actions_toolbar.addAction(
            self.stop_icon, "Detener")
        self.stop_action.setObjectName("stop_button")
        self.stop_action.setStatusTip("Detener la ejecución")
        self.stop_action.setEnabled(False)
        self.stop_action.setCheckable(True)
        self.stop_action.setChecked(True)

        self.reset_action = self.actions_toolbar.addAction(
            self.reset_icon, "Reiniciar")
        self.reset_action.setObjectName("reset_button")
        self.reset_action.setStatusTip("Reiniciar los valores")

        self.start_button = self.actions_toolbar.widgetForAction(
            self.start_action)
        self.pause_button = self.actions_toolbar.widgetForAction(
            self.pause_action)
        self.stop_button = self.actions_toolbar.widgetForAction(
            self.stop_action)
        self.reset_button = self.actions_toolbar.widgetForAction(
            self.reset_action)

    def init_simulation(self):
        """
        Inicializa el modulo de simulacion y lo agrega a su contenedor.

        Crea el SimulationController que integra la vista Quick3D con
        el motor de fisica PyBullet.
        """
        if not self.modelBox.layout():
            self.sim_layout = QVBoxLayout(self.modelBox)
            self.sim_layout.setContentsMargins(0, 0, 0, 0)
            self.modelBox.setLayout(self.sim_layout)

        self.simulation_controller = SimulationController(
            self, self.preloaded_data, self.robot_id)
        self.sim_layout.addWidget(
            self.simulation_controller.get_simulation_widget())

    def init_openbotv(self, com: str):
        """
        Inicializa la conexion con el microcontrolador via puerto serie.

        Crea el RobotController y el DataController para el dominio fisico.

        Args:
            com (str): Nombre del puerto COM (e.g. 'COM3').
        """
        self.robot_service = RobotController(com)

        self.robot_controller = DataController(
            Modes.SLIDERS, Units.DEG, Domains.PHYSICAL,
            robot_controller=self.robot_service
        )

        self.robot_service.start_service()

        self.connect_action.setEnabled(False)

    def init_graphics(self):
        """
        Inicializa el modulo de graficos de telemetria.

        Crea el GraphController con el servicio de cinematica para
        el calculo de trayectorias cartesianas.
        """
        if not self.graphsBox.layout():
            graph_layout = QVBoxLayout(self.graphsBox)
            graph_layout.setContentsMargins(0, 0, 0, 0)
            self.graphsBox.setLayout(graph_layout)

        self.graphsBox.setStyleSheet("""padding: 0px;""")

        self.graph_controller = GraphController(
            self, self.kinematics_controller.get_worker())
        self.graphsBox.layout().addWidget(self.graph_controller.get_widget())

    def center_window(self):
        """
        Centra la ventana en la pantalla al iniciar la aplicacion.
        """
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)
