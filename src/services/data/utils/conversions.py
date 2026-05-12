import numpy as np


def deg_to_rad(pos):
    """ Obtiene los valores objetivos de los slider/spinBox y los convierte a radianes

    Returns:
        NDArray: Array de valores objetivos en radianes
    """
    if pos is None:
        pos = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        return np.array(pos)
    return np.deg2rad(np.array(pos))


def rad_to_deg(pos):
    """ Obtiene los valores objetivos de los slider/spinBox y los convierte a radianes

    Returns:
        NDArray: Array de valores objetivos en grados
    """
    if pos is None:
        pos = []
    return np.rad2deg(np.array(pos))