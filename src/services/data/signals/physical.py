"""
Modulo que define el gestor de senales para el dominio fisico.

Proporciona el singleton PhysicalSignalManager con senales para
la comunicacion con el hardware robotico real.
"""

from PyQt6.QtCore import pyqtSignal
from .base import _SignalManager


class PhysicalSignalManager(_SignalManager):
    """
    Gestor de senales especifico para el robot fisico.

    Hereda las senales base y anade senales para el envio de comandos
    y recepcion de telemetria desde el microcontrolador.

    Signals:
        send_to_robot: Emite una lista de posiciones de servos.
        data_received: Emite (posiciones, temperaturas) desde el hardware.
    """
    is_connected = False
    send_to_robot = pyqtSignal(list)
    data_received = pyqtSignal(list, list)
    start_service = pyqtSignal()
    stop_service = pyqtSignal()
    
    start_request = pyqtSignal()
    stop_request = pyqtSignal()

    _instance = None

    @classmethod
    def get_instance(cls):
        """
        Obtiene la instancia unica del gestor (patron Singleton).

        Returns:
            PhysicalSignalManager: Instancia unica.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance