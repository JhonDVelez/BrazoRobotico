# from pyqt_frameless_window import FramelessMainWindow
from qframelesswindow import FramelessMainWindow
from PyQt6.QtWidgets import QMessageBox, QVBoxLayout, QHBoxLayout, QWidget, QSizePolicy, QMainWindow, QApplication
from PyQt6.QtGui import QScreen
from gui.main_window.main_init import MainInit
from gui.main_window.main_actions import MainActions
from gui.main_window.main_menu import MainMenu
from gui.main_window.main_theme import MainTheme
from gui.main_window.main_title_bar import MainTitleBar


class MainInterface(FramelessMainWindow, MainInit, MainActions, MainMenu, MainTheme):
    """ Ventana principal de la interfaz

    Args:
        FramelessMainWindow: Ventana sin marco personalizada
    """

    def __init__(self):
        super().__init__()
        self.simulation_interface = None
        self.stopped = True
        self.camera_paused = False
        self.hab_simulation = True
        self.dark_theme = True

        # IMPORTANTE: Configurar la title bar ANTES de setup_ui
        self.custom_title_bar = MainTitleBar(self)
        self.custom_title_bar.setSizePolicy(QSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred))
        self.setTitleBar(self.custom_title_bar)

        # Crear un widget contenedor principal que respete la title bar
        self.main_container = QWidget()
        self.main_layout = QVBoxLayout(self.main_container)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.create_menu()

        self.title_container = QWidget()
        self.title_layout = QHBoxLayout(self.title_container)
        self.title_layout.setContentsMargins(0, 0, 0, 0)
        self.title_layout.setSpacing(0)

        self.title_layout.addWidget(self.menubar)
        self.title_layout.addWidget(self.titleBar)
        self.main_layout.addWidget(self.title_container)

        self.setup_ui_in_container()
        self.init_camera()
        self.init_controls()
        self.init_simulation()
        self.setup_connections()
        self.load_dark_theme()

        self.contentSplitter.setSizes([500, 500, 200])
        self.visualSplitter.setSizes([100, 100])
        self.setCentralWidget(self.main_container)
        # self.titleBar.raise_()
        self.resize(1280, 720)
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()

        # Calculate the center position
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2

        # Move the window to the calculated position
        self.move(x, y)

    def setup_ui_in_container(self):
        """Configura la UI dentro del contenedor principal"""
        # Crear el widget que contendrá toda la interfaz original
        self.centralwidget = QWidget()

        # Llamar al setup_ui original pero pasando el widget contenedor
        self.setup_ui(self.centralwidget)

        # Añadir el centralwidget al layout principal
        self.main_layout.addWidget(self.centralwidget)

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
        if hasattr(self, 'theme_menu'):
            self.theme_menu.pressed.connect(self.toggle_theme_event)

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
