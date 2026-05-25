"""
Modulo que define el temporizador global de sincronizacion.

Proporciona un singleton QTimer que emite ticks a diferentes
frecuencias para la actualizacion del modelo 3D, los graficos
y la sincronizacion con el robot fisico.
"""

from PyQt6.QtCore import pyqtSignal, QObject, QTimer
from ..signals import PhysicalSignalManager


class GlobalTimer(QObject):
    """
    Temporizador global que coordina los ciclos de actualizacion del sistema.

    Emite senales a distintas frecuencias:
    - model_tick: Alta frecuencia para actualizacion suave del modelo 3D.
    - update_tick: Frecuencia media para graficos.
    - sync_simulation_tick / sync_robot_tick: Baja frecuencia para sincronizacion.

    Signals:
        sync_simulation_tick: Pulso de sincronizacion de simulacion.
        update_tick: Actualizacion de graficos.
        model_tick: Actualizacion del modelo 3D.
        sync_robot_tick: Pulso de sincronizacion del robot fisico.
    """
    sync_simulation_tick = pyqtSignal()
    update_tick = pyqtSignal()
    model_tick = pyqtSignal()
    sync_robot_tick = pyqtSignal()

    _instance = None
    _initialized = False

    @classmethod
    def get_instance(cls):
        """
        Obtiene la instancia unica del temporizador (Singleton).

        Returns:
            GlobalTimer: Instancia unica.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if GlobalTimer._initialized:
            return
        super().__init__()
        self._timer = QTimer()
        self._timer.setInterval(4)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

        self._sync_counter = 0
        self._model_counter = 0
        GlobalTimer._initialized = True

        self.signal_manager = PhysicalSignalManager.get_instance()

    def _tick(self):
        """
        Ejecuta la logica de distribucion de ticks segun contadores internos.
        """
        self._sync_counter += 1
        self._model_counter += 1

        if self._model_counter >= 4:
            self.model_tick.emit()
            self._model_counter = 0

        if self._sync_counter >= 25:
            if not self.signal_manager.is_connected:
                self.sync_simulation_tick.emit()
            else:
                self.sync_robot_tick.emit()
            self._sync_counter = 0
        else:
            self.update_tick.emit()

    def start(self):
        """
        Inicia el temporizador si no esta activo.
        """
        if not self._timer.isActive():
            self._timer.start()

    def stop(self):
        """
        Detiene el temporizador si esta activo.
        """
        if self._timer.isActive():
            self._timer.stop()
