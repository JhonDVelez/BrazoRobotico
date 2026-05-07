import numpy as np
import cv2
from PyQt6.QtCore import QRunnable


class PoseEstimation(QRunnable):
    def __init__(self, results: dict, camera_matrix, dist_coeffs,
                 sphere_radius, custom_origin_offset, error_callback,
                 frame_id=None, pose_callback=None):
        """ Constructor de la tarea.
        """
        super().__init__()
        self.ellipse_results = results.get("ellipses") or {}
        self.charuco_results = results.get("charuco") or {}
        self.rvec = self.charuco_results.get("rvec")
        self.tvec = self.charuco_results.get("tvec")
        self.camera_matrix = np.asarray(camera_matrix, dtype=np.float64)
        self.dist_coeffs = np.asarray(dist_coeffs, dtype=np.float64)
        self.sphere_radius = sphere_radius
        self.error_callback = error_callback
        self.frame_id = frame_id
        self.pose_callback = pose_callback

        # El offset C que el usuario define como el nuevo (0,0)
        self.custom_origin_offset = np.array(
            custom_origin_offset, dtype=np.float64).reshape(3, 1)

    def run(self):
        """
        Función principal ejecutada por el QThreadPool.
        """
        try:
            if self.rvec is None or self.tvec is None:
                self.error_callback("Could not estimate ChArUco board pose.")
                return

            if not self.ellipse_results:
                return

            # R transforma coordenadas del tablero hacia coordenadas de cámara.
            rotation_matrix, _ = cv2.Rodrigues(self.rvec)

            final_poses = {}

            for color_name, sphere_data in self.ellipse_results.items():
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

            print(final_poses)

        except Exception as e:
            self.error_callback(str(e))

    def _calculate_sphere_board_coordinates(self, sphere_data, rotation_matrix):
        """
        Intersecta el rayo del centro 2D de la esfera con el plano paralelo al
        tablero donde debe estar el centro 3D de una esfera apoyada en él.
        """
        center = sphere_data.get("center")
        if center is None:
            raise ValueError("Sphere center is missing.")

        ray_cam = self._pixel_to_camera_ray(center)
        tvec = np.asarray(self.tvec, dtype=np.float64).reshape(3, 1)
        rotation_matrix = np.asarray(rotation_matrix, dtype=np.float64)

        camera_center_board = -rotation_matrix.T @ tvec
        ray_board = rotation_matrix.T @ ray_cam

        if abs(ray_board[2, 0]) < 1e-10:
            raise ValueError("Ray is parallel to the sphere support plane.")

        # La esfera está del lado visible del tablero: el mismo lado donde está la cámara.
        support_z = self.sphere_radius
        if camera_center_board[2, 0] < 0:
            support_z = -self.sphere_radius

        ray_scale = (support_z - camera_center_board[2, 0]) / ray_board[2, 0]
        return camera_center_board + ray_scale * ray_board

    def _pixel_to_camera_ray(self, center):
        """Convierte un pixel distorsionado en un rayo normalizado de cámara."""
        image_point = np.array([[center]], dtype=np.float64)
        undistorted = cv2.undistortPoints(
            image_point, self.camera_matrix, self.dist_coeffs)
        x_norm, y_norm = undistorted[0, 0]
        return np.array([[x_norm], [y_norm], [1.0]], dtype=np.float64)

    def _apply_custom_origin(self, p_world):
        """
        Desplaza las coordenadas para que el punto elegido actúe como el origen (0,0,0).
        """
        # Restar el offset físico definido por el usuario
        p_final = p_world - self.custom_origin_offset
        return p_final
