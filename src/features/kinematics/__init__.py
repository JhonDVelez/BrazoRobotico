""" Paquete encargado del control cinemático del brazo robótico.
    Implementa algoritmos de cinemática directa e inversa realimentada.
"""

from .kinematics_controller import KinematicsController

__all__ = ["KinematicsController"]
