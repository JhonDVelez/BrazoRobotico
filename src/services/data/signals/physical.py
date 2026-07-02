"""
Módulo que define el gestor de señales para el dominio físico.

Proporciona el singleton PhysicalSignalManager con señales para
la comunicación con el hardware robótico real.
"""

from PyQt6.QtCore import pyqtSignal
from .base import _SignalManager


class PhysicalSignalManager(_SignalManager):
    """
    Gestor de señales específico para el robot físico.

    Hereda las señales base y añade señales para el envío de comandos
    y recepción de telemetría desde el microcontrolador.

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
        Obtiene la instancia única del gestor (patrón Singleton).

        Returns:
            PhysicalSignalManager: Instancia única.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance