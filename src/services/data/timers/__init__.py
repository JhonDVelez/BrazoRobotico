"""
Paquete de temporizadores del sistema.

Proporciona los componentes de temporizacion global (GlobalTimer) y
contador de fotogramas (FrameCounter) para la sincronizacion de
procesamiento de video y actualizacion de datos.
"""

from .global_timer import GlobalTimer
from .frame_counter import FrameCounter

__all__ = ['GlobalTimer', 'FrameCounter']