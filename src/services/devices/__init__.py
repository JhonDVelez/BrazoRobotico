"""
Paquete de servicios de deteccion y monitoreo de dispositivos.

Proporciona las clases CameraDevices (enumeration de camaras) y
DeviceMonitor (monitoreo de cambios de hardware).
"""

from .camera_device import CameraDevices
from .device_monitor import DeviceMonitor

__all__ = [
    "CameraDevices",
    "DeviceMonitor"
]
