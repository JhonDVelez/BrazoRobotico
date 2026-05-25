"""
Paquete de la feature de camara para captura y visualizacion de video.

Proporciona los componentes Worker-Widget-Controller para gestionar
el feed de video, la seleccion de dispositivos y la transmision de
frames hacia otros modulos (calibracion, deteccion, etc).
"""
from .camera_controller import CameraController

__all__ = [
    "CameraController"
]
