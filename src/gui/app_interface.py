import os
from PyQt6.QtWidgets import QMainWindow, QMessageBox
from PyQt6.QtCore import QEvent
from PyQt6 import uic
from gui.main_window.main_init import MainInit
from gui.main_window.main_actions import MainActions
from gui.main_window.main_menu import MainMenu
from gui.main_window.main_theme import MainTheme
from gui.main_window.main_title_bar import MainTitleBar


class MainInterface(QMainWindow, MainInit, MainActions, MainMenu, MainTheme, MainTitleBar):
    """ Ventana principal de la interfaz

    Args:
        QMainWindow (QtWidget): Integracion como ventana principal de la aplicacion
    """

    def __init__(self):
        super().__init__()
        self.simulation_interface = None
        self.stopped = True
        self.camera_paused = False
        self.hab_simulation = True
        self.dark_theme = True

        ui_path = os.path.join(os.path.dirname(__file__), "app_interface.ui")
        self.ui = uic.loadUi(ui_path, self)

        self.contentSplitter.setSizes([500, 500, 200])
        self.visualSplitter.setSizes([100, 100])

        self.init_camera()
        self.init_controls()
        self.init_simulation()
        self.create_actions()
        self.create_menu()
        self.setup_custom_titlebar()
        self.setup_connections()
        self.load_dark_theme()

    def setup_connections(self):
        """ Configura las conexiones de eventos para los botones de la interfaz
        """
        # Mantener exactamente igual - self.ui sigue funcionando
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

    def changeEvent(self, event):
        """Detectar cambios de estado de la ventana"""
        if event.type() == QEvent.Type.WindowStateChange and hasattr(self, 'custom_title_bar'):
            self.custom_title_bar.window_state_changed(self.windowState())
        super().changeEvent(event)
