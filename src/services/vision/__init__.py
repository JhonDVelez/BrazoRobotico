"""
Paquete de servicios de vision artificial y deteccion.

Proporciona herramientas para control de camara, deteccion de
tableros ChArUco, deteccion de esferas de color por segmentacion
HSV, dibujo de resultados sobre el frame y estimacion de pose 3D.
"""

from src.services.vision.camera_control import CameraControl
from src.services.vision.charuco_detection import ChArUcoDetection
from src.services.vision.pose_estimation import PoseEstimation
from src.services.vision.circle_detection import CircleDetection
from src.services.vision.detection_drawer import DetectionDrawer

__all__ = [
    "CameraControl",
    "ChArUcoDetection",
    "PoseEstimation",
    "CircleDetection",
    "DetectionDrawer"
]
