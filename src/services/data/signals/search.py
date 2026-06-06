"""
Modulo que define el gestor de estado de busqueda visual.

Mantiene el estado de activacion de las detecciones de ChArUco y
esferas de color, sincronizado con el archivo de configuracion.
"""

from PyQt6.QtCore import pyqtSignal, QObject
import threading
from .config import ConfigSignalManager


class SearchSignalManager(QObject):
    """
    Gestor del estado de busqueda visual para la camara.

    Permite habilitar o deshabilitar la deteccion de patrones ChArUco
    y esferas de color, persistiendo el estado en settings.json.

    Es un singleton thread-safe.
    """
    _instance = None
    _lock_instance = threading.Lock()
    
    charuco_search_changed = pyqtSignal(bool)
    circle_search_changed = pyqtSignal(bool)

    @classmethod
    def get_instance(cls):
        """
        Obtiene la instancia unica del gestor (patron Singleton thread-safe).

        Returns:
            SearchSignalManager: Instancia unica.
        """
        with cls._lock_instance:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    def __init__(self):
        super().__init__()
        self._init_state()

    def _init_state(self):
        """
        Inicializa el estado desde la configuracion persistente.
        """
        self._lock = threading.RLock()
        config_manager = ConfigSignalManager.get_instance()
        state = config_manager.get_param("settings.json", "camera", default={})
        self._charuco = state.get("charuco", False)
        self._circle = state.get("circle", False)

    def set_charuco(self, checked: bool):
        """
        Activa o desactiva la busqueda de tablero ChArUco.

        Args:
            checked (bool): True para activar.
        """
        with self._lock:
            if self._charuco == checked:
                return
            self._charuco = checked
            ConfigSignalManager.get_instance().request_change("settings.json", "camera", "charuco", value=checked)
        
        # Emitir fuera del lock para evitar deadlocks con la UI
        self.charuco_search_changed.emit(checked)

    def set_circle(self, checked: bool):
        with self._lock:
            if self._circle == checked:
                return
            self._circle = checked
            ConfigSignalManager.get_instance().request_change("settings.json", "camera", "circle", value=checked)
        
        # Emitir fuera del lock
        self.circle_search_changed.emit(checked)

    def get_state(self):
        """
        Obtiene el estado actual de ambas busquedas.

        Returns:
            tuple: (charuco_activo, circle_activa).
        """
        with self._lock:
            return self._charuco, self._circle
