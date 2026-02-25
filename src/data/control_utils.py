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
        Sirve para que el controlador sepa a qué fuente de entrada debe 'escuchar'.
    """
    SLIDERS = 1


class Units(Enum):
    """ Define el tipo de unidades que requiere el robot ya sea radianes o grados tanto para 
        simulación como para el físico. 
        Facilita la estandarización de los cálculos matemáticos en todo el sistema.
    """
    DEG = 1
    RAD = 2


class Domains(Enum):
    """ El dominio identifica si el controlador y el signal manager se conectan con el robot físico
        o con la simulación.
        Permite bifurcar la lógica de envío de datos según el destino seleccionado.
    """
    SIMULATION = 1
    PHYSICAL = 2


class _SignalManager(QObject):
    """ Gestor centralizado de señales para comunicación entre threads.
        Hereda de QObject para poder emitir y conectar señales de PyQt.
    """
    # Señal para solicitar nuevos datos de la fuente de entrada
    get_data_signal = pyqtSignal()
    # Señal que transporta la posición real leída (sensores o motor de física)
    actual_position_signal = pyqtSignal(list)
    # Señal para indicar al modelo visual que debe actualizar su pose
    update_robot_signal = pyqtSignal(list)
    # Señal que envía datos a las gráficas en tiempo real
    update_graph_signal = pyqtSignal(list)


class SimulationSignalManager(_SignalManager):
    """ SignalManager específico para el entorno de simulación.
        Utiliza el patrón Singleton para asegurar que todos los hilos usen el mismo canal.
    """
    # Señal exclusiva para actualizar el motor físico PyBullet
    update_pybullet_signal = pyqtSignal(list)

    _instance = None # Atributo privado para almacenar la instancia única

    @classmethod
    def get_instance(cls):
        """ Implementación del patrón Singleton. 
            Permite obtener una única instancia del objeto evitando que se generen multiples señales
            de comunicación. En caso de que no haya ninguna instancia entonces se crea una nueva.

        Returns:
            SimulationSignalManager: instancia única de la clase
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


class PhysicalSignalManager(_SignalManager):
    """ SignalManager específico para interactuar con el robot físico.
        Hereda las señales base y añade las necesarias para el hardware.
    """
    # Señal para enviar los comandos de movimiento hacia el controlador serie/hardware
    send_to_robot = pyqtSignal(list)
    # Nueva señal: envía una lista con posiciones y una lista con temperaturas
    telemetry_updated = pyqtSignal(list, list)

    _instance = None # Atributo privado para la instancia única del hardware

    @classmethod
    def get_instance(cls):
        """ Implementación del patrón Singleton.
            Permite obtener una única instancia del objeto evitando que se generen multiples señales
            de comunicación. En caso de que no haya ninguna instancia entonces se crea una nueva.

        Returns:
            PhysicalSignalManager: instancia única de la clase
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


def deg_to_rad(pos):
    """ Obtiene los valores objetivos de los slider/spinBox y los convierte a radianes.
        Utiliza NumPy para realizar la operación de forma vectorizada (eficiente para listas).

    Returns:
        NDArray: Array de valores objetivos en radianes
    """
    if pos is None:
        pos = []
    return np.deg2rad(np.array(pos))


def rad_to_deg(pos):
    """ Realiza la conversión inversa de radianes a grados. 
        Útil para mostrar datos del motor de física en los SpinBoxes de la interfaz.

    Returns:
        NDArray: Array de valores objetivos en grados
    """
    if pos is None:
        pos = []
    return np.rad2deg(np.array(pos))