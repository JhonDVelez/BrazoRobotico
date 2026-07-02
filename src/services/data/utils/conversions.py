"""
Módulo de funciones de conversión entre unidades angulares.

Proporciona las funciones auxiliares deg_to_rad y rad_to_deg para
la transformación de datos entre los distintos componentes del
sistema (UI, simulación PyBullet, hardware).
"""

import numpy as np


def deg_to_rad(pos):
    """
    Convierte un array de grados a radianes.

    Args:
        pos (list or None): Lista de ángulos en grados. Si es None,
            se retorna un array de ceros.

    Returns:
        np.ndarray: Array de ángulos en radianes.
    """
    if pos is None:
        pos = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        return np.array(pos)
    return np.deg2rad(np.array(pos))


def rad_to_deg(pos):
    """
    Convierte un array de radianes a grados.

    Args:
        pos (list or None): Lista de ángulos en radianes. Si es None,
            se retorna un array vacio.

    Returns:
        np.ndarray: Array de ángulos en grados.
    """
    if pos is None:
        pos = []
    return np.rad2deg(np.array(pos))