"""
Modulo de utilidades geometricas para vision artificial.

Proporciona funciones para transformaciones espaciales, proyecciones de rayos
y calculos de interseccion entre el espacio de imagen y el espacio 3D.
"""

import cv2
import numpy as np


def pixel_to_camera_ray(pixel, camera_matrix, dist_coeffs, frame_size):
    """
    Convierte un punto (pixel) en la imagen en un rayo unitario en el espacio de la camara.

    Args:
        pixel (tuple): Coordenadas (x, y) del pixel.
        camera_matrix (np.ndarray): Matriz intrinseca de la camara.
        dist_coeffs (np.ndarray): Coeficientes de distorsion.
        frame_size (tuple): Tamaño (ancho, alto) del frame.

    Returns:
        np.ndarray: Vector unitario (rayo) 3x1 en coordenadas de camara.
    """
    image_point = np.array([[pixel]], dtype=np.float64)
    # UndistortPoints devuelve coordenadas normalizadas (x/z, y/z)
    undistorted = cv2.undistortPoints(
        image_point, camera_matrix, dist_coeffs, P=camera_matrix)
    
    # Para obtener el rayo en coordenadas de camara, necesitamos proyectar 
    # de nuevo al espacio normalizado (sin la matriz de camara K)
    # o usar K_inv. cv2.undistortPoints con P=None devuelve (x/z, y/z).
    undistorted_norm = cv2.undistortPoints(
        image_point, camera_matrix, dist_coeffs)
    
    x_norm, y_norm = undistorted_norm[0, 0]
    ray = np.array([[x_norm], [y_norm], [1.0]], dtype=np.float64)
    return ray / np.linalg.norm(ray)


def pixel_to_board_coordinates(pixel, rvec, tvec, camera_matrix, dist_coeffs, frame_size, plane_z=0):
    """
    Intersecta el rayo visual de un pixel con un plano paralelo al tablero ChArUco.

    Args:
        pixel (tuple): Coordenadas (x, y) del pixel en la imagen.
        rvec (np.ndarray): Vector de rotacion del tablero.
        tvec (np.ndarray): Vector de traslacion del tablero.
        camera_matrix (np.ndarray): Matriz de la camara.
        dist_coeffs (np.ndarray): Coeficientes de distorsion.
        frame_size (tuple): Tamaño del frame.
        plane_z (float): Altura del plano de interseccion respecto al tablero (mm).

    Returns:
        np.ndarray: Vector de posicion 3x1 en el espacio del tablero.
    """
    # 1. Obtener rayo en espacio de camara
    ray_cam = pixel_to_camera_ray(pixel, camera_matrix, dist_coeffs, frame_size)
    
    # 2. Matrices de transformacion
    rotation_matrix, _ = cv2.Rodrigues(rvec)
    tvec = np.asarray(tvec, dtype=np.float64).reshape(3, 1)
    
    # 3. Transformar centro de camara y rayo al espacio del tablero
    # La posicion de la camara en el espacio del tablero es -R.T @ t
    camera_center_board = -rotation_matrix.T @ tvec
    ray_board = rotation_matrix.T @ ray_cam
    
    if abs(ray_board[2, 0]) < 1e-10:
        return None  # Rayo paralelo al plano
    
    # 4. Calculo de la interseccion rayo-plano (Z = plane_z)
    # P_board = camera_center_board + ray_scale * ray_board
    # P_board[2] = plane_z  => plane_z = camera_center_board[2] + ray_scale * ray_board[2]
    ray_scale = (plane_z - camera_center_board[2, 0]) / ray_board[2, 0]
    
    return camera_center_board + ray_scale * ray_board
