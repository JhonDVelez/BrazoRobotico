"""
Módulo que define el gestor de señales para el dominio de simulación.

Proporciona el singleton SimulationSignalManager con señales para
la actualización de posiciones de esferas en la escena 3D.
"""

from PyQt6.QtCore import pyqtSignal
from .base import _SignalManager


class SimulationSignalManager(_SignalManager):
    """
    Gestor de señales específico para el dominio de simulación.

    Hereda las señales base y añade la señal ``sphere_pos`` para
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
    start_simulation = pyqtSignal()
    pause_simulation = pyqtSignal(bool)
    stop_simulation = pyqtSignal()
    
    start_request = pyqtSignal()
    pause_request = pyqtSignal(bool)
    stop_request = pyqtSignal()

    @classmethod
    def get_instance(cls):
        """
        Obtiene la instancia única del gestor (patrón Singleton).

        Returns:
            SimulationSignalManager: Instancia única.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
