"""
Paquete de gestores de senales del sistema.

Cada modulo define un SignalManager especializado (simulacion, fisico,
busqueda visual, vista de dibujo, camara, tema) que extiende la clase
base _SignalManager.
"""

from .base import _SignalManager
from .simulation import SimulationSignalManager
from .physical import PhysicalSignalManager
from .search import SearchSignalManager
from .draw_view import DrawViewSignalManager
from .camera import CameraSignalManager
from .theme import ThemeSignalManager

__all__ = [
    '_SignalManager',
    'SimulationSignalManager',
    'PhysicalSignalManager',
    'SearchSignalManager',
    'DrawViewSignalManager',
    'CameraSignalManager',
    'ThemeSignalManager'
]
