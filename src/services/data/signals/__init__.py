"""
Paquete de gestores de señales del sistema.

Cada módulo define un SignalManager especializado (simulación, físico,
búsqueda visual, vista de dibujo, cámara, tema) que extiende la clase
base _SignalManager.
"""

from .base import _SignalManager
from .simulation import SimulationSignalManager
from .physical import PhysicalSignalManager
from .search import SearchSignalManager
from .draw_view import DrawViewSignalManager
from .camera import CameraSignalManager
from .theme import ThemeSignalManager
from .config import ConfigSignalManager
from .pick_place import PickPlaceSignalManager
from .sliders import SlidersSignalManager
from .kinematics import KinematicsSignalManager

__all__ = [
    '_SignalManager',
    'SimulationSignalManager',
    'PhysicalSignalManager',
    'SearchSignalManager',
    'DrawViewSignalManager',
    'CameraSignalManager',
    'ThemeSignalManager',
    'ConfigSignalManager',
    'PickPlaceSignalManager',
    'SlidersSignalManager',
    'KinematicsSignalManager'
]
