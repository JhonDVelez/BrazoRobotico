import math
import traceback
import numpy as np
import cv2
from PyQt6.QtCore import QRunnable


class PoseEstimation(QRunnable):
    def __init__(self, results: dict, camera_matrix, dist_coeffs,
                 sphere_radius, custom_origin_offset, error_callback):
        """ Constructor de la tarea.
        """
        super().__init__()
        self.ellipse_results = results.get("ellipses")
        self.charuco_results = results.get("charuco")
        self.charuco_board = results.get("board")
        self.rvec = self.charuco_results.get("rvec")
        self.tvec = self.charuco_results.get("tvec")
        self.camera_matrix = camera_matrix
        self.dist_coeffs = dist_coeffs
        self.sphere_radius = sphere_radius
        self.error_callback = error_callback

        # El offset C que el usuario define como el nuevo (0,0)
        self.custom_origin_offset = np.array(
            custom_origin_offset).reshape(3, 1)

    def run(self):
        """
        Función principal ejecutada por el QThreadPool.
        """
        try:
            if self.rvec is None or self.tvec is None:
                self.error_callback("Could not estimate ChArUco board pose.")
                return

            # Matriz de rotación (De Mundo a Cámara)
            rotation_matrix, _ = cv2.Rodrigues(self.rvec)

            final_poses = {}

            # 2. Procesar cada esfera encontrada (por color)
            for color_name, ellipse_data in self.ellipse_results.items():

                # 3. Calcular la coordenada de la esfera relativa a la cámara (Algoritmo Sección 3)
                p_cam = self._calculate_sphere_camera_coordinates(ellipse_data)

                # 4. Transformar al sistema de coordenadas original del tablero ChArUco
                p_world = self._transform_to_board_coordinates(
                    p_cam, rotation_matrix, self.tvec)

                # 5. Aplicar el desplazamiento para que el punto 'C' sea el nuevo (0,0,0)
                p_final = self._apply_custom_origin(p_world)

                # Guardar el resultado aplanado [X, Y, Z]
                final_poses[color_name] = p_final.flatten().tolist()

            # Emitir los resultados cuando termine
            print(final_poses)

        except Exception as e:
            self.error_callback(str(e))

    def _calculate_sphere_camera_coordinates(self, ellipse_data):
        """
        Aplica el algoritmo matemático exacto (Sección 3) para encontrar 
        la posición P de la esfera respecto a la cámara.
        """
        # Extraer parámetros de la cámara
        # Distancia focal (asumiendo píxeles cuadrados fx ~ fy)
        f = self.camera_matrix[0, 0]
        u_0 = self.camera_matrix[0, 2]  # Punto principal X
        v_0 = self.camera_matrix[1, 2]  # Punto principal Y

        # Extraer parámetros de la elipse
        u_m, v_m = ellipse_data["center"]
        # Asumiendo que 'a' es el semi-eje mayor (la mitad del largo total)
        a = ellipse_data["major"]

        # Distancia en píxeles desde el centro de la elipse al punto principal
        delta_m = math.hypot(u_m - u_0, v_m - v_0)

        # Ecuaciones trigonométricas del artículo
        term1 = math.atan((delta_m + a) / f)
        term2 = math.atan((delta_m - a) / f)

        phi = (term1 + term2) / 2.0
        theta = (term1 - term2) / 2.0

        # Distancia desde el centro óptico al centro de la esfera (Módulo de OP)
        distance_op = self.sphere_radius * \
            math.sqrt(math.pow(math.tan(theta), 2) + 1) / math.tan(theta)

        # Proyección del centro de la esfera en el plano de la imagen (Punto Q)
        if delta_m < 1e-5:
            # Si la esfera está perfectamente centrada en el punto principal
            u_q, v_q = u_0, v_0
        else:
            u_q = u_0 + (f * math.tan(phi) / delta_m) * (u_m - u_0)
            v_q = v_0 + (f * math.tan(phi) / delta_m) * (v_m - v_0)

        # Módulo de OQ (Distancia en píxeles)
        distance_oq = math.sqrt(
            math.pow(u_q - u_0, 2) + math.pow(v_q - v_0, 2) + math.pow(f, 2))

        # Posición 3D final relativa a la cámara
        x_cam = (distance_op / distance_oq) * (u_q - u_0)
        y_cam = (distance_op / distance_oq) * (v_q - v_0)
        z_cam = (distance_op / distance_oq) * f

        return np.array([[x_cam], [y_cam], [z_cam]])

    def _transform_to_board_coordinates(self, p_cam, rotation_matrix, tvec):
        """
        Convierte el punto P del sistema de la cámara al sistema original del tablero.
        """
        # P_world = R^T * (P_cam - tvec)
        p_world = rotation_matrix.T @ (p_cam - tvec)
        return p_world

    def _apply_custom_origin(self, p_world):
        """
        Desplaza las coordenadas para que el punto elegido actúe como el origen (0,0,0).
        """
        # Restar el offset físico definido por el usuario
        p_final = p_world - self.custom_origin_offset
        return p_final
