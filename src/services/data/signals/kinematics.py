"""
Modulo que define el gestor de senales para el dominio de cinematica.

Proporciona el singleton KinematicsSignalManager, el bus de intencion saliente
del control cartesiano. El KinematicsController publica aqui sus peticiones de
cambio de modo y de objetivo; el DataController las escucha y orquesta el resto
del sistema. De este modo la feature de cinematica deja de conocer el bus de
simulacion.
"""

from PyQt6.QtCore import pyqtSignal
from .base import _SignalManager


class KinematicsSignalManager(_SignalManager):
    """
    Gestor de senales especifico para el control cinematico (cartesiano).

    Hereda las senales base. El KinematicsController emite ``change_mode_signal``
    y ``update_target_signal``, y participa en el dialogo de cinematica inversa
    mediado por el DataController.

    Signals (heredadas de _SignalManager):
        change_mode_signal: Sender KinematicsController, receiver DataController.
            Solicita conmutar el modo global a ``Modes.KINEMATIC``.
        update_target_signal: Sender KinematicsController, receiver DataController.
            Publica el nuevo vector de posiciones articulares calculadas.

    Signals (propias):
        inverse_kinematics_requested: Sender DataController, receiver
            KinematicsController. Solicita el calculo de IK para una accion.
        inverse_kinematics_ready: Sender KinematicsController, receiver
            DataController. Publica el resultado de IK calculado.
    """
    _instance = None
    inverse_kinematics_requested = pyqtSignal(dict)
    inverse_kinematics_ready = pyqtSignal(dict)

    @classmethod
    def get_instance(cls):
        """
        Obtiene la instancia unica del gestor (patron Singleton).

        Returns:
            KinematicsSignalManager: Instancia unica.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
