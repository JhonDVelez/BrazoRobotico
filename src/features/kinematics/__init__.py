"""
Paquete de la feature de cinematica del brazo robotico.

Proporciona los modelos de cinematica directa e inversa para el calculo
de posiciones articulares y cartesianas del robot.
"""

from .kinematics_controller import KinematicsController

__all__ = ["KinematicsController"]
