from PyQt6.QtCore import pyqtSignal, QObject, QTimer
from data.signals.physical import PhysicalSignalManager


class GlobalTimer(QObject):
    # Pulso de sincronización
    sync_simulation_tick = pyqtSignal()
    # Actualiza la simulación y envía datos a la gráfica
    update_tick = pyqtSignal()
    # Solicita datos para 3D mas rápido que el de la gráfica para fluidez
    model_tick = pyqtSignal()
    sync_robot_tick = pyqtSignal()

    _instance = None
    _initialized = False

    @classmethod
    def get_instance(cls):
        """ Permite obtener una única instancia del objeto evitando que se generen multiples señales
            de sincronización. En caso de que no haya ninguna instancia entonces se crea una nueva.

        Returns:
            GlobalTimer: instancia única de la clase
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if GlobalTimer._initialized:
            return
        super().__init__()
        self._timer = QTimer()
        self._timer.setInterval(4)  # Mayor frecuencia para precisión
        self._timer.timeout.connect(self._tick)
        self._timer.start()

        self._sync_counter = 0
        self._model_counter = 0
        GlobalTimer._initialized = True

        self.signal_manager = PhysicalSignalManager.get_instance()

    def _tick(self):
        self._sync_counter += 1
        self._model_counter += 1

        if self._model_counter >= 4:
            self.model_tick.emit()
            self._model_counter = 0

        if self._sync_counter >= 25:  # Cada 100ms
            if not self.signal_manager.is_connected:
                self.sync_simulation_tick.emit()
            else:
                self.sync_robot_tick.emit()
            self._sync_counter = 0
        else:  # No emitir update_tick si ya emitimos model_tick
            self.update_tick.emit()

    def start(self):
        if not self._timer.isActive():
            self._timer.start()

    def stop(self):
        if self._timer.isActive():
            self._timer.stop()