""" Este paquete provee diferentes herramientas para la comunicación entre la interfaz, 
    el procesamiento de datos y el robot, tanto la simulación como el robot físico.

    Las clases modes, units y domains permiten conocer el contexto de los datos que se transmiten
    asi como su origen el tratamiento que se realiza y su objetivo.

    Las clases SignalManager permiten una comunicación bidireccional entre la interfaz 
    y el controlador asi como entre el robot y el controlador.

    Las clases deg_to_rad y rad_to_deg realizan la conversion de posiciones angulares entre
    radianes y grados o viceversa.

    NOTA: Este módulo mantiene backwards compatibility. El código nuevo debería importar
    directamente de los submódulos:
    - from data.enums import Modes, Units, Domains
    - from data.signals import SimulationSignalManager, PhysicalSignalManager, ...
    - from data.timers import GlobalTimer, FrameCounter
    - from data.utils import deg_to_rad, rad_to_deg
"""


from src.services.data.data_controller import DataController
from src.services.data.config_manager import init_config, load, save, get, set_value
from src.services.data import enums, signals, timers, utils

__all__ = [
    "DataController",
    "init_config",
    "load",
    "save",
    "get",
    "set_value",
    "enums",
    "signals",
    "timers",
    "utils"
]
