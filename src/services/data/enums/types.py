from enum import Enum


class Modes(Enum):
    """ Define el origen de los datos en la interfaz como los sliders que proporcionan el 
        angulo objetivo o las coordenadas que provee la cámara.
    """
    SLIDERS = 1
    KINEMATIC = 2


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