"""
Modulo que define el contador de fotogramas para control de cadencia.

Proporciona un singleton que cuenta los frames entrantes y emite una
senal de procesamiento cada N frames, permitiendo reducir la carga
computacional del pipeline de vision.
"""

import threading
from PyQt6.QtCore import pyqtSignal, QObject
from .. import config_manager as cfg


class FrameCounter(QObject):
    """
    Contador de fotogramas con emision periodica.

    Cuenta los frames entrantes y emite ``process_frame_signal`` cada
    ``_interval`` ticks, permitiendo espaciar el procesamiento pesado
    de vision artificial.

    Signals:
        process_frame_signal: Se emite cuando se alcanza el intervalo.
    """
    process_frame_signal = pyqtSignal()

    _instance = None
    _initialized = False

    @classmethod
    def get_instance(cls):
        """
        Obtiene la instancia unica del contador (Singleton).

        Returns:
            FrameCounter: Instancia unica.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if FrameCounter._initialized:
            return
        super().__init__()
        self._interval = cfg.get(
            "settings.json", "camera", "view", "interval")
        self._counter = 0
        self._lock = threading.Lock()
        FrameCounter._initialized = True

    def tick(self):
        """
        Incrementa el contador y emite la senal al alcanzar el intervalo.
        """
        with self._lock:
            self._counter += 1
            if self._counter >= self._interval:
                try:
                    self.process_frame_signal.emit()
                finally:
                    self._counter = 0

    def reset(self):
        """
        Reinicia el contador a cero.
        """
        with self._lock:
            self._counter = 0

    def set_interval(self, interval: int):
        """
        Establece un nuevo intervalo de emision y persiste el cambio.

        Args:
            interval (int): Nuevo intervalo en frames.
        """
        with self._lock:
            self._interval = int(interval)
            self._counter = 0
            cfg.set_value("settings.json", "camera", "view",
                          "interval", value=self._interval)
