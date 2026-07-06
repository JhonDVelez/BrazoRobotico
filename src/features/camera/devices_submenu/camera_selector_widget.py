"""
Módulo que define el selector de dispositivos de cámara.

Este modulo contiene la clase CameraSelectorWidget, un componente especializado
para listar y seleccionar las cámaras conectadas al sistema.
"""

from PyQt6.QtWidgets import QComboBox, QSizePolicy
from src.services.devices import CameraDevices


class CameraSelectorWidget(QComboBox):
    """
    Widget de selección de cámara basado en QComboBox.

    Permite al usuario elegir entre las diferentes cámaras detectadas por el
    sistema, integrando la lógica de descubrimiento de hardware.
    """

    def __init__(self) -> None:
        """
        Inicializa el selector de cámara con estilos y configuraciones base.
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

    def get_cameras(self) -> None:
        """
        Consulta las cámaras disponibles y actualiza el contenido del selector.
        """
        self.camera_devices.get_cameras()
