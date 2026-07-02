"""
Paquete de la feature de cámara para captura y visualización de video.

Proporciona los componentes Worker-Widget-Controller para gestionar
el feed de video, la selección de dispositivos y la transmisión de
frames hacia otros módulos (calibración, detección, etc).
"""
from .camera_controller import CameraController

__all__ = [
    "CameraController"
]
