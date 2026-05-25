"""
Modulo que define la interfaz visual para el proceso de calibracion.

Este modulo contiene la clase CalibrationWidget, la cual organiza los elementos
graficos necesarios para visualizar el feed de camara y gestionar las acciones
de captura y calculo de calibracion.
"""

from PyQt6.QtWidgets import QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, QPushButton, QGroupBox
from PyQt6.QtCore import pyqtSignal


class CalibrationWidget(QWidget):
    """
    Widget de interfaz para la calibracion de camaras.

    Organiza la vista de camara y los controles de accion en una disposicion
    de cuadricula, facilitando la interaccion del usuario durante el proceso
    de captura de frames ChArUco.

    Attributes:
        capture_clicked (pyqtSignal): Señal emitida al presionar el boton de captura.
        calibrate_clicked (pyqtSignal): Señal emitida al presionar el boton de calibrar.
    """
    capture_clicked = pyqtSignal()
    calibrate_clicked = pyqtSignal()

    def __init__(self, parent=None):
        """
        Inicializa el widget de calibracion y configura su interfaz.

        Args:
            parent (QWidget, optional): Widget padre.
        """
        super().__init__(parent)
        self.__setup_ui()

    def __setup_ui(self):
        """
        Configura la disposicion de los componentes visuales (Layouts).
        """
        self.main_layout = QGridLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.setSpacing(10)

        # (0, 0) - Contenedor para el widget de la camara
        self.camera_container = QGroupBox()
        self.camera_container.setTitle("Vista de Calibración")
        self.camera_layout = QVBoxLayout(self.camera_container)
        self.camera_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.camera_container, 0, 0)

        # (1, 0) - Panel de botones de accion
        self.buttons_widget = QWidget()
        self.buttons_layout = QHBoxLayout(self.buttons_widget)

        self.capture_button = QPushButton("Capturar Imagen")
        self.capture_button.setMinimumHeight(40)
        self.capture_button.clicked.connect(self.capture_clicked)

        self.calibrate_button = QPushButton("Calibrar Cámara")
        self.calibrate_button.setMinimumHeight(40)
        self.calibrate_button.clicked.connect(self.calibrate_clicked)

        self.buttons_layout.addWidget(self.capture_button)
        self.buttons_layout.addWidget(self.calibrate_button)

        self.main_layout.addWidget(self.buttons_widget, 1, 0)

    def get_camera_layout(self):
        """
        Retorna el layout destinado a contener el widget de feed de camara.

        Returns:
            QVBoxLayout: Layout del contenedor de camara.
        """
        return self.camera_layout

    def set_capture_button_enabled(self, state: bool):
        """
        Habilita o deshabilita el boton de captura de frames.

        Args:
            state (bool): True para habilitar, False para deshabilitar.
        """
        self.capture_button.setEnabled(state)

    def set_calibrate_button_enabled(self, state: bool):
        """
        Habilita o deshabilita el boton de ejecucion de calibracion.

        Args:
            state (bool): True para habilitar, False para deshabilitar.
        """
        self.calibrate_button.setEnabled(state)
