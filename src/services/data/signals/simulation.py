"""
Modulo que define el gestor de senales para el dominio de simulacion.

Proporciona el singleton SimulationSignalManager con senales para
la actualizacion de posiciones de esferas en la escena 3D.
"""

from PyQt6.QtCore import pyqtSignal
from .base import _SignalManager


class SimulationSignalManager(_SignalManager):
    """
    Gestor de senales especifico para el dominio de simulacion.

    Hereda las senales base y anade la senal ``sphere_pos`` para
    actualizar las posiciones 3D de las esferas detectadas.

    Signals:
        sphere_pos: Emite un diccionario {color: [x, y, z]}.
    """
    _instance = None
    sphere_pos_from_camera = pyqtSignal(dict)
    sphere_pos_from_pybullet = pyqtSignal(dict)
    clear_spheres = pyqtSignal()
    release_sphere = pyqtSignal(str)
    reattach_sphere = pyqtSignal(str)
    sphere_radius_changed = pyqtSignal(float)

    @classmethod
    def get_instance(cls):
        """
        Obtiene la instancia unica del gestor (patron Singleton).

        Returns:
            SimulationSignalManager: Instancia unica.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
