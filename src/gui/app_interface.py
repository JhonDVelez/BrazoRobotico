from PyQt6.QtWidgets import QMainWindow, QMessageBox
from gui.main_window.main_init import MainInit
from gui.main_window.main_actions import MainActions
from gui.main_window.main_menu import MainMenu


class MainInterface(QMainWindow, MainInit, MainActions, MainMenu):
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
        self.init_main_window()
        self.init_camera()
        self.init_controls()
        self.init_openbotv()
        self.init_simulation()
        self.create_actions()
        self.create_menu()
        self.setup_connections()

    def setup_connections(self):
        """ Configura las conexiones de eventos para los botones de la interfaz
        """
        if hasattr(self.ui, 'cameraBox'):
            self.camera_action.triggered.connect(
                self.toggle_visibility_camera_event)
        if hasattr(self.ui, 'modelBox'):
            self.model_action.triggered.connect(
                self.toggle_visibility_model_event)
        if hasattr(self.ui, 'start_button'):
            self.start_button.clicked.connect(self.start)
        if hasattr(self.ui, 'pause_button'):
            self.pause_button.clicked.connect(self.pause)
        if hasattr(self.ui, 'stop_button'):
            self.stop_button.clicked.connect(self.stop)
        if hasattr(self.ui, 'reset_button'):
            self.reset_button.clicked.connect(self.reset)
        self.simulation_action.triggered.connect(
            self.toggle_activation_model_event)

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
