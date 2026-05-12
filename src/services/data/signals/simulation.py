from PyQt6.QtCore import pyqtSignal
from .base import _SignalManager


class SimulationSignalManager(_SignalManager):
    """ SignalManager específico para simulación
    """
    _instance = None
    sphere_pos = pyqtSignal(dict)

    @classmethod
    def get_instance(cls):
        """ Permite obtener una única instancia del objeto evitando que se generen multiples señales
            de comunicación. En caso de que no haya ninguna instancia entonces se crea una nueva.

        Returns:
            SimulationSignalManager: instancia única de la clase
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
