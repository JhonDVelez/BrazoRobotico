"""
Paquete de la feature de sistema de pick and place.

Proporciona los componentes para el cálculo y manejo de datos de la funcionalidad
pick and place una vez se obtienen las posiciones de las esfera, permitiendo enviar
datos objetivos de robot tanto en simulación como en físico.

Conexiones:
    - PickAndPlaceController coordina con PickPlaceSignalManager (bus global).
    - PickAndPlaceWorker ejecuta la máquina de estados con feedback del robot/sim.
    - PickPlaceState define los estados de la secuencia de pickup.
"""

from .pick_and_place_controller import PickAndPlaceController
from .pick_and_place_widget import PickAndPlaceWidget
from .pick_and_place_worker import PickAndPlaceWorker
from .pick_place_states import PickPlaceState

__all__ = [
    "PickAndPlaceController",
    "PickAndPlaceWidget",
    "PickAndPlaceWorker",
    "PickPlaceState"
]
