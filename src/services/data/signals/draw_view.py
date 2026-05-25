"""
Modulo que define el gestor de estado de la vista de dibujo.

Controla la visibilidad de los overlays (cuadricula ChArUco y
geometrias de esferas) que se dibujan sobre el frame de camara.
"""

import threading
from .. import config_manager as cfg


class DrawViewSignalManager:
    """
    Gestor del estado de visualizacion de overlays en la camara.

    Permite al usuario alternar la visualizacion de la cuadricula
    ChArUco y las esferas detectadas sobre el feed de video.

    Es un singleton thread-safe.
    """
    _instance = None
    _lock_instance = threading.Lock()

    @classmethod
    def get_instance(cls):
        """
        Obtiene la instancia unica del gestor (patron Singleton thread-safe).

        Returns:
            DrawViewSignalManager: Instancia unica.
        """
        with cls._lock_instance:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_state()
        return cls._instance

    def _init_state(self):
        """
        Inicializa el estado desde la configuracion persistente.
        """
        self._lock = threading.Lock()
        state = cfg.get("settings.json", "camera", "view")
        self._charuco = state.get("charuco")
        self._circle = state.get("circle")

    def set_charuco(self, checked: bool):
        """
        Activa o desactiva el overlay de cuadricula ChArUco.

        Args:
            checked (bool): True para mostrar la cuadricula.
        """
        with self._lock:
            self._charuco = checked
            cfg.set_value("settings.json", "camera",
                          "view", "charuco", value=checked)

    def set_circle(self, checked: bool):
        """
        Activa o desactiva el overlay de geometria de las esferas.

        Args:
            checked (bool): True para mostrar las esferas.
        """
        with self._lock:
            self._circle = checked
            cfg.set_value("settings.json", "camera",
                          "view", "circle", value=checked)

    def get_state(self):
        """
        Obtiene el estado actual de ambos overlays.

        Returns:
            tuple: (charuco_visible, circle_visible).
        """
        with self._lock:
            return self._charuco, self._circle
