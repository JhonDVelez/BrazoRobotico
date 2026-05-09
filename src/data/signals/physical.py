from PyQt6.QtCore import pyqtSignal
from data.signals.base import _SignalManager


class PhysicalSignalManager(_SignalManager):
    """ SignalManager específico para robot físico
    """
    is_connected = False
    send_to_robot = pyqtSignal(list)
    data_received = pyqtSignal(list, list)

    _instance = None

    @classmethod
    def get_instance(cls):
        """ Permite obtener una única instancia del objeto evitando que se generen multiples señales
            de comunicación. En caso de que no haya ninguna instancia entonces se crea una nueva.

        Returns:
            PhysicalSignalManager: instancia única de la clase
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance