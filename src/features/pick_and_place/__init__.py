"""
Paquete de la feature de sistema de pick and place.

Proporciona los componentes para el calculo y manejo de datos de la funcionalidad
pick and place una vez se obtienen las posiciones de las esfera, permitiendo enviar
datos objetivos de robot tanto en simulación como en físico.
"""

from .pick_and_place_controller import PickAndPlaceController
from .pick_and_place_widget import PickAndPlaceWidget

__all__ = [
    "PickAndPlaceController",
    "PickAndPlaceWidget"
]
