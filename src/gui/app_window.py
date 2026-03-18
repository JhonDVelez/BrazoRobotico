import os
from ctypes import wintypes
from qframelesswindow import FramelessMainWindow
from PyQt6.QtWidgets import QMessageBox, QVBoxLayout, QWidget, QLabel, QApplication
from PyQt6.QtCore import QAbstractNativeEventFilter, QCoreApplication, QTimer, Qt
from .main_window import (MainInitMixin, MainActionsMixin, ThemeManager,
                          MainMenuMixin, MainThemeMixin, MainTitleBarMixin)
from data import config_manager as cfg


WM_DEVICECHANGE = 0x0219
DBT_DEVICEARRIVAL = 0x8000
DBT_DEVICEREMOVECOMPLETE = 0x8004
os.environ["QT_LOGGING_RULES"] = "qt.qpa.window=false"


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

        content = cfg.get("settings.json", "content")
        mapping = {
            "camera": self.cameraBox,
            "model": self.modelBox,
            "graphs": self.graphsBox,
            "controls": self.controlsBox
        }

        for key, widget in mapping.items():
            if key in content:
                # Usamos setVisible para evitar el if/else interno
                widget.setVisible(bool(content[key]))

        color_schemes = QApplication.instance().styleHints().colorScheme()
        theme_map = {
            "light": color_schemes.Light,
            "dark": color_schemes.Dark
        }
        actual_theme = cfg.get("settings.json", "theme").lower()
        scheme = theme_map.get(actual_theme, color_schemes.Dark)
        self.update_theme(scheme)

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
            if hasattr(self, 'camera_calibration_action'):
                self.camera_calibration_action.triggered.connect(
                    self.initiate_camera_calibration)

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
                self.toggle_activation_simulation_event)
        if hasattr(self, 'graphs_action'):
            self.graphs_action.triggered.connect(
                self.toggle_visibility_graphs_event)
        if hasattr(self, 'controls_action'):
            self.controls_action.triggered.connect(
                self.toggle_visibility_controls_event)
        if hasattr(self, 'theme_action'):
            self.theme_action.triggered.connect(self.toggle_theme_event)
        if hasattr(self, 'connect_action'):
            self.connect_action.triggered.connect(self.connect_robot)

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
                self.calibration_window.close()
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
        """ Sobrescritura del método de manejo de eventos de ventana para barra de titulo 
            personalizada
        """
        msg = wintypes.MSG.from_address(message.__int__())
        if msg.message == WM_DEVICECHANGE and msg.wParam in (DBT_DEVICEARRIVAL, DBT_DEVICEREMOVECOMPLETE):
            QTimer.singleShot(0, self.callback)
        return False, 0
