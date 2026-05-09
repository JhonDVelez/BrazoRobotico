import threading
from PyQt6.QtCore import pyqtSignal, QObject
from data import config_manager as cfg


class FrameCounter(QObject):
    """Cuenta fotogramas y emite `process_frame_signal` cada N frames.

    Uso:
    - Obtener instancia con `FrameCounter.get_instance(interval)`
    - Llamar `tick(frame)` por cada fotograma entrante
    - Conectar a `process_frame_signal` para ejecutar procesamiento cada N frames
    """
    process_frame_signal = pyqtSignal()

    _instance = None
    _initialized = False

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if FrameCounter._initialized:
            return
        super().__init__()
        self._interval = cfg.get("settings.json", "camera", "view", "interval")
        self._counter = 0
        self._lock = threading.Lock()
        FrameCounter._initialized = True

    def tick(self):
        """Incrementa contador; emite `process_frame_signal` cada `_interval` frames."""
        with self._lock:
            self._counter += 1
            if self._counter >= self._interval:
                try:
                    self.process_frame_signal.emit()
                finally:
                    self._counter = 0

    def reset(self):
        with self._lock:
            self._counter = 0

    def set_interval(self, interval: int):
        with self._lock:
            self._interval = int(interval)
            self._counter = 0
            cfg.set_value("settings.json", "camera", "view",
                          "interval", value=self._interval)