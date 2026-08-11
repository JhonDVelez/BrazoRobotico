"""
Módulo de funciones de conversión entre unidades angulares.

Proporciona las funciones auxiliares deg_to_rad, rad_to_deg,
angulos_robotang y robotang_angulos para la transformación de datos
entre los distintos componentes del sistema (UI, simulación PyBullet, hardware).
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


def angulos_robotang(q1, q2, q3, q4, q5, q6):
    """Convierte ángulos del espacio de usuario a espacio robot (0-300).

    Args:
        q1-q6: Ángulos articulares en el espacio del usuario.

    Returns:
        list: Posiciones en el espacio del robot (0-300).
    """
    return [q1 + 150, 150 - q2, 150 - q3, q4 + 150, q5 + 150, q6 + 150]


def robotang_angulos(q1, q2, q3, q4, q5, q6):
    """Convierte posiciones del robot (0-300) a ángulos del espacio de usuario.

    Args:
        q1-q6: Posiciones en el espacio del robot (0-300).

    Returns:
        list: Ángulos articulares en el espacio del usuario.
    """
    return [q1 - 150, 150 - q2, 150 - q3, q4 - 150, q5 - 150, q6 - 150]


def process_robot_positions_for_viz(raw_pos):
    """Procesa posiciones crudas del robot para la visualización 3D."""
    # 1. Convertir de unidades de servo (0-300) a ángulos (°)
    angulos = robotang_angulos(*raw_pos)
    
    # 2. Procesamiento: invertir motores 5 y 6 (índices 4 y 5) y redondear a entero
    processed_pos = []
    for i, val in enumerate(angulos):
        if i in [4, 5]: # Motores 5 y 6
            processed_pos.append(float(-val))
        else:
            processed_pos.append(float(val))
    return processed_pos
