from PyQt6.QtCore import pyqtSignal, QObject
import threading
from .config import ConfigSignalManager


class PickPlaceSignalManager(QObject):
    _instance = None
    _pk_active = False
    _pick_place_running = False

    poses_from_camera = pyqtSignal(dict)
    spheres_detected_2d = pyqtSignal(dict)
    sphere_selected = pyqtSignal(str)
    place_requested = pyqtSignal(dict)
    pick_requested = pyqtSignal(str)
    inverse_kinematics_requested = pyqtSignal(dict)
    inverse_kinematics_ready = pyqtSignal(dict)
    target_reached = pyqtSignal(list)
    state_changed = pyqtSignal(bool)
    pick_place_running_changed = pyqtSignal(bool)
    release_sphere_request = pyqtSignal(str)
    reattach_sphere_request = pyqtSignal(str)
    clear_spheres_request = pyqtSignal()
    # Peticion de (des)activar la busqueda de esferas en la camara.
    # Sender PickAndPlaceController, receiver DataController -> SearchSignalManager.
    search_circle_request = pyqtSignal(bool)

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

    def is_pick_place_running(self):
        """Retorna True si una secuencia de pick and place esta en ejecucion."""
        return self._pick_place_running

    def set_pick_place_running(self, running):
        """Establece el estado de ejecucion de la secuencia.

        Args:
            running (bool): True si la secuencia esta activa.
        """
        self._pick_place_running = running
        self.pick_place_running_changed.emit(running)
