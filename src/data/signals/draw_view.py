import threading
from data import config_manager as cfg


class DrawViewSignalManager:
    _instance = None
    _lock_instance = threading.Lock()

    @classmethod
    def get_instance(cls):
        """ Permite gestionar la búsqueda del tablero y las esferas mediante señales, el usuario
            puede decidir si quiere buscar o no mediante la cámara

        Returns:
            DrawViewSignalManager: instancia única de la clase
        """
        with cls._lock_instance:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_state()
        return cls._instance

    def _init_state(self):
        self._lock = threading.Lock()
        state = cfg.get("settings.json", "camera", "view")
        self._charuco = state.get("charuco")
        self._ellipse = state.get("ellipse")

    def set_charuco(self, checked: bool):
        with self._lock:
            self._charuco = checked
            cfg.set_value("settings.json", "camera",
                          "view", "charuco", value=checked)

    def set_ellipse(self, checked: bool):
        with self._lock:
            self._ellipse = checked
            cfg.set_value("settings.json", "camera",
                          "view", "ellipse", value=checked)

    def get_state(self):
        with self._lock:
            return self._charuco, self._ellipse