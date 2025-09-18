from qframelesswindow import FramelessMainWindow
from PyQt6.QtWidgets import (
    QMessageBox, QVBoxLayout, QWidget, QApplication
)
from PyQt6.QtGui import QScreen
from gui.main_window.main_init import MainInit
from gui.main_window.main_actions import MainActions
from gui.main_window.main_menu import MainMenu
from gui.main_window.main_theme import MainTheme, ThemeManager
from gui.main_window.main_title_bar import MainTitleBar


class MainInterface(FramelessMainWindow, MainInit, MainActions, MainMenu, MainTheme):
    """ Ventana principal de la interfaz """

    def __init__(self):
        super().__init__()
        self.simulation_interface = None
        self.stopped = True
        self.camera_paused = False
        self.hab_simulation = True
        self.dark_theme = True
        self.theme_manager = ThemeManager.get_instance()

        # Crear contenedor principal
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ---- Barra de título
        self.create_menu()
        self.title_bar = MainTitleBar(self)
        # necesario para arrastrar/min/max
        self.setTitleBar(self.title_bar)
        layout.addWidget(self.title_bar)

        # ---- Contenido
        self.centralwidget = QWidget()
        self.setup_ui(self.centralwidget)
        layout.addWidget(self.centralwidget)

        self.create_status_bar()
        self.init_camera()
        self.init_controls()
        self.init_simulation()
        self.setup_connections()
        self.load_dark_theme()

        # ahora el central widget real es el contenedor con barra + contenido
        self.setCentralWidget(container)

        self.resize(1280, 720)
        self.center_window()

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

    def closeEvent(self, event):
        """ Gestiona el evento de cerrado presentando una ventana para verificar la salida de
            la aplicacion
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
