"""
Módulo principal de la interfaz gráfica de usuario.

Define la clase MainWindow, la cual orquesta la integración de múltiples mixins
para gestionar la inicialización, acciones, menús y la barra de título personalizada.
Centraliza el control de la simulación y la conexión con el hardware.

Conexiones:
    - Hereda de `FramelessMainWindow` para una estética moderna sin bordes.
    - Utiliza `ThemeManager` para la gestión de estilos claro/oscuro.
    - Se comunica con controladores de cámara, simulación, cinemática y sliders.
"""

from qframelesswindow import FramelessMainWindow
from PyQt6.QtWidgets import QMessageBox, QVBoxLayout, QWidget, QLabel, QApplication, QMainWindow
from PyQt6.QtCore import QCoreApplication, Qt
from src.main_window.mixins import (
    MainInitMixin, MainActionsMixin, MainMenuMixin, MainTitleBarMixin)
from src.services.devices import CameraDevices
from src.services.devices.device_monitor import get_device_monitor
from src.services.data.signals import SearchSignalManager, ThemeSignalManager, ConfigSignalManager
from src.services.styling import ThemeManager
from src.services.data import config_manager, DataController
from src.services.ui.notification_manager import NotificationManager
from src.services.data.enums.types import NotificationType


class MainWindow(FramelessMainWindow, MainInitMixin, MainActionsMixin, MainMenuMixin):
    """
    Ventana principal de la aplicación de control del brazo robótico.

    Hereda de múltiples mixins que organizan la estructura de la interfaz,
    widgets y comportamiento de las diferentes secciones (Cámara, Gráficos,
    Controles y Simulación).
    """

    def __init__(self, quick3d, robot_id):
        """
        Inicializa la ventana principal y configura todos los sub-sistemas.

        Args:
            quick3d (PreloadedContainer): Datos y recursos pre-cargados de QML/Quick3D.
            robot_id (str): Identificador único para el robot (URDF/Config).
        """
        super().__init__()
        # Inicialización centralizada de configuración (antes de cualquier controller)
        self.config_manager = ConfigSignalManager.get_instance()
        config_manager.init_config()
        for filename in config_manager.DEFAULTS.keys():
            data = config_manager.load(filename)
            self.config_manager.set_all_config(filename, data)

        # Orquestador Central de Datos e Inter-Controladores
        self.data_controller = DataController()

        self.preloaded_data = quick3d
        self.robot_id = robot_id
        self.simulation_controller = None
        self.stopped = True
        self.camera_paused = False
        self.hab_simulation = True
        self.theme_manager = ThemeManager(self)
        self.theme_signal_manager = ThemeSignalManager.get_instance()
        self.theme_signal_manager.theme_changed.connect(
            self._on_external_theme_changed)
        self.com = None
        self.com_connected_label = QLabel("Micro no conectado")
        self.camera_connected_label = QLabel("Cámara no conectada")
        self.connected_to_robot = False
        self.last_cameras = None
        self.last_com = None
        self.last_camera_name = None

        # Crear contenedor principal para manejar barra de titulo personalizada y contenido
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Barra de titulo personalizada
        self.create_main_menu()
        self.title_bar = MainTitleBarMixin(self)
        self.title_bar.setObjectName("title_bar")
        self.setTitleBar(self.title_bar)
        container_layout.addWidget(self.title_bar)

        self.inner_window = QMainWindow()
        self.inner_window.setWindowFlags(Qt.WindowType.Widget)
        self.inner_window.setObjectName("inner_window")
        container_layout.addWidget(self.inner_window)

        # setup_ui ahora gestiona los docks directamente en inner_window
        self.setup_ui()

        # Inicializacion de servicios y controladores (definidos en Mixins)
        self.create_status_bar()
        self.init_camera()
        self.init_controls()
        self.init_tool_bar()
        self.init_simulation()
        self.init_graphics()
        self.setup_connections()

        # Añadir toolbar de acciones
        self.inner_window.addToolBar(
            Qt.ToolBarArea.LeftToolBarArea,
            self.actions_toolbar
        )

        # Cargar configuración de visibilidad de paneles desde archivo
        settings: dict = self.config_manager.get_param(
            "settings.json", default={})
        content = settings.get("content", {})
        mode = settings.get('mode', {})
        mapping_content = {
            "camera": (self.cameraDock, self.camera_action, True),
            "model": (self.modelDock, self.model_action, True),
            "graphs": (self.graphsDock, self.graphs_action, True),
            "controls": (self.controlsDock, self.controls_action, not mode.get("pick_place", False)),
        }

        for key, (dock, action, enable) in mapping_content.items():
            if key in content:
                state = bool(content[key])
                dock.toggleView(state)
                action.setChecked(state)
                action.setEnabled(bool(enable))

            # Sincronizar dock -> action (por si se cierra desde el botón 'X' del dock)
            dock.visibilityChanged.connect(action.setChecked)

        # Cargar configuración de búsqueda visual
        camera = settings.get("camera", {})
        search_manager = SearchSignalManager.get_instance()
        for key, widget in camera.items():
            state = bool(camera[key])
            if key == "charuco":
                search_manager.set_charuco(state)
            elif key == "circle":
                search_manager.set_circle(state)

        self.hab_simulation = settings.get(
            "simulation", {}).get("activated", True)

        # Configurar modo de control inicial (Sliders o Cinemática)
        mapping_mode = {
            'sliders': self.sliders_controller.get_widget(),
            'kinematics': self.kinematics_controller.get_widget()
        }

        for key, widget in mapping_mode.items():
            if key in mode:
                state = bool(mode[key])
                widget.setVisible(state)
                if key == 'sliders' and not state:
                    self.kinematics_controller.get_widget().set_horizontal_layout()

        # Conectar señal al cambio de tema del sistema
        QApplication.instance().styleHints().colorSchemeChanged.connect(
            self.theme_manager.update_theme)
        self.theme_manager.load_current_theme()

        # Instalar monitor de dispositivos (Cámaras y Puertos COM)
        self.camera_devices = CameraDevices()
        self._device_monitor = get_device_monitor(
            self.get_com_ports, self.camera_devices.get_cameras)
        self._device_monitor.install_filter(QCoreApplication.instance())

        self.get_com_ports()
        self.camera_devices.get_cameras()
        self.setCentralWidget(container)

        # Restaurar geometría desde config
        self.setMinimumSize(800, 600)
        settings = config_manager.load("settings.json")
        win_cfg = settings.get("window", {})
        if win_cfg.get("maximized"):
            self.showMaximized()
        else:
            w = win_cfg.get("width", 1280)
            h = win_cfg.get("height", 720)
            self.resize(w, h)
            self.center_window()

        noti_manager = NotificationManager.get_instance()
        noti_manager.set_main_window(self)

    def _on_external_theme_changed(self, is_dark: bool):
        """
        Actualiza el estilo cuando se detecta un cambio de tema externo.

        Args:
            is_dark (bool): True si el nuevo tema es oscuro.
        """
        self.theme_manager.apply_theme_from_signal(is_dark)

    def setup_connections(self):
        """
        Configura todas las conexiones de señales y slots de la interfaz.

        Enlaza botones, acciones de menu y eventos de controladores con sus
        respectivas funciones de respuesta.
        """
        # Visibilidad de ventanas/paneles
        if hasattr(self, 'cameraBox'):
            if hasattr(self, 'camera_action'):
                self.camera_action.triggered.connect(
                    self.toggle_visibility_camera_event)
        if hasattr(self, 'modelBox'):
            if hasattr(self, 'model_action'):
                self.model_action.triggered.connect(
                    self.toggle_visibility_model_event)
        if hasattr(self, 'graphs_action'):
            self.graphs_action.triggered.connect(
                self.toggle_visibility_graphs_event)
        if hasattr(self, 'controls_action'):
            self.controls_action.triggered.connect(
                self.toggle_visibility_controls_event)

        # Configuración de detección visual
        search_manager = SearchSignalManager.get_instance()
        if hasattr(self, 'charuco_action'):
            self.charuco_action.toggled.connect(
                self.toggle_charuco_search)
            search_manager.charuco_search_changed.connect(
                self.charuco_action.setChecked)
        if hasattr(self, 'sphere_action'):
            self.sphere_action.toggled.connect(
                self.toggle_sphere_search)
            search_manager.circle_search_changed.connect(
                self.sphere_action.setChecked)
        if hasattr(self, 'camera_calibration_action'):
            self.camera_calibration_action.triggered.connect(
                self.initiate_camera_calibration)
        if hasattr(self, 'color_calibration_action'):
            self.color_calibration_action.triggered.connect(
                self.initiate_color_calibration)

        # Visibilidad y uso de controles (Manual/Cinematico)
        if hasattr(self, "sliders_action"):
            self.sliders_action.toggled.connect(self.toggle_sliders_controls)
        if hasattr(self, "kinematics_action"):
            self.kinematics_action.toggled.connect(
                self.toggle_kinematics_controls)
        if hasattr(self, "pick_place_action"):
            self.pick_place_action.toggled.connect(
                self.toggle_pick_place_controls)

        # Sincronizacion Kinematics -> Sliders
        if hasattr(self, 'kinematics_controller') and hasattr(self, 'sliders_controller'):
            self.kinematics_controller.status_updated.connect(
                self.sliders_controller.set_external_values)

        # Botones de control de flujo (Start, Pause, Stop, Reset)
        if hasattr(self, 'start_action'):
            self.start_action.triggered.connect(self.start)
        if hasattr(self, 'pause_action'):
            self.pause_action.triggered.connect(self.pause)
        if hasattr(self, 'stop_action'):
            self.stop_action.triggered.connect(self.stop)
        if hasattr(self, 'reset_action'):
            self.reset_action.triggered.connect(self.reset)

        # Activación de simulación física
        if hasattr(self, 'simulation_action'):
            self.simulation_action.triggered.connect(
                self.toggle_activation_simulation_event)
        if hasattr(self, 'shadows_action'):
            self.shadows_action.triggered.connect(self.toggle_shadows_event)
        if hasattr(self, 'grid_action'):
            self.grid_action.triggered.connect(self.toggle_grid_event)
        if hasattr(self, 'axes_action'):
            self.axes_action.triggered.connect(self.toggle_axes_event)
        if hasattr(self, 'labels_action'):
            self.labels_action.triggered.connect(self.toggle_labels_event)
        if hasattr(self, 'aa_action'):
            self.aa_action.triggered.connect(self.toggle_aa_event)

        # Control de temas y conexión de hardware
        if hasattr(self, 'theme_action'):
            self.theme_action.triggered.connect(
                self.theme_manager.toggle_theme_event)

        if hasattr(self, 'connect_action'):
            self.connect_action.triggered.connect(self.connect_robot)

    def closeEvent(self, event):
        """
    Gestiona el cierre de la aplicación y la liberación de recursos.

    Muestra un diálogo de confirmación y asegura que los hilos de cámara,
    simulación y ventanas secundarias se detengan correctamente.

        Args:
            event (QCloseEvent): Evento de cierre de Qt.
        """
        msg = QMessageBox(self)
        msg.setWindowTitle("Salir")
        msg.setText("¿Seguro que quieres cerrar la aplicación?")
        msg.setIcon(QMessageBox.Icon.Question)

        msg.setWindowFlags(
            msg.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
        )

        si_btn = msg.addButton("Sí", QMessageBox.ButtonRole.YesRole)
        no_btn = msg.addButton("No", QMessageBox.ButtonRole.NoRole)
        msg.setDefaultButton(no_btn)

        msg.exec()

        if msg.clickedButton() == si_btn:
            # Guardar geometría de ventana
            is_max = self.isMaximized()
            if not is_max:
                config_manager.set_value(
                    "settings.json", ["window", "width"], self.width())
                config_manager.set_value(
                    "settings.json", ["window", "height"], self.height())
            config_manager.set_value(
                "settings.json", ["window", "maximized"], is_max)

            # Detención segura de procesos
            if hasattr(self, "calibration_window"):
                if hasattr(self.calibration_window, "calibration_interface"):
                    self.calibration_window.calibration_interface.stop_video()
                self.calibration_window.close()
            if hasattr(self, "color_window"):
                if hasattr(self.color_window, "color_interface"):
                    self.color_window.color_interface.close()
                self.color_window.close()
            if hasattr(self, "camera_controller"):
                self.camera_controller.stop_video()
            if hasattr(self, 'graph_controller'):
                self.graph_controller.cleanup()
            event.accept()
        else:
            event.ignore()
