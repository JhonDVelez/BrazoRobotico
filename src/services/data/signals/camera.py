"""
Modulo que define el gestor de senales de la camara.

Proporciona el singleton CameraSignalManager con senales para
notificar la disponibilidad de camaras, los resultados de las
detecciones de vision y los datos de esferas detectadas.
"""

from PyQt6.QtCore import pyqtSignal, QObject


class CameraSignalManager(QObject):
    """
    Gestor de senales para el modulo de camara.

    Signals:
        available_cameras: Emite una lista de (indice, nombre).
        charuco_done: Emite (frame_id, datos) con resultados ChArUco.
        circles_done: Emite (frame_id, datos) con resultados de esferas.
        pose_done: Emite (frame_id, datos) con datos de pose.
        spheres_detected_2d: Sender CameraController, receiver DataController.
            Emite un diccionario con las detecciones 2D de esferas; el
            DataController lo re-publica al bus de pick and place.
        poses_from_camera: Sender CameraController, receiver DataController.
            Emite un diccionario {color: {'position': [x, y, z]}}; el
            DataController lo puentea hacia simulacion y pick and place.
        clear_spheres_request: Sender CameraController, receiver DataController.
            Solicita limpiar las esferas al detenerse el video.
    """
    available_cameras = pyqtSignal(list)
    charuco_done = pyqtSignal(int, object)
    circles_done = pyqtSignal(int, object)
    pose_done = pyqtSignal(int, object)
    spheres_detected_2d = pyqtSignal(dict)
    poses_from_camera = pyqtSignal(dict)
    clear_spheres_request = pyqtSignal()

    _instance = None

    @classmethod
    def get_instance(cls):
        """
        Obtiene la instancia unica del gestor (patron Singleton).

        Returns:
            CameraSignalManager: Instancia unica.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
