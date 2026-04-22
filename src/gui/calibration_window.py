from PyQt6.QtWidgets import (
    QVBoxLayout, QGridLayout, QPushButton, QApplication, QWidget, QHBoxLayout, QSizePolicy)
from PyQt6.QtCore import QSize, QCoreApplication
from qframelesswindow import FramelessMainWindow
from .main_window import MainTitleBarMixin, CalibrationMenuMixin
from .calibration_interface import CalibrationInterface
from .device_monitor import get_device_monitor


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
        self.clear_camera_selection()

        # Instalar monitor de dispositivos multiplataforma (solo para cámaras)
        self._device_monitor = get_device_monitor(
            camera_callback=self.get_cameras, camera_only=True)
        self._device_monitor.install_filter(QCoreApplication.instance())
        self.get_cameras()

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

        self.calibration_interface = CalibrationInterface(self)
        self.gridLayout.addWidget(self.calibration_interface, 0, 0)

        self.buttons_widget = QWidget()
        self.buttons_layout = QHBoxLayout(self.buttons_widget)
        self.capture_button = QPushButton("Capturar Imagen")
        self.buttons_layout.addWidget(self.capture_button)
        self.calibrate_button = QPushButton("Calibrar Cámara")
        self.buttons_layout.addWidget(self.calibrate_button)
        self.gridLayout.addWidget(self.buttons_widget)

    def setup_connections(self):
        if hasattr(self, 'capture_button'):
            self.capture_button.clicked.connect(self.capture_pixmap)
        if hasattr(self, 'calibrate_button'):
            self.calibrate_button.clicked.connect(self.calibrate)

    def capture_pixmap(self):
        self.calibration_interface.save_pixmap = True

    def calibrate(self):
        self.calibration_interface.read_temporal_pixmap()

    def closeEvent(self, event):
        if hasattr(self, "calibration_interface"):
            self.calibration_interface.stop_video()
        self.clear_camera_selection()
        if hasattr(self, "_device_monitor"):
            self._device_monitor.uninstall_filter()
        event.accept()
