from PyQt6.QtWidgets import QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, QPushButton, QGroupBox
from PyQt6.QtCore import Qt, QSize, pyqtSignal

class CalibrationWidget(QWidget):
    """
    Widget encargado de la interfaz visual de calibración.
    Organiza la cuadrícula 2x2 y gestiona los botones de acción.
    """
    capture_clicked = pyqtSignal()
    calibrate_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.__setup_ui()

    def __setup_ui(self):
        """
        Configura el layout de la cuadrícula 2x2.
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

        # (1, 0) - Panel de botones
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

        # Espacios para futuros componentes en (0, 1) y (1, 1) si se requieren, 
        # manteniendo la estructura de cuadrícula.

    def get_camera_layout(self):
        """ Retorna el layout donde se insertará el widget de cámara """
        return self.camera_layout

    def set_capture_button_enabled(self, state: bool):
        """ Habilita/Deshabilita el botón de captura """
        self.capture_button.setEnabled(state)

    def set_calibrate_button_enabled(self, state: bool):
        """ Habilita/Deshabilita el botón de calibración """
        self.calibrate_button.setEnabled(state)
