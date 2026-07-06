"""
Paquete que agrupa las funcionalidades modulares de la aplicación.

Cada subpaquete representa una feature independiente (calibración, cámara,
color, gráficos, cinemática, simulación, sliders) siguiendo el patrón
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
