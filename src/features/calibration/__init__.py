""" Paquete encargado de la calibración de la cámara web. 
    Implementa la detección de tableros ChArUco y el cálculo de parámetros intrínsecos.
"""

from .calibration_window import CameraCalibrationWindow
from .calibration_controller import CalibrationController

__all__ = [
    "CameraCalibrationWindow",
    "CalibrationController"
]
