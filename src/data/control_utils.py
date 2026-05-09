""" Este modulo provee diferentes herramientas para la comunicación entre la interfaz, 
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

# Enums - backwards compatibility
from data.enums.types import Modes, Units, Domains

# Signal managers - backwards compatibility
from data.signals.base import _SignalManager
from data.signals.simulation import SimulationSignalManager
from data.signals.physical import PhysicalSignalManager
from data.signals.search import SearchSignalManager
from data.signals.draw_view import DrawViewSignalManager
from data.signals.camera import CameraSignalManager

# Timers - backwards compatibility
from data.timers.global_timer import GlobalTimer
from data.timers.frame_counter import FrameCounter

# Utils - backwards compatibility
from data.utils.conversions import deg_to_rad, rad_to_deg

__all__ = [
    # Enums
    'Modes', 'Units', 'Domains',
    # Signal managers
    '_SignalManager',
    'SimulationSignalManager',
    'PhysicalSignalManager',
    'SearchSignalManager',
    'DrawViewSignalManager',
    'CameraSignalManager',
    # Timers
    'GlobalTimer',
    'FrameCounter',
    # Utils
    'deg_to_rad',
    'rad_to_deg',
]