"""
Modulo que define el gestor de senales para el dominio de sliders.

Proporciona el singleton SlidersSignalManager, el bus de intencion saliente
del control manual por sliders. El SlidersController publica aqui sus
peticiones de cambio de modo y de objetivo; el DataController las escucha y
orquesta el resto del sistema. De este modo la feature de sliders deja de
conocer el bus de simulacion.
"""

from .base import _SignalManager


class SlidersSignalManager(_SignalManager):
    """
    Gestor de senales especifico para el control manual por sliders.

    Hereda las senales base. En la practica el SlidersController solo emite
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
        Obtiene la instancia unica del gestor (patron Singleton).

        Returns:
            SlidersSignalManager: Instancia unica.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
