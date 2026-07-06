"""
Módulo que define el gestor de señales para el dominio de sliders.

Proporciona el singleton SlidersSignalManager, el bus de intención saliente
del control manual por sliders. El SlidersController publica aquí sus
peticiones de cambio de modo y de objetivo; el DataController las escucha y
orquesta el resto del sistema. De este modo la feature de sliders deja de
conocer el bus de simulación.
"""

from .base import _SignalManager


class SlidersSignalManager(_SignalManager):
    """
    Gestor de señales específico para el control manual por sliders.

    Hereda las señales base. En la práctica el SlidersController solo emite
    ``change_mode_signal`` y ``update_target_signal``:

    Signals (heredadas de _SignalManager):
        change_mode_signal: Sender SlidersController, receiver DataController.
            Solicita conmutar el modo global a ``Modes.SLIDERS``.
        update_target_signal: Sender SlidersController, receiver DataController.
            Publica el nuevo vector de posiciones articulares deseadas.
    """
    _instance = None

    @classmethod
    def get_instance(cls):
        """
        Obtiene la instancia única del gestor (patrón Singleton).

        Returns:
            SlidersSignalManager: Instancia única.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
