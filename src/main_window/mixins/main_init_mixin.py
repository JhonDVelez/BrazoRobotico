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
import PyQt6Ads as ads
from src.services.data.enums import Modes, Units, Domains
from src.services.data import DataController
from src.services.data.signals import ConfigSignalManager, ThemeSignalManager
from src.services.robot import RobotController
from src.features.camera import CameraController
from src.features.sliders import SlidersController
from src.features.kinematics import KinematicsController
from src.features.pick_and_place import PickAndPlaceController
from src.features.simulation.simulation_controller import SimulationController
from src.features.graph import GraphController


class MainInitMixin:
    """
    Mixin responsable de la inicializacion de la interfaz principal.

    Proporciona metodos para configurar los layouts, splitters y group boxes,
    asi como para inicializar los controladores de los modulos funcionales
    (camara, simulacion, graficos, sliders, cinematica).
    """

    def setup_ui(self, dummy_widget=None):
        """
        Configura la UI dinámica basada en PyQt6-Ads.

        Crea los contenedores acoplables para el modelo, cámara, gráficas y controles.
        La gestión del layout ahora reside exclusivamente en el CDockManager.
        """
        # Inicializar el Dock Manager. No establecemos Central Widget manualmente
        # para evitar conflictos que causan el borrado de objetos en C++.
        # ads.CDockManager.setConfigFlags(
        #     ads.CDockManager.eConfigFlag.DefaultOpaqueConfig)
        ads.CDockManager.setConfigFlag(
            ads.CDockManager.eConfigFlag.DisableTabTextEliding, True)
        ads.CDockManager.setConfigFlag(
            ads.CDockManager.eConfigFlag.AlwaysShowTabs, False)
        ads.CDockManager.setConfigFlag(
            ads.CDockManager.eConfigFlag.HideSingleCentralWidgetTitleBar, True)
        ads.CDockManager.setConfigFlag(
            ads.CDockManager.eConfigFlag.DockAreaDynamicTabsMenuButtonVisibility, True)

        self.dock_manager = ads.CDockManager(self.inner_window)
        self.dock_manager.setObjectName("dockManager")

        # Resolver el enum de áreas para la versión 4.5.0
        Area = ads.DockWidgetArea

        box_size_policy = QSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # 1. Dock del Modelo 3D
        self.modelDock = ads.CDockWidget("Visualización 3D")
        self.modelDock.setObjectName("modelDock")
        self.modelBox = QGroupBox(self.inner_window)
        self.modelBox.setTitle("")
        self.modelBox.setObjectName("modelBox")
        # Forzamos eliminación de bordes nativos también vía código
        self.modelBox.setFlat(True)
        self.modelBox.setSizePolicy(box_size_policy)
        self.modelDock.setWidget(self.modelBox)
        self.dock_manager.addDockWidget(
            Area.LeftDockWidgetArea, self.modelDock)
        self._configure_dock_title_bar(self.modelDock)
        # 2. Dock de la Cámara
        self.cameraDock = ads.CDockWidget("Cámara en Vivo")
        self.cameraDock.setObjectName("cameraDock")
        self.cameraBox = QGroupBox(self.inner_window)
        self.cameraBox.setTitle("")
        self.cameraBox.setObjectName("cameraBox")
        self.cameraBox.setFlat(True)
        self.cameraBox.setSizePolicy(box_size_policy)
        self.cameraDock.setWidget(self.cameraBox)
        self.dock_manager.addDockWidget(
            Area.BottomDockWidgetArea, self.cameraDock, self.modelDock.dockAreaWidget())
        self._configure_dock_title_bar(self.cameraDock)

        # 3. Dock de Gráficas
        self.graphsDock = ads.CDockWidget("Telemetría y Gráficas")
        self.graphsDock.setObjectName("graphsDock")
        self.graphsBox = QGroupBox(self.inner_window)
        self.graphsBox.setTitle("")
        self.graphsBox.setObjectName("graphsBox")
        self.graphsBox.setFlat(True)
        self.graphsBox.setSizePolicy(box_size_policy)
        self.graphsDock.setWidget(self.graphsBox)
        self.dock_manager.addDockWidget(
            Area.RightDockWidgetArea, self.graphsDock)
        self._configure_dock_title_bar(self.graphsDock)

        # 4. Dock de Controles
        self.controlsDock = ads.CDockWidget("Panel de Control")
        self.controlsDock.setObjectName("controlsDock")
        self.controlsBox = QGroupBox(self.inner_window)
        self.controlsBox.setTitle("")
        self.controlsBox.setObjectName("controlsBox")
        self.controlsBox.setFlat(True)
        self.controlsBox.setSizePolicy(box_size_policy)

        self.verticalLayout_2 = QVBoxLayout(self.controlsBox)
        self.verticalLayout_2.setSpacing(0)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)

        self.controlsDock.setWidget(self.controlsBox)
        self.dock_manager.addDockWidget(
            Area.BottomDockWidgetArea, self.controlsDock, self.graphsDock.dockAreaWidget())
        self._configure_dock_title_bar(self.controlsDock)

        # Configurar proporciones iniciales si es posible (ADS maneja esto de forma interna tras el layout)
        # ADS no usa setSizes como QSplitter, se basa en factores de estiramiento y jerarquía de áreas.
        for i, dock in self.dock_manager.dockWidgetsMap().items():
            self._configure_dock_title_bar(dock)
            dock.topLevelChanged.connect(
                lambda floating, d=dock: self._on_dock_floating_changed(d))

    def _configure_dock_title_bar(self, dock):
        """Apply title bar margins and button object names to a dock widget."""
        area = dock.dockAreaWidget()
        if area is None:
            return
        title = area.titleBar()
        area.layout().setContentsMargins(0, 0, 0, 0)
        dock.layout().setContentsMargins(0, 0, 0, 0)
        undock_btn = title.button(ads.TitleBarButton.TitleBarButtonUndock)
        if undock_btn is not None:
            undock_btn.setObjectName("undockBtn")
            undock_btn.setVisible(True)
        close_btn = title.button(ads.TitleBarButton.TitleBarButtonClose)
        if close_btn is not None:
            close_btn.setObjectName("closeBtn")

    def _on_dock_floating_changed(self, dock):
        """Re-apply title bar config when a dock is docked (floating=False) or undocked (floating=True)."""
        self._configure_dock_title_bar(dock)

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

        # Inicializar el controlador de Pick and Place asociado a la cámara
        self.pick_and_place_controller = PickAndPlaceController(
            self.camera_controller.get_widget()
        )

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

        self.toolbar_signal_manager = ThemeSignalManager.get_instance()
        is_dark = self.toolbar_signal_manager.get_current_theme() == Qt.ColorScheme.Dark

        self.model_action = self.actions_toolbar.addAction(
            self.toolbar_signal_manager.get_toolbar_icon('sim_view', is_dark), "Vista de simulación")
        self.model_action.setObjectName("simulation_view_button")
        self.model_action.setStatusTip(
            "Mostrar/Ocultar el modelo 3D de la simulación")
        self.model_action.setCheckable(True)

        self.camera_action = self.actions_toolbar.addAction(
            self.toolbar_signal_manager.get_toolbar_icon('camera_view', is_dark), "Vista de cámara")
        self.camera_action.setObjectName("camera_view_button")
        self.camera_action.setStatusTip("Mostrar/Ocultar la cámara")
        self.camera_action.setCheckable(True)

        self.graphs_action = self.actions_toolbar.addAction(
            self.toolbar_signal_manager.get_toolbar_icon('graphs_view', is_dark), "Vista de gráficas")
        self.graphs_action.setObjectName("graph_view_button")
        self.graphs_action.setStatusTip("Mostrar/Ocultar las gráficas")
        self.graphs_action.setCheckable(True)

        self.controls_action = self.actions_toolbar.addAction(
            self.toolbar_signal_manager.get_toolbar_icon('controls_view', is_dark), "Vista de controles")
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

        self.charuco_icon = self.toolbar_signal_manager.get_toolbar_icon(
            'charuco', is_dark)
        self.sphere_icon = self.toolbar_signal_manager.get_toolbar_icon(
            'sphere', is_dark)

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

        self.start_action = self.actions_toolbar.addAction(
            self.toolbar_signal_manager.get_toolbar_icon('start', is_dark), "Iniciar")
        self.start_action.setObjectName("start_button")
        self.start_action.setStatusTip("Iniciar la ejecución")
        self.start_action.setCheckable(True)

        self.pause_action = self.actions_toolbar.addAction(
            self.toolbar_signal_manager.get_toolbar_icon('pause', is_dark), "Pausar")
        self.pause_action.setObjectName("pause_button")
        self.pause_action.setStatusTip("Pausar la ejecución")
        self.pause_action.setEnabled(False)
        self.pause_action.setCheckable(True)

        self.stop_action = self.actions_toolbar.addAction(
            self.toolbar_signal_manager.get_toolbar_icon('stop', is_dark), "Detener")
        self.stop_action.setObjectName("stop_button")
        self.stop_action.setStatusTip("Detener la ejecución")
        self.stop_action.setEnabled(False)
        self.stop_action.setCheckable(True)
        self.stop_action.setChecked(True)

        self.reset_action = self.actions_toolbar.addAction(
            self.toolbar_signal_manager.get_toolbar_icon('reset', is_dark), "Reiniciar")
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

        Crea el RobotController para el dominio fisico. El DataController
        central ya esta orquestando las señales.

        Args:
            com (str): Nombre del puerto COM (e.g. 'COM3').
        """
        self.robot_service = RobotController(com)
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
