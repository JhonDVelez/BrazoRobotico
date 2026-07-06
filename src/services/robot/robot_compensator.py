"""
Metodos estaticos de conversion y limitacion para comandos del robot fisico.

Mantiene las utilidades compartidas entre KinematicsWorker y el servicio serial:
conversion angulo-servo y saturacion de limites fisicos.
"""

import math
import numpy as np

_LIMITS_DEG = [(-100.0, 100.0), (-90.0, 90.0),
               (-130.0, 130.0), (-90.0, 120.0)]


class CartesianPidCompensator:
    """Metodos estaticos de conversion y limitacion articular."""

    @staticmethod
    def angulos_robotang(q1, q2, q3, q4, q5, q6):
        """Convierte angulos articulares a posiciones de servo (0-300)."""
        return [q1 + 150, 150 - q2, 150 - q3, q4 + 150, q5 + 150, q6 + 150]

    @staticmethod
    def robotang_angulos(q1, q2, q3, q4, q5, q6):
        """Convierte posiciones de servo (0-300) a angulos articulares."""
        return [q1 - 150, 150 - q2, 150 - q3, q4 - 150, q5 - 150, q6 - 150]

    @staticmethod
    def apply_physical_limits(q_rad, limites_deg=None):
        """Satura cada articulacion segun los limites fisicos del robot."""
        if limites_deg is None:
            limites_deg = _LIMITS_DEG
        q_ajustado = []
        for index, angle in enumerate(q_rad):
            angle_deg = math.degrees(angle)
            low, high = limites_deg[index]
            q_ajustado.append(math.radians(max(low, min(angle_deg, high))))
        return np.array(q_ajustado)
