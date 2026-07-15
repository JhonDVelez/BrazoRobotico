"""
Paquete de funciones utilitarias para conversión de unidades.

Expone las funciones deg_to_rad, rad_to_deg, angulos_robotang y
robotang_angulos para la conversión entre los distintos espacios
de representación del sistema.
"""

from .conversions import deg_to_rad, rad_to_deg, angulos_robotang, robotang_angulos

__all__ = ['deg_to_rad', 'rad_to_deg', 'angulos_robotang', 'robotang_angulos']