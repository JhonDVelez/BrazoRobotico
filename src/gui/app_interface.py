import os
from ctypes import wintypes
from qframelesswindow import FramelessMainWindow
from PyQt6.QtWidgets import QMessageBox, QVBoxLayout, QWidget, QLabel, QApplication
from PyQt6.QtCore import QAbstractNativeEventFilter, QCoreApplication, QTimer
from gui.main_window.main_init_mixin import MainInitMixin
from gui.main_window.main_actions_mixin import MainActionsMixin
from gui.main_window.main_menu_mixin import MainMenuMixin
from gui.main_window.main_theme_mixin import MainThemeMixin, ThemeManager
from gui.main_window.main_title_bar_mixin import MainTitleBarMixin

WM_DEVICECHANGE = 0x0219
DBT_DEVICEARRIVAL = 0x8000
DBT_DEVICEREMOVECOMPLETE = 0x8004
os.environ["QT_LOGGING_RULES"] = "qt.qpa.window=false"


class MainInterface(FramelessMainWindow, MainInitMixin, MainActionsMixin, MainMenuMixin,
                    MainThemeMixin):
    """ Ventana principal de la interfaz 
    """

    def __init__(self, quick3d, robot_id):
        super().__init__()
        self.preloaded_data = quick3d
        self.robot_id = robot_id
        self.simulation_interface = None
        self.stopped = True
        self.camera_paused = False
        self.hab_simulation = True
        self.dark_theme = True
        self.theme_manager = ThemeManager.get_instance()
        self.com = None
        self.com_connected_label = QLabel('No conectado')
        self.connected_to_robot = False

        # Crear contenedor principal
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Barra de título
        self.create_menu()
        self.title_bar = MainTitleBarMixin(self)
        # necesario para arrastrar/min/max
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

        # Carga tema dependiendo de la configuracion de tema de windows
        self.actual_theme = QApplication.instance().styleHints().colorScheme()
        self.update_theme(self.actual_theme)

        # Conectar señal al cambio de tema
        QApplication.instance().styleHints().colorSchemeChanged.connect(self.update_theme)

        # ahora el central widget real es el contenedor con barra + contenido
        self.setCentralWidget(container)

        self.resize(1280, 720)
        self.center_window()

        self._dev_filter = DeviceEventFilter(self.get_com_ports)
        QCoreApplication.instance().installNativeEventFilter(self._dev_filter)

    def setup_connections(self):
        """ Configura las conexiones de eventos para los botones de la interfaz
        """
        if hasattr(self, 'cameraBox'):
            if hasattr(self, 'camera_action'):
                self.camera_action.triggered.connect(
                    self.toggle_visibility_camera_event)

        if hasattr(self, 'modelBox'):
            if hasattr(self, 'model_action'):
                self.model_action.triggered.connect(
                    self.toggle_visibility_model_event)

        if hasattr(self, 'start_button'):
            self.start_button.clicked.connect(self.start)
        if hasattr(self, 'pause_button'):
            self.pause_button.clicked.connect(self.pause)
        if hasattr(self, 'stop_button'):
            self.stop_button.clicked.connect(self.stop)
        if hasattr(self, 'reset_button'):
            self.reset_button.clicked.connect(self.reset)

        if hasattr(self, 'simulation_action'):
            self.simulation_action.triggered.connect(
                self.toggle_activation_model_event)
        if hasattr(self, 'theme_action'):
            self.theme_action.triggered.connect(self.toggle_theme_event)
        if hasattr(self, 'connect_action'):
            self.connect_action.triggered.connect(self.connect_robot)

    def closeEvent(self, event):
        """ Gestiona el evento de cerrado presentando una ventana para verificar la salida de
            la aplicación
        """
        reply = QMessageBox.question(
            self,
            "Salir",
            "¿Seguro que quieres cerrar la aplicación?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()


class DeviceEventFilter(QAbstractNativeEventFilter):
    """ Clase que permite el uso de los eventos de ventana nativa de windows con barra de titulo 
        personalizada
    """

    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def nativeEventFilter(self, eventType, message):
        """ Sobreescritura del metodo de manejo de eventos de ventana para barra de titulo 
            personalizada
        """
        msg = wintypes.MSG.from_address(message.__int__())
        if msg.message == WM_DEVICECHANGE and msg.wParam in (DBT_DEVICEARRIVAL, DBT_DEVICEREMOVECOMPLETE):
            QTimer.singleShot(0, self.callback)
        return False, 0
