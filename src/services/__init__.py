"""
Paquete de servicios transversales de la aplicación.

Proporciona los subsistemas de datos, dispositivos, robot, simulación,
estilos, interfaz de usuario y visión artificial.
"""

from . import data, devices, robot, simulation, styling, ui, vision

__all__ = [
    "data",
    "devices",
    "robot",
    "simulation",
    "styling",
    "ui",
    "vision"
]
