from PyQt6.QtWidgets import QComboBox, QSizePolicy
from src.services.devices import CameraDevices


class CameraSelectorWidget(QComboBox):
    def __init__(self):
        super().__init__()
        self.setObjectName("camera_selector")
        self.setPlaceholderText("Seleccionar cámara")
        self.setFixedHeight(30)
        self.setMinimumWidth(220)
        self.setMaximumWidth(360)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setVisible(False)
        self.camera_devices = CameraDevices()

    def get_cameras(self):
        cameras = self.camera_devices.get_cameras()
        self.clear()
        for camera_index, display_name in cameras:
            self.addItem(display_name, [camera_index, display_name])
