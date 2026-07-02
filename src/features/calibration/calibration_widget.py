"""
Módulo que define la interfaz visual para el proceso de calibración.

Este módulo contiene la clase CalibrationWidget, la cual organiza los elementos
gráficos necesarios para visualizar el feed de cámara y gestionar las acciones
de captura y cálculo de calibración.
"""

from PyQt6.QtWidgets import QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, QPushButton, QGroupBox
from PyQt6.QtCore import pyqtSignal


class CalibrationWidget(QWidget):
    """
    Widget de interfaz para la calibración de cámaras.

    Organiza la vista de cámara y los controles de acción en una disposición
    de cuadricula, facilitando la interacción del usuario durante el proceso
    de captura de frames ChArUco.

    Attributes:
        capture_clicked (pyqtSignal): Señal emitida al presionar el botón de captura.
        calibrate_clicked (pyqtSignal): Señal emitida al presionar el botón de calibrar.
    """
    capture_clicked = pyqtSignal()
    calibrate_clicked = pyqtSignal()

    def __init__(self, parent=None) -> None:
        """
        Inicializa el widget de calibración y configura su interfaz.

        Args:
            parent (QWidget, optional): Widget padre.
        """
        super().__init__(parent)
        self.__setup_ui()

    def __setup_ui(self):
        """
        Configura la disposición de los componentes visuales (Layouts).
        """
        self.main_layout = QGridLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.setSpacing(10)

        # (0, 0) - Contenedor para el widget de la cámara
        self.camera_container = QGroupBox()
        self.camera_container.setTitle("Vista de Calibración")
        self.camera_layout = QVBoxLayout(self.camera_container)
        self.camera_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.camera_container, 0, 0)

        # (1, 0) - Panel de botones de acción
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

    def get_camera_layout(self) -> QVBoxLayout:
        """
        Retorna el layout destinado a contener el widget de feed de cámara.

        Returns:
            QVBoxLayout: Layout del contenedor de cámara.
        """
        return self.camera_layout

    def set_capture_button_enabled(self, state: bool) -> None:
        """
        Habilita o deshabilita el botón de captura de frames.

        Args:
            state (bool): True para habilitar, False para deshabilitar.
        """
        self.capture_button.setEnabled(state)

    def set_calibrate_button_enabled(self, state: bool) -> None:
        """
        Habilita o deshabilita el botón de ejecución de calibración.

        Args:
            state (bool): True para habilitar, False para deshabilitar.
        """
        self.calibrate_button.setEnabled(state)
