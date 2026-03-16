import numpy as np
import cv2
from data import config_manager as cfg


def apply_division_trick(img):
    """ El truco de la división: Esta es la forma más agresiva de "ignorar" una sombra. 
        Al dividir la imagen por una versión muy borrosa de sí misma, se elimina la zona 
        oscura de la sombra y solo quedan los bordes de alto contraste de las casillas 
        del tablero de ajedrez.
    """

    if img is None:
        return img

    smooth = cv2.GaussianBlur(img, (95, 95), 0)
    return cv2.divide(img, smooth, scale=255)


def sphere_pose_estimation(img, pixel_u, pixel_v, radius_sphere, camera_matrix, dist_coeffs, rvec, tvec):
    """
    Calcula la posición real (X, Y) del centro de una esfera compensando la perspectiva.

    :param imagen: Imagen actual para dibujar los ejes.
    :param pixel_u: Coordenada X (píxel) del centro de la esfera en la imagen.
    :param pixel_v: Coordenada Y (píxel) del centro de la esfera en la imagen.
    :param radio_esfera: El radio físico 'r' de la esfera (en la misma unidad que el tablero).
    """

    # 1. Dibujar el indicador visual en el origen (esquina superior izquierda)
    # El eje X será rojo (derecha), Y verde (abajo), Z azul (entrando a la mesa)
    axis_lenght = 40.0
    cv2.drawFrameAxes(img, camera_matrix, dist_coeffs,
                      rvec, tvec, axis_lenght)

    # 2. Obtener posición de la cámara (C) en el mundo 3D
    R, _ = cv2.Rodrigues(rvec)
    # Para matrices de rotación, la inversa es la transpuesta
    R_inv = np.transpose(R)
    C = -np.dot(R_inv, tvec)
    C_z = C[2][0]

    # 3. Convertir el píxel 2D a un vector direccional en el marco de la cámara
    img_dot = np.array([[[float(pixel_u), float(pixel_v)]]])

    # undistortPoints elimina la distorsión del lente y multiplica por la inversa de K
    camera_dot = cv2.undistortPoints(
        img_dot, camera_matrix, dist_coeffs)

    # El rayo direccional en coordenadas de la cámara (z=1)
    camera_ray = np.array([[camera_dot[0][0][0]],
                           [camera_dot[0][0][1]],
                           [1.0]])

    # 4. Transformar el rayo direccional al sistema de coordenadas del mundo
    world_ray = np.dot(R_inv, camera_ray)
    z_ray = world_ray[2][0]

    if z_ray == 0:
        return None  # Prevención de división por cero (rayo paralelo al plano)

    # 5. Intersección Rayo-Plano
    # Como el eje Y del tablero va hacia abajo, por regla de la mano derecha el Z positivo entra a la mesa.
    # El centro de la esfera está SOBRE la mesa, por lo que su centro está en Z = -radio_esfera
    z_plane = -radius_sphere

    # Despejamos el parámetro lambda (t) de la ecuación de la recta
    t_lambda = (z_plane - C_z) / z_ray

    # Sustituimos lambda para encontrar X e Y reales en el plano del tablero
    O_x = C[0][0] + t_lambda * world_ray[0][0]
    O_y = C[1][0] + t_lambda * world_ray[1][0]

    return O_x, O_y


def get_sphere_pose(img):
    data = cfg.load("camera.json")
    camera_matrix = data.get("matrix")
    dist_coeff = data.get("distortion coefficients")
