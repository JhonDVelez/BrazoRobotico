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
from PyQt6.QtCore import pyqtSignal, QObject


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
    actual_position_signal = pyqtSignal(list)
    update_robot_signal = pyqtSignal(list)
    update_graph_signal = pyqtSignal(list)


class SimulationSignalManager(_SignalManager):
    """ SignalManager específico para simulación
    """
    update_pybullet_signal = pyqtSignal(list)

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
    send_to_robot = pyqtSignal(list)

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
