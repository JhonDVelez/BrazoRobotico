"""
Módulo que define el temporizador global de sincronización.

Proporciona un singleton QTimer que emite ticks a diferentes
frecuencias para la actualización del modelo 3D, los gráficos
y la sincronización con el robot físico.
"""

from PyQt6.QtCore import pyqtSignal, QObject, QTimer
from ..signals import PhysicalSignalManager


class GlobalTimer(QObject):
    """
    Temporizador global que coordina los ciclos de actualización del sistema.

    Emite señales a distintas frecuencias:
    - model_tick: Alta frecuencia para actualización suave del modelo 3D.
    - update_tick: Frecuencia media para gráficos.
    - sync_simulation_tick / sync_robot_tick: Baja frecuencia para sincronización.

    Signals:
        sync_simulation_tick: Pulso de sincronización de simulación.
        update_tick: Actualización de gráficos.
        model_tick: Actualización del modelo 3D.
        sync_robot_tick: Pulso de sincronización del robot físico.
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
        Obtiene la instancia única del temporizador (Singleton).

        Returns:
            GlobalTimer: Instancia única.
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
        Ejecuta la lógica de distribución de ticks según contadores internos.
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
        Inicia el temporizador si no está activo.
        """
        if not self._timer.isActive():
            self._timer.start()

    def stop(self):
        """
        Detiene el temporizador si está activo.
        """
        if self._timer.isActive():
            self._timer.stop()
