"""
Paquete de temporizadores del sistema.

Proporciona los componentes de temporización global (GlobalTimer) y
contador de fotogramas (FrameCounter) para la sincronización de
procesamiento de video y actualización de datos.
"""

from .global_timer import GlobalTimer
from .frame_counter import FrameCounter

__all__ = ['GlobalTimer', 'FrameCounter']