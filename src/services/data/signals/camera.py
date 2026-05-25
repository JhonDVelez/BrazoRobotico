"""
Modulo que define el gestor de senales de la camara.

Proporciona el singleton CameraSignalManager con senales para
notificar la disponibilidad de camaras y los resultados de las
detecciones de vision.
"""

from PyQt6.QtCore import pyqtSignal, QObject


class CameraSignalManager(QObject):
    """
    Gestor de senales para el modulo de camara.

    Signals:
        available_cameras: Emite una lista de (indice, nombre).
        charuco_done: Emite (frame_id, datos) con resultados ChArUco.
        circles_done: Emite (frame_id, datos) con resultados de esferas.
        fusion_done: Emite (frame_id, datos) con datos fusionados.
    """
    available_cameras = pyqtSignal(list)
    charuco_done = pyqtSignal(int, object)
    circles_done = pyqtSignal(int, object)
    fusion_done = pyqtSignal(int, object)

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
