"""
Módulo que define el gestor de estado de la vista de dibujo.

Controla la visibilidad de los overlays (cuadrícula ChArUco y
geometrías de esferas) que se dibujan sobre el frame de cámara.
"""

import threading
from .config import ConfigSignalManager


class DrawViewSignalManager:
    """
    Gestor del estado de visualización de overlays en la cámara.

    Permite al usuario alternar la visualización de la cuadrícula
    ChArUco y las esferas detectadas sobre el feed de video.

    Es un singleton thread-safe.
    """
    _instance = None
    _lock_instance = threading.Lock()
    _charuco = False
    _circle = False

    @classmethod
    def get_instance(cls):
        """
        Obtiene la instancia única del gestor (patrón Singleton thread-safe).

        Returns:
            DrawViewSignalManager: Instancia única.
        """
        with cls._lock_instance:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_state()
        return cls._instance

    def _init_state(self):
        """
        Inicializa el estado desde la configuración persistente.
        """
        self._lock = threading.Lock()
        config_manager = ConfigSignalManager.get_instance()
        state = config_manager.get_param(
            "settings.json", "camera", "view", default={})
        self._charuco = state.get("charuco", False)
        self._circle = state.get("circle", False)

    def set_charuco(self, checked: bool):
        """
        Activa o desactiva el overlay de cuadrícula ChArUco.

        Args:
            checked (bool): True para mostrar la cuadrícula.
        """
        with self._lock:
            self._charuco = checked
            ConfigSignalManager.get_instance().request_change("settings.json", ["camera",
                                                              "view", "charuco"], checked)

    def set_circle(self, checked: bool):
        """
        Activa o desactiva el overlay de geometría de las esferas.

        Args:
            checked (bool): True para mostrar las esferas.
        """
        with self._lock:
            self._circle = checked
            ConfigSignalManager.get_instance().request_change("settings.json", ["camera",
                                                              "view", "circle"], checked)

    def get_state(self):
        """
        Obtiene el estado actual de ambos overlays.

        Returns:
            tuple: (charuco_visible, circle_visible).
        """
        with self._lock:
            return self._charuco, self._circle
