import numpy as np
import cv2
from data import config_manager as cfg


class PoseEstimation:
    def __init__(self, charuco_board: cv2.aruco.CharucoBoard) -> None:
        self.prev_circles = None
        self.mask_corners = None
        self.show_mask = False
        self.show_circles = False
        self.charuco_board = charuco_board

        camera = cfg.get("camera.json")
        self.camera_matrix = np.array(camera.get("matrix"))
        self.dist_coeffs = np.array(camera.get("distortion coefficients"))

        self.sphere_radius = 0.02
        self.board_cell_size = 0.03

    def get_sphere_pose(
        self,
        original_frame,
        drawn_frame=None,
        processed_frame=None,
        charuco_results=None,
        search_mask_corners=None,
    ):
        umat_frame = cv2.UMat(original_frame)
        umat_drawn_frame = cv2.UMat(
            drawn_frame) if drawn_frame is not None else umat_frame

        print("calcula pose de esfera")

        # sphere_results = self.circle_estimator.get_all_circles(
        #     umat_frame, umat_drawn_frame, search_mask_corners
        # )

        # if charuco_results is None or sphere_results is None:
        #     return drawn_frame

        # cam_pos, rvec, tvec, R = self.get_camera_pose(charuco_results)
        # if cam_pos is None:
        #     return drawn_frame

        # for color, datos in sphere_results.items():
        #     centro = datos["centro"]   # np.array([u, v])
        #     xyz = self.find_sphere_center_on_board(
        #         pixel_point=centro,
        #         c_world=cam_pos,
        #         rvec=rvec,
        #         R_cam=R,
        #         sphere_radius=self.sphere_radius,
        #     )
        #     if xyz is not None:
        #         print(f"[{color}] Posición 3D en tablero: {xyz}")

        return drawn_frame

    # ──────────────────────────────────────────────────────────────────────────
    # POSE DE LA CÁMARA
    # ──────────────────────────────────────────────────────────────────────────

    def get_camera_pose(self, charuco_results: dict):
        """Retorna la posición de la cámara en coordenadas del tablero.

        Args:
            charuco_results: diccionario con los resultados del tablero ChArUco.

        Returns:
            c_world : np.ndarray [X, Y, Z] — posición de la cámara en coords mundo.
                      c_world[0] → nadir X  (equivale al "400" hardcodeado en RBE3001)
                      c_world[1] → nadir Y  (equivale al "0"   hardcodeado en RBE3001)
                      c_world[2] → altura de la cámara sobre el tablero
            rvec    : vector de rotación (Rodrigues)
            tvec    : vector de traslación
            R       : matriz de rotación 3×3
        """
        charuco_corners = np.array(charuco_results["visible_corners"])
        charuco_ids = np.array(charuco_results["visible_ids"])

        success, rvec, tvec = cv2.aruco.estimatePoseCharucoBoard(
            charuco_corners, charuco_ids,
            self.charuco_board, self.camera_matrix, self.dist_coeffs,
            None, None,
        )
        if not success:
            return None, None, None, None

        R, _ = cv2.Rodrigues(rvec)
        # Centro óptico de la cámara en coordenadas mundo: C = -R^T · t
        c_world = (-R.T @ tvec).flatten()

        return c_world, rvec, tvec, R

    # ──────────────────────────────────────────────────────────────────────────
    # LOCALIZACIÓN 3D DE LA ESFERA — método de intersección rayo-plano
    # (más preciso que triángulos semejantes)
    # ──────────────────────────────────────────────────────────────────────────

    def find_sphere_center_on_board(
        self,
        pixel_point: tuple[float, float],
        c_world: np.ndarray,
        rvec: np.ndarray,
        R_cam: np.ndarray,
        sphere_radius: float,
    ) -> np.ndarray | None:
        """Halla el centro XYZ de una esfera usando intersección rayo-plano.

        La esfera reposa sobre el tablero (Z=0), por lo que su centro
        está en Z = sphere_radius. Se lanza un rayo desde la cámara
        hacia el centroide detectado y se intersecta con ese plano.

        Args:
            pixel_point  : (u, v) centro del círculo detectado en imagen.
            c_world      : Posición [X, Y, Z] de la cámara en coords del tablero.
                           Viene de get_camera_pose().
            rvec         : Vector de rotación (no usado aquí, se recibe por consistencia).
            R_cam        : Matriz de rotación 3×3 cámara→mundo.
            sphere_radius: Radio de la esfera en las mismas unidades que el tablero.

        Returns:
            np.ndarray [x, y, sphere_radius] en coords del tablero, o None si falla.

        Geometría:
            Un punto sobre el rayo: P = c_world + k * d_world
            Queremos Z = sphere_radius:
                sphere_radius = c_world[2] + k * d_world[2]
                k = (sphere_radius - c_world[2]) / d_world[2]
        """
        # 1. Eliminar distorsión y normalizar el punto imagen → rayo en cámara
