"""
Paquete de la feature de calibracion del brazo robotico.

Proporciona las herramientas de calibracion de articulaciones y sensores,
incluyendo la interfaz de usuario (widget/ventana), la logica de control
y el worker de procesamiento asociado.
"""

from .calibration_window import CameraCalibrationWindow
from .calibration_controller import CalibrationController

__all__ = [
    "CameraCalibrationWindow",
    "CalibrationController"
]
