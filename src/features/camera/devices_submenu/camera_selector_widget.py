"""
Modulo que define el selector de dispositivos de camara.

Este modulo contiene la clase CameraSelectorWidget, un componente especializado
para listar y seleccionar las camaras conectadas al sistema.
"""

from PyQt6.QtWidgets import QComboBox, QSizePolicy
from src.services.devices import CameraDevices


class CameraSelectorWidget(QComboBox):
    """
    Widget de seleccion de camara basado en QComboBox.

    Permite al usuario elegir entre las diferentes camaras detectadas por el
    sistema, integrando la logica de descubrimiento de hardware.
    """

    def __init__(self):
        """
        Inicializa el selector de camara con estilos y configuraciones base.
        """
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
        """
        Consulta las camaras disponibles y actualiza el contenido del selector.
        """
        cameras = self.camera_devices.get_cameras()
        self.clear()
        for camera_index, display_name in cameras:
            self.addItem(display_name, [camera_index, display_name])
