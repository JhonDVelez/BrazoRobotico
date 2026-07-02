"""
Paquete de la feature de calibración del brazo robótico.

Proporciona las herramientas de calibración de articulaciones y sensores,
incluyendo la interfaz de usuario (widget/ventana), la lógica de control
y el worker de procesamiento asociado.
"""

from .calibration_window import CameraCalibrationWindow
from .calibration_controller import CalibrationController

__all__ = [
    "CameraCalibrationWindow",
    "CalibrationController"
]
