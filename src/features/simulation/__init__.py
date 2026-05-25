"""
Paquete de la feature de simulacion del brazo robotico.

Proporciona la integracion con la vista Quick3D/QML para la representacion
visual del robot, asi como el controlador que orquesta el intercambio de
datos entre la simulacion y los graficos de telemetria.
"""

from .simulation_controller import SimulationController

__all__ = [
    "SimulationController",
]