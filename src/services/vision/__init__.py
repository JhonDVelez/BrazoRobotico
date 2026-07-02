"""
Paquete de servicios de visión artificial y detección.

Proporciona herramientas para control de cámara, detección de
tableros ChArUco, detección de esferas de color por segmentación
HSV, dibujo de resultados sobre el frame y estimación de pose 3D.
"""

from src.services.vision.camera_connection import CameraConnection
from src.services.vision.charuco_detection import ChArUcoDetection
from src.services.vision.pose_estimation import PoseEstimation
from src.services.vision.circle_detection import CircleDetection
from src.services.vision.detection_drawer import DetectionDrawer

__all__ = [
    "CameraConnection",
    "ChArUcoDetection",
    "PoseEstimation",
    "CircleDetection",
    "DetectionDrawer"
]
