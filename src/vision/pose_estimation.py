import numpy as np
import cv2
from data import config_manager as cfg
from vision.circle_estimation import CircleEstimation


class PoseEstimation:
    def __init__(self, charuco_board: cv2.aruco.CharucoBoard) -> None:
        self.prev_circles = None
        self.mask_corners = None
        self.show_mask = False
        self.show_circles = False
        self.charuco_board = charuco_board

        self.circle_estimator = CircleEstimation()

        camera = cfg.get("camera.json")
        self.camera_matrix = np.array(camera.get("matrix"))
        self.dist_coeffs = np.array(camera.get("distortion coefficients"))

    def set_sphere_radius(self, radius_mm: float) -> None:
        self.sphere_radius_mm = float(radius_mm)

    def set_board_cell_size(self, cell_size_mm: float) -> None:
        self.board_cell_size_mm = float(cell_size_mm)

    def get_sphere_pose(self, original_frame, drawn_frame=None, processed_frame=None, charuco_results=None, search_mask_corners=None):
        umat_frame = cv2.UMat(original_frame)
        if drawn_frame is not None:
            umat_drawn_frame = cv2.UMat(drawn_frame)
        else:
            umat_drawn_frame = umat_frame

        sphere_results = self.circle_estimator.get_all_circles(
            umat_frame, umat_drawn_frame, search_mask_corners)
        if sphere_results is not None and self.show_circles:
            self.circle_estimator._draw_detection(drawn_frame, sphere_results)

        if charuco_results is not None:
            cam_pos, rvec, tvec, R = self.get_camera_pose(charuco_results)
            if cam_pos is not None and sphere_results is not None:
                for color, (centro, radio, area) in sphere_results.items():
                    sphere = sphere_results[color]
                    xyz_sphere_position = self.find_sphere_center_on_board(
                        sphere[centro], cam_pos, rvec, R, 0.03)
                    print(xyz_sphere_position)
        return drawn_frame

    def get_camera_pose(self, charuco_results: dict):
        """ Retorna la posición de la cámara en coordenadas del tablero.
            Llámala después de detect_corners si tienes calibración de cámara.

        Args:
            charuco_results (dict): diccionario con los resultados obtenidos del tablero

        Returns:
            c_world: posición de la cámara XYZ respecto al plano
        """
        charuco_corners = np.array(charuco_results["visible_corners"])
        charuco_ids = np.array(charuco_results["visible_ids"])
        success, rvec, tvec = cv2.aruco.estimatePoseCharucoBoard(
            charuco_corners, charuco_ids,
            self.charuco_board, self.camera_matrix, self.dist_coeffs,
            None, None
        )
        if not success:
            return None, None, None, None

        R, _ = cv2.Rodrigues(rvec)
        # Centro óptico de la cámara en el mundo
        c_world = (-R.T @ tvec).flatten()  # Posición XYZ en coords del tablero
        # cam_pos = np.array([cam_pos[1], cam_pos[0], -cam_pos[2]])
        return c_world, rvec, tvec, R

    def find_sphere_center_on_board(
        self,
        pixel_point: tuple[float, float],
        c_world: np.ndarray,
        rvec: np.ndarray,
        R_cam: np.ndarray,  # Matriz de rotacion 3x3
        sphere_radius: float = 0.03,
    ) -> np.ndarray | None:
        """
        Halla el centro XY de una esfera sobre el tablero (Z=0),
        conociendo el radio y el pixel del círculo detectado.

        Args:
            pixel_point:   (u, v) centro del círculo detectado en imagen
            c_mundo:       Posición de la cámara en coords del tablero
            rvec:          Vector de rotación de la pose del tablero
            R_cam:         Matriz de rotación de la camara
            sphere_radius: Radio de la esfera (mismas unidades que squareLength)

        Returns:
            np.ndarray [x, y, z=radio] en coords del tablero, o None si falla
        """
        # Rayo de vision hacia la esfera
        punto_np = np.array([[pixel_point]], dtype=np.float32)
        puntos_undistorted = cv2.undistortPoints(
            punto_np, self.camera_matrix, self.dist_coeffs)
        x_prime, y_prime = puntos_undistorted[0, 0]
        # x_prime, y_prime
        # Vector de dirección del rayo en el sistema de coordenadas de la cámara
        d_cam = np.array([x_prime, y_prime, 1])

        # Transformar el rayo al sistema del tablero ChArUco
        d_mundo = (R_cam.T @ d_cam).flatten()

        # Calcular la intersección
        # Ecuación parametrica de una linea recta en 3D
        # P = C_mundo + k @ d_mundo
        # donde k es la distancia a lo largo del rayo (escalar)
        # Z_esfera = r = C_mundo,z + k @ d_mundo,z
        # k = (r - C_mundo,z) / d_mundo,z

        k = (sphere_radius - c_world[2]) / d_mundo[2]

        x_sphere = c_world[0] + k * d_mundo[0]
        y_sphere = c_world[1] + k * d_mundo[1]

        # [x, y, radio] en coords del tablero
        return np.array([x_sphere, y_sphere, sphere_radius])
