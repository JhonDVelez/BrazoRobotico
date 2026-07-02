"""
Paquete de la feature de cinemática del brazo robótico.

Proporciona los modelos de cinemática directa e inversa para el cálculo
de posiciones articulares y cartesianas del robot.
"""

from .kinematics_controller import KinematicsController

__all__ = ["KinematicsController"]
