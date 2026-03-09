from PyQt6.QtWidgets import QVBoxLayout, QGridLayout, QSplitter, QGroupBox, QPushButton, QApplication
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QSizePolicy
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget
from qframelesswindow import FramelessMainWindow
from .main_window import MainTitleBarMixin, CalibrationMenuMixin
from .camera_interface import CameraInterface


class CameraCalibrationWindow(FramelessMainWindow, CalibrationMenuMixin):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Calibración De Cámara")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Barra de título
        self.create_calibration_menu()
        self.create_status_bar()
        self.title_bar = MainTitleBarMixin(self, "Calibración De La Cámara")
        # necesario para acciones de ventana como arrastrar/min/max
        self.setTitleBar(self.title_bar)
        layout.addWidget(self.title_bar)

        self.central_widget = QWidget()
        self.setup_ui(self.central_widget)

        layout.addWidget(self.central_widget)

        self.setCentralWidget(container)

        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        self.resize(int(screen_geometry.width()*0.66),
                    int(screen_geometry.height()*0.66))
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)

        self.setup_connections()

    def setup_ui(self, main_widget):

        self.main_widget = main_widget
        self.main_widget.setObjectName("MainWidget")
        self.main_widget.setMinimumSize(QSize(400, 400))
        self.main_widget.resize(QSize(1280, 720))

        sizePolicy = QSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Preferred
        )
        sizePolicy.setHorizontalStretch(3)
        sizePolicy.setVerticalStretch(3)
        self.main_widget.setSizePolicy(sizePolicy)

        # ========== LAYOUT PRINCIPAL ==========
        self.gridLayout = QGridLayout(self.main_widget)
        self.gridLayout.setObjectName("gridLayout")
        # Añadir margen superior para evitar superposición con title bar
        self.gridLayout.setContentsMargins(5, 5, 5, 5)

        self.camera_interface = CameraInterface(self)
        self.gridLayout.addWidget(self.camera_interface, 0, 0)

        self.calibrate_button = QPushButton("Calibrar Cámara")
        self.gridLayout.addWidget(self.calibrate_button, 1, 0)

    def setup_connections(self):
        if hasattr(self, 'calibrate_button'):
            self.calibrate_button.clicked.connect(self.calibrate)

    def calibrate(self):
        pass
