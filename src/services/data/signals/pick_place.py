from PyQt6.QtCore import pyqtSignal, QObject
import threading
from .config import ConfigSignalManager


class PickPlaceSignalManager(QObject):
    _instance = None
    _pk_active = False

    poses_from_camera = pyqtSignal(dict)
    spheres_detected_2d = pyqtSignal(dict)
    sphere_selected = pyqtSignal(str)
    pick_requested = pyqtSignal(str)
    inverse_kinematics_requested = pyqtSignal(dict)
    inverse_kinematics_ready = pyqtSignal(dict)
    state_changed = pyqtSignal(bool)

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._init_state()
        return cls._instance

    def _init_state(self):
        """
        Inicializa el estado desde la configuracion persistente.
        """
        self._lock = threading.Lock()
        config_manager = ConfigSignalManager.get_instance()
        self._pk_active = config_manager.get_param(
            "settings.json", "mode", "pick_place", default=False)

    def get_state(self):
        """ Retorna el estado del modo pick and place

        Returns:
            bool: estado del modo
        """
        return self._pk_active

    def set_state(self, state):
        """ Establece nuevo estado del modo pick and place

        Args:
            state (bool): nuevo estado del modo
        """
        self._pk_active = state
        self.state_changed.emit(state)
