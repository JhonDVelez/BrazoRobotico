from PyQt6.QtCore import pyqtSignal, QObject


class CameraSignalManager(QObject):
    """ Manejo de las señales para el control del flujo de frames de la cámara
    """
    charuco_done = pyqtSignal(int, object)   # (frame_id, data)
    ellipses_done = pyqtSignal(int, object)  # (frame_id, data)
    fusion_done = pyqtSignal(int, object)    # (frame_id, data)

    _instance = None

    @classmethod
    def get_instance(cls):
        """ Permite obtener una única instancia del objeto evitando que se generen multiples señales
            de comunicación. En caso de que no haya ninguna instancia entonces se crea una nueva.

        Returns:
            CameraSignalManager: instancia única de la clase
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance