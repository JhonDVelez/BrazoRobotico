import numpy as np
from enum import Enum
from PyQt6.QtCore import pyqtSignal, QObject


class modes(Enum):
    SLIDERS = 1


class units(Enum):
    DEG = 1
    RAD = 2


class domains(Enum):
    SIMULATION = 1
    PHYSICAL = 2


class SignalManager(QObject):
    """ Gestor centralizado de señales para comunicación entre threads
    """
    get_data_signal = pyqtSignal()
    actual_position_signal = pyqtSignal(list)
    update_robot_signal = pyqtSignal(list)
    update_graph_signal = pyqtSignal(list)


class SimulationSignalManager(SignalManager):
    """ SignalManager específico para simulacion
    """
    update_pybullet_signal = pyqtSignal(list)

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


class PhysicalSignalManager(SignalManager):
    """ SignalManager específico para robot físico
    """
    send_to_robot = pyqtSignal(list)

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


def deg_to_rad(pos):
    """ Obtiene los valores objetivos de los slider/spinBox y los convierte a radianes

    Returns:
        NDArray: Array de valores objetivos en radianes
    """
    if pos is None:
        pos = []
    return np.deg2rad(np.array(pos))


def rad_to_deg(pos):
    """ Obtiene los valores objetivos de los slider/spinBox y los convierte a radianes

    Returns:
        NDArray: Array de valores objetivos en grados
    """
    if pos is None:
        pos = []
    return np.rad2deg(np.array(pos))
