import ctypes
from ctypes import wintypes, cast, POINTER
import win32con
from qframelesswindow import FramelessMainWindow
from PyQt6.QtWidgets import QMessageBox, QVBoxLayout, QWidget, QLabel, QApplication
from PyQt6.QtCore import QAbstractNativeEventFilter, QCoreApplication, QTimer, Qt
from .main_window import (MainInitMixin, MainActionsMixin, ThemeManager,
                          MainMenuMixin, MainThemeMixin, MainTitleBarMixin)
from data import SearchSignalManager
from data import config_manager as cfg

# os.environ["QT_LOGGING_RULES"] = "qt.qpa.window=false"
DBT_DEVTYP_PORT = 0x00000003


class MainWindow(FramelessMainWindow, MainInitMixin, MainActionsMixin, MainMenuMixin,
                 MainThemeMixin):
    """ Ventana principal de la interfaz la cual hereda todos los mixin los cuales solo almacenan
        los métodos utilizados en la interfaz como estructura de las diferentes secciones, widgets
        y el comportamiento de estos.
    """

    def __init__(self, quick3d, robot_id):
        super().__init__()
        self.preloaded_data = quick3d
        self.robot_id = robot_id
        self.simulation_interface = None
        self.stopped = True
        self.camera_paused = False
        self.hab_simulation = True
        self.theme_manager = ThemeManager.get_instance()
        self.com = None
        self.com_connected_label = QLabel("Micro no conectado")
        self.camera_connected_label = QLabel("Cámara no conectada")
        self.connected_to_robot = False
        self.last_cameras = None
        self.last_com = None
        self.last_camera_name = None

        # Crear contenedor principal
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Barra de título
        self.create_main_menu()
        self.title_bar = MainTitleBarMixin(self)
        # necesario para acciones de ventana como arrastrar/min/max
        self.setTitleBar(self.title_bar)
        layout.addWidget(self.title_bar)

        self.central_widget = QWidget()
        self.setup_ui(self.central_widget)
        layout.addWidget(self.central_widget)

        self.create_status_bar()
        self.init_camera()
        self.init_controls()
        self.init_simulation()
        self.init_graphics()
        self.setup_connections()

        settings = cfg.get("settings.json")
        content = settings.get("content")
        mapping_content = {
            "camera": self.cameraBox,
            "model": self.modelBox,
            "graphs": self.graphsBox,
            "controls": self.controlsBox
        }

        for key, widget in mapping_content.items():
            if key in content:
                # Usamos setVisible para evitar el if/else interno
                widget.setVisible(bool(content[key]))

        camera = settings.get("camera")
        search_manager = SearchSignalManager().get_instance()
        for key, widget in camera.items():
            state = bool(camera[key])
            if key == "charuco":
                search_manager.set_charuco(state)
            elif key == "ellipse":
                search_manager.set_ellipse(state)

        self.hab_simulation = settings.get(
            "simulation").get("activated", True)

        mapping_mode = {
            'sliders': self.slider_widget,
            'kinematics': self.kinematics_widget
        }
        mode = settings.get('mode')
        for key, widget in mapping_mode.items():
            if key in mode:
                state = bool(mode[key])
                widget.setVisible(state)
                if key == 'sliders' and not state:
                    self.kinematics_widget.set_horizontal_layout()
        self.toggle_theme_event()

        # Conectar señal al cambio de tema
        QApplication.instance().styleHints().colorSchemeChanged.connect(self.update_theme)

        # ahora el central widget real es el contenedor con barra + contenido
        self.setCentralWidget(container)

        self.resize(1280, 720)
        self.center_window()

        self._dev_filter = DeviceEventFilter(
            self.get_com_ports, self.get_cameras)
        QCoreApplication.instance().installNativeEventFilter(self._dev_filter)

    def setup_connections(self):
        """ Configura las conexiones de eventos para los botones de la interfaz
        """
        # Visibilidad de ventanas
        if hasattr(self, 'cameraBox'):
            if hasattr(self, 'camera_action'):
                self.camera_action.toggled.connect(
                    self.toggle_visibility_camera_event)
        if hasattr(self, 'modelBox'):
            if hasattr(self, 'model_action'):
                self.model_action.toggled.connect(
                    self.toggle_visibility_model_event)
        if hasattr(self, 'graphs_action'):
            self.graphs_action.toggled.connect(
                self.toggle_visibility_graphs_event)
        if hasattr(self, 'controls_action'):
            self.controls_action.toggled.connect(
                self.toggle_visibility_controls_event)

        # Configuración de cámara
        if hasattr(self, 'charuco_action'):
            self.charuco_action.toggled.connect(
                self.toggle_charuco_search)
        if hasattr(self, 'sphere_action'):
            self.sphere_action.toggled.connect(
                self.toggle_sphere_search)
        if hasattr(self, 'camera_calibration_action'):
            self.camera_calibration_action.triggered.connect(
                self.initiate_camera_calibration)

        # Visibilidad y uso de controles
        if hasattr(self, "sliders_action"):
            self.sliders_action.toggled.connect(self.toggle_sliders_controls)
        if hasattr(self, "kinematics_action"):
            self.kinematics_action.toggled.connect(
                self.toggle_kinematics_controls)

        # Botones de control de estado
        if hasattr(self, 'start_button'):
            self.start_button.clicked.connect(self.start)
        if hasattr(self, 'pause_button'):
            self.pause_button.clicked.connect(self.pause)
        if hasattr(self, 'stop_button'):
            self.stop_button.clicked.connect(self.stop)
        if hasattr(self, 'reset_button'):
            self.reset_button.clicked.connect(self.reset)

        # Activación o desactivación de la simulación
        if hasattr(self, 'simulation_action'):
            self.simulation_action.triggered.connect(
                self.toggle_activation_simulation_event)

        # Botón de cambio de tema
        if hasattr(self, 'theme_action'):
            self.theme_action.triggered.connect(self.toggle_theme_event)

        # Botón para conectar el robot
        if hasattr(self, 'connect_action'):
            self.connect_action.triggered.connect(self.connect_robot)

        self.get_cameras()

    def closeEvent(self, event):
        """ Gestiona el evento de cerrado presentando una ventana para verificar la salida """

        msg = QMessageBox(self)
        msg.setWindowTitle("Salir")
        msg.setText("¿Seguro que quieres cerrar la aplicación?")
        msg.setIcon(QMessageBox.Icon.Question)

        # 🔥 Hace que el mensaje quede por encima de todo
        msg.setWindowFlags(
            msg.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
        )

        si_btn = msg.addButton("Sí", QMessageBox.ButtonRole.YesRole)
        no_btn = msg.addButton("No", QMessageBox.ButtonRole.NoRole)
        msg.setDefaultButton(no_btn)

        msg.exec()

        if msg.clickedButton() == si_btn:
            if hasattr(self, "calibration_window"):
                if hasattr(self.calibration_window, "calibration_interface"):
                    self.calibration_window.calibration_interface.stop_video()
                self.calibration_window.close()
            if hasattr(self, "camera_interface"):
                self.camera_interface.stop_video()
            event.accept()
        else:
            event.ignore()


class DEV_BROADCAST_HDR(ctypes.Structure):
    _fields_ = [
        ("dbch_size", wintypes.DWORD),
        ("dbch_devicetype", wintypes.DWORD),
        ("dbch_reserved", wintypes.DWORD),
    ]


class DeviceEventFilter(QAbstractNativeEventFilter):

    def __init__(self, serial_callback, camera_callback):
        super().__init__()
        self.serial_callback = serial_callback
        self.camera_callback = camera_callback

    def nativeEventFilter(self, eventType, message):
        msg = wintypes.MSG.from_address(message.__int__())

        if msg.message == win32con.WM_DEVICECHANGE:
            # print("Evento detectado:", msg.wParam, msg.lParam)

            if msg.wParam in (win32con.DBT_DEVICEARRIVAL,
                              win32con.DBT_DEVICEREMOVECOMPLETE):

                hdr = cast(msg.lParam, POINTER(DEV_BROADCAST_HDR)).contents

                if hdr.dbch_devicetype == win32con.DBT_DEVTYP_PORT:
                    # Evento de puerto serial
                    QTimer.singleShot(0, self.serial_callback)

            elif msg.wParam == win32con.DBT_DEVNODES_CHANGED:
                # Posible cámara (u otro dispositivo)
                QTimer.singleShot(0, self.camera_callback)

        return False, 0
