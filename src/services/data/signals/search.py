"""
Modulo que define el gestor de estado de busqueda visual.

Mantiene el estado de activacion de las detecciones de ChArUco y
esferas de color, sincronizado con el archivo de configuracion.
"""

import threading
from .. import config_manager as cfg


class SearchSignalManager:
    """
    Gestor del estado de busqueda visual para la camara.

    Permite habilitar o deshabilitar la deteccion de patrones ChArUco
    y esferas de color, persistiendo el estado en settings.json.

    Es un singleton thread-safe.
    """
    _instance = None
    _lock_instance = threading.Lock()

    @classmethod
    def get_instance(cls):
        """
        Obtiene la instancia unica del gestor (patron Singleton thread-safe).

        Returns:
            SearchSignalManager: Instancia unica.
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
        state = cfg.get("settings.json", "camera")
        self._charuco = state.get("charuco")
        self._circle = state.get("circle")

    def set_charuco(self, checked: bool):
        """
        Activa o desactiva la busqueda de tablero ChArUco.

        Args:
            checked (bool): True para activar.
        """
        with self._lock:
            self._charuco = checked
            cfg.set_value("settings.json", "camera", "charuco", value=checked)

    def set_circle(self, checked: bool):
        with self._lock:
            self._circle = checked
            cfg.set_value("settings.json", "camera", "circle", value=checked)

    def get_state(self):
        """
        Obtiene el estado actual de ambas busquedas.

        Returns:
            tuple: (charuco_activo, circle_activa).
        """
        with self._lock:
            return self._charuco, self._circle
