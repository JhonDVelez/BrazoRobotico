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
from src.services.vision.geometry_utils import pixel_to_board_coordinates


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
            final_poses = {}

            if self.rvec is None or self.tvec is None:
                # No podemos estimar poses sin el tablero, reportamos vacio
                if self.pose_callback is not None:
                    self.pose_callback(self.frame_id, final_poses)
                return

            if not self.circle_results:
                # No hay esferas detectadas, reportamos vacio
                if self.pose_callback is not None:
                    self.pose_callback(self.frame_id, final_poses)
                return

            # R transforma coordenadas del tablero hacia coordenadas de camara.
            rotation_matrix, _ = cv2.Rodrigues(self.rvec)

            for color_name, sphere_data in self.circle_results.items():
                center = sphere_data.get("center")
                if center is None:
                    continue
                
                # Calculamos la posicion del centro de la esfera (plane_z = radio)
                p_world = pixel_to_board_coordinates(
                    center, self.rvec, self.tvec, self.camera_matrix, 
                    self.dist_coeffs, self.frame_size, self.sphere_radius
                )
                
                if p_world is None:
                    continue

                p_final = self._apply_custom_origin(p_world)

                final_poses[color_name] = p_final.flatten().tolist()
                sphere_data["position"] = final_poses[color_name]

            if self.pose_callback is not None:
                self.pose_callback(self.frame_id, final_poses)

        except Exception as e:
            self.error_callback(str(e))

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
