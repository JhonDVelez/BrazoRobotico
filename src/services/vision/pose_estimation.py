"""
Modulo para la estimacion de pose 3D de esferas de color.

Este modulo implementa la clase PoseEstimation que, utilizando los resultados
de deteccion de esferas y la pose de un tablero ChArUco, calcula la posicion
3D de esferas apoyadas sobre el plano del tablero.

Conexiones:
    - Ejecutado por un QThreadPool.
    - Reporta resultados a traves de `pose_callback`.
    - Reporta errores a traves de `error_callback`.
"""

import cv2
import numpy as np
from PyQt6.QtCore import QRunnable


class PoseEstimation(QRunnable):
    """
    Tarea ejecutable para estimar la posicion 3D de esferas detectadas.

    Esta clase utiliza tecnicas de ray-casting para intersectar el rayo visual
    proveniente del centro de una esfera con un plano paralelo al tablero
    ChArUco, situado a una distancia igual al radio de la esfera.
    """

    def __init__(self, results: dict, camera_matrix, dist_coeffs, frame_size,
                 sphere_radius, custom_origin_offset, error_callback,
                 frame_id=None, pose_callback=None):
        """
        Inicializa la tarea de estimacion de pose.

        Args:
            results (dict): Diccionario con resultados de 'circles' y 'charuco'.
            camera_matrix (np.ndarray): Matriz intrinseca de la camara.
            dist_coeffs (np.ndarray): Coeficientes de distorsion de la camara.
            frame_size (tuple): Tamaño del frame (ancho, alto).
            sphere_radius (float): Radio fisico de las esferas (mm).
            custom_origin_offset (list): Offset [x, y, z] para el origen personalizado.
            error_callback (callable): Funcion para reportar errores.
            frame_id (int, optional): Identificador del frame procesado.
            pose_callback (callable, optional): Funcion para devolver los resultados.
        """
        super().__init__()
        self.circle_results = results.get("circles") or {}
        self.charuco_results = results.get("charuco") or {}
        self.rvec = self.charuco_results.get("rvec")
        self.tvec = self.charuco_results.get("tvec")
        self.camera_matrix = np.asarray(camera_matrix, dtype=np.float64)
        self.dist_coeffs = np.asarray(dist_coeffs, dtype=np.float64)
        self.frame_size = frame_size
        self.sphere_radius = sphere_radius
        self.error_callback = error_callback
        self.frame_id = frame_id
        self.pose_callback = pose_callback

        # El offset C que el usuario define como el nuevo (0,0)
        self.custom_origin_offset = np.array(
            custom_origin_offset, dtype=np.float64).reshape(3, 1)

    def run(self):
        """
        Ejecuta el proceso de estimacion de pose para todas las elipses detectadas.

        Valida la pose del tablero ChArUco, calcula la matriz de rotacion
        y proyecta cada esfera al espacio 3D del tablero y del origen personalizado.
        """
        try:
            if self.rvec is None or self.tvec is None:
                self.error_callback(
                    "No fue posible estimar la pose del tablero ChArUco.")
                return

            if not self.circle_results:
                return

            # R transforma coordenadas del tablero hacia coordenadas de camara.
            rotation_matrix, _ = cv2.Rodrigues(self.rvec)

            final_poses = {}

            for color_name, sphere_data in self.circle_results.items():
                p_world = self._calculate_sphere_board_coordinates(
                    sphere_data, rotation_matrix)
                p_cam = rotation_matrix @ p_world + self.tvec.reshape(3, 1)
                p_final = self._apply_custom_origin(p_world)

                final_poses[color_name] = p_final.flatten().tolist()
                sphere_data["position"] = final_poses[color_name]
                sphere_data["position_board"] = p_world.flatten().tolist()
                sphere_data["position_camera"] = p_cam.flatten().tolist()

            if self.pose_callback is not None:
                self.pose_callback(self.frame_id, final_poses)

        except Exception as e:
            self.error_callback(str(e))

    def _calculate_sphere_board_coordinates(self, sphere_data, rotation_matrix):
        """
        Calcula las coordenadas 3D de la esfera respecto al tablero.

        Intersecta el rayo del centro 2D de la esfera con el plano paralelo al
        tablero donde debe estar el centro 3D de una esfera apoyada en el.

        Args:
            sphere_data (dict): Datos de la elipse detectada.
            rotation_matrix (np.ndarray): Matriz de rotacion del tablero (3x3).

        Returns:
            np.ndarray: Vector de posicion 3x1 en el espacio del tablero.

        Raises:
            ValueError: Si el centro de la esfera es invalido o el rayo es paralelo al plano.
        """
        center = sphere_data.get("center")
        if center is None:
            raise ValueError("Centro de la esfera perdido.")

        ray_cam = self._pixel_to_camera_ray(center)
        tvec = np.asarray(self.tvec, dtype=np.float64).reshape(3, 1)
        rotation_matrix = np.asarray(rotation_matrix, dtype=np.float64)

        # Transformamos el centro de la camara y el rayo al espacio del tablero
        camera_center_board = -rotation_matrix.T @ tvec
        ray_board = rotation_matrix.T @ ray_cam

        if abs(ray_board[2, 0]) < 1e-10:
            raise ValueError("El rayo es paralelo al plano de soporte de la esfera.")

        # La esfera esta del lado visible del tablero: el mismo lado donde esta la camara.
        support_z = self.sphere_radius
        if camera_center_board[2, 0] < 0:
            support_z = -self.sphere_radius

        # Calculo de la interseccion rayo-plano
        ray_scale = (support_z - camera_center_board[2, 0]) / ray_board[2, 0]
        return camera_center_board + ray_scale * ray_board

    def _pixel_to_camera_ray(self, center):
        """
        Convierte un pixel distorsionado en un rayo normalizado de camara.

        Args:
            center (tuple): Coordenadas (x, y) del pixel en la imagen original.

        Returns:
            np.ndarray: Vector unitario (rayo) 3x1 en coordenadas de camara.
        """
        image_point = np.array([[center]], dtype=np.float64)
        new_camera_matrix, _ = cv2.getOptimalNewCameraMatrix(
            self.camera_matrix, self.dist_coeffs, self.frame_size, 1)
        # UndistortPoints devuelve coordenadas normalizadas (x/z, y/z)
        undistorted = cv2.undistortPoints(
            image_point, new_camera_matrix, self.dist_coeffs)
        x_norm, y_norm = undistorted[0, 0]
        return np.array([[x_norm], [y_norm], [1.0]], dtype=np.float64)

    def _apply_custom_origin(self, p_world):
        """
        Aplica el desplazamiento del origen personalizado.

        Args:
            p_world (np.ndarray): Coordenadas 3x1 en el espacio del tablero.

        Returns:
            np.ndarray: Coordenadas 3x1 respecto al origen personalizado.
        """
        # Restar el offset fisico definido por el usuario para trasladar el origen
        p_final = p_world - self.custom_origin_offset
        return p_final
