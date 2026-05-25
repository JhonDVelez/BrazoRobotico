"""
Paquete de servicios transversales de la aplicacion.

Proporciona los subsistemas de datos, dispositivos, robot, simulacion,
estilos, interfaz de usuario y vision artificial.
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
