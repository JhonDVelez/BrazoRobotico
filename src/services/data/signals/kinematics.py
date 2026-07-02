"""
Módulo que define el gestor de señales para el dominio de cinemática.

Proporciona el singleton KinematicsSignalManager, el bus de intención saliente
del control cartesiano. El KinematicsController publica aquí sus peticiones de
cambio de modo y de objetivo; el DataController las escucha y orquesta el resto
del sistema. De este modo la feature de cinemática deja de conocer el bus de
simulación.
"""

from PyQt6.QtCore import pyqtSignal
from .base import _SignalManager


class KinematicsSignalManager(_SignalManager):
    """
    Gestor de señales específico para el control cinemático (cartesiano).

    Hereda las señales base. El KinematicsController emite ``change_mode_signal``
    y ``update_target_signal``, y participa en el diálogo de cinemática inversa
    mediado por el DataController.

    Signals (heredadas de _SignalManager):
        change_mode_signal: Sender KinematicsController, receiver DataController.
            Solicita conmutar el modo global a ``Modes.KINEMATIC``.
        update_target_signal: Sender KinematicsController, receiver DataController.
            Publica el nuevo vector de posiciones articulares calculadas.

    Signals (propias):
        inverse_kinematics_requested: Sender DataController, receiver
            KinematicsController. Solicita el cálculo de IK para una acción.
        inverse_kinematics_ready: Sender KinematicsController, receiver
            DataController. Publica el resultado de IK calculado.
    """
    _instance = None
    inverse_kinematics_requested = pyqtSignal(dict)
    inverse_kinematics_ready = pyqtSignal(dict)

    @classmethod
    def get_instance(cls):
        """
        Obtiene la instancia única del gestor (patrón Singleton).

        Returns:
            KinematicsSignalManager: Instancia única.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
