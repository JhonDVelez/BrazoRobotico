""" Este modulo provee diferentes herramientas para la comunicación entre la interfaz, 
    el procesamiento de datos y el robot, tanto la simulación como el robot físico.

    Las clases modes, units y domains permiten conocer el contexto de los datos que se transmiten
    asi como su origen el tratamiento que se realiza y su objetivo.

    Las clases SignalManager permiten una comunicación bidireccional entre la interfaz 
    y el controlador asi como entre el robot y el controlador.

    Las clases deg_to_rad y rad_to_deg realizan la conversion de posiciones angulares entre
    radianes y grados o viceversa.
"""
from enum import Enum
import numpy as np
from PyQt6.QtCore import pyqtSignal, QObject, QTimer


class Modes(Enum):
    """ Define el origen de los datos en la interfaz como los sliders que proporcionan el 
        angulo objetivo o las coordenadas que provee la cámara.
    """
    SLIDERS = 1


class Units(Enum):
    """ Define el tipo de unidades que requiere el robot ya sea radianes o grados tanto para 
        simulación como para el físico.
    """
    DEG = 1
    RAD = 2


class Domains(Enum):
    """ El dominio identifica si el controlador y el signal manager se conectan con el robot físico
        o con la simulación.
    """
    SIMULATION = 1
    PHYSICAL = 2


class _SignalManager(QObject):
    """ Gestor centralizado de señales para comunicación entre threads
    """
    get_data_signal = pyqtSignal()
    sensor_position_signal = pyqtSignal(list)
    model_position_signal = pyqtSignal(list)
    update_robot_signal = pyqtSignal(list)
    update_graph_signal = pyqtSignal(list)


class SimulationSignalManager(_SignalManager):
    """ SignalManager específico para simulación
    """
    update_pybullet_signal = pyqtSignal(list)
    update_model_signal = pyqtSignal(list)

    _instance = None

    @classmethod
    def get_instance(cls):
        """ Permite obtener una única instancia del objeto evitando que se generen multiples señales
            de comunicación. En caso de que no haya ninguna instancia entonces se crea una nueva.

        Returns:
            SimulationSignalManager: instancia única de la clase
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


class PhysicalSignalManager(_SignalManager):
    """ SignalManager específico para robot físico
    """
    is_connected = False
    send_to_robot = pyqtSignal(list)
    data_recibed = pyqtSignal(list, list)

    _instance = None

    @classmethod
    def get_instance(cls):
        """ Permite obtener una única instancia del objeto evitando que se generen multiples señales
            de comunicación. En caso de que no haya ninguna instancia entonces se crea una nueva.

        Returns:
            PhysicalSignalManager: instancia única de la clase
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


class GlobalTimer(QObject):
    sync_tick = pyqtSignal()
    update_tick = pyqtSignal()
    model_tick = pyqtSignal()

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
        self._data_request = 0
        GlobalTimer._initialized = True

        self.signal_manager = PhysicalSignalManager.get_instance()

    def _tick(self):
        self._sync_counter += 1
        self._model_counter += 1

        if self._model_counter >= 8:
            self.model_tick.emit()
            self._model_counter = 0

        if self._sync_counter >= 25 and not self.signal_manager.is_connected:  # Cada 100ms
            self.sync_tick.emit()
            self._sync_counter = 0
        else:  # No emitir update_tick si ya emitimos model_tick
            self.update_tick.emit()

        if self._data_request >= 4:
            self.data_request_signal.emit()
            self._data_request = 0

    def start(self):
        if not self._timer.isActive():
            self._timer.start()

    def stop(self):
        if self._timer.isActive():
            self._timer.stop()

    def is_running(self) -> bool:
        return self._timer.isActive()


def deg_to_rad(pos):
    """ Obtiene los valores objetivos de los slider/spinBox y los convierte a radianes

    Returns:
        NDArray: Array de valores objetivos en radianes
    """
    if pos is None:
        pos = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        return np.array(pos)
    return np.deg2rad(np.array(pos))


def rad_to_deg(pos):
    """ Obtiene los valores objetivos de los slider/spinBox y los convierte a radianes

    Returns:
        NDArray: Array de valores objetivos en grados
    """
    if pos is None:
        pos = []
    return np.rad2deg(np.array(pos))
