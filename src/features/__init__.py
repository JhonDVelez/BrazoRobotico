"""
Paquete que agrupa las funcionalidades modulares de la aplicacion.

Cada subpaquete representa una feature independiente (calibracion, camara,
color, graficos, cinematica, simulacion, sliders) siguiendo el patron
Worker-Widget-Controller.
"""
from .camera import devices_submenu

from . import calibration, camera, color, graph, kinematics, simulation, sliders

__all__ = [
    "calibration",
    "camera",
    "color",
    "devices_submenu",
    "graph",
    "kinematics",
    "simulation",
    "sliders"
]
