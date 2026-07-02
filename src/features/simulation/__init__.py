"""
Paquete de la feature de simulación del brazo robótico.

Proporciona la integración con la vista Quick3D/QML para la representación
visual del robot, así como el controlador que orquesta el intercambio de
datos entre la simulación y los gráficos de telemetría.
"""

from .simulation_controller import SimulationController

__all__ = [
    "SimulationController",
]