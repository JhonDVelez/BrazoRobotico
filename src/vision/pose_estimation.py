import numpy as np
import cv2
from data import config_manager as cfg
from vision.circle_estimation import CircleEstimation


class PoseEstimation:
    # Radio de la esfera en metros
    SPHERE_RADIUS_M = 0.02
    # Tamaño de celda del tablero ChArUco en metros
    BOARD_CELL_SIZE_M = 0.03

    def __init__(self, charuco_board: cv2.aruco.CharucoBoard) -> None:
        self.prev_circles = None
        self.mask_corners = None
        self.show_mask = False
        self.show_circles = False
        self.charuco_board = charuco_board

        self.circle_estimator = CircleEstimation()

        camera = cfg.get("camera.json")
        self.camera_matrix = np.array(camera.get("matrix"), dtype=np.float64)
        self.dist_coeffs = np.array(
            camera.get("distortion coefficients"), dtype=np.float64
        )

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

        sphere_results = self.circle_estimator.get_all_circles(
            umat_frame, umat_drawn_frame, search_mask_corners
        )
        if sphere_results is not None and self.show_circles:
            self.circle_estimator._draw_detection(drawn_frame, sphere_results)

        # --- LOCALIZACIÓN CON CORRECCIÓN GEOMÉTRICA (Triángulos Semejantes) ---
        if sphere_results is not None and charuco_results is not None and "physical_corners" in charuco_results:
            # 1. Preparar puntos: píxeles y sus coordenadas físicas (en mm)
            img_pts = charuco_results["unified_corners"].astype(np.float32)
            phys_pts_2d = charuco_results["physical_corners"].reshape(
                -1, 2).astype(np.float32)

            # Calcular la homografía directa de píxeles a milímetros en el plano Z=0
            H_mm, _ = cv2.findHomography(img_pts, phys_pts_2d)

            # 2. Calcular la pose de la cámara para obtener su altura (H) y posición (Cx, Cy)
            obj_pts = np.hstack((phys_pts_2d, np.zeros(
                (phys_pts_2d.shape[0], 1)))).astype(np.float32)
            dist_zeros = np.zeros((4, 1))  # El frame ya tiene undistort previo

            success, rvec, tvec = cv2.solvePnP(
                obj_pts, img_pts, self.camera_matrix, dist_zeros, flags=cv2.SOLVEPNP_ITERATIVE
            )

            if success and H_mm is not None:
                # Obtener matriz de rotación e invertirla para ubicar la cámara en el mundo
                R, _ = cv2.Rodrigues(rvec)
                camera_pos_world = -np.dot(R.T, tvec)

                Cx = float(camera_pos_world[0][0])
                Cy = float(camera_pos_world[1][0])
                Cz = float(camera_pos_world[2][0])  # Altura de la cámara (H)

                h_esfera = self.SPHERE_RADIUS_M * \
                    1000.0  # Altura de la bola (h) en mm

                for color, data in sphere_results.items():
                    u, v = data["centro"]

                    # A. Proyectar el píxel al plano xy del tablero (genera error de proyección)
                    pt_px = np.array([[[float(u), float(v)]]])
                    pt_plano = cv2.perspectiveTransform(pt_px, H_mm)
                    Ppx = pt_plano[0][0][0]
                    Ppy = pt_plano[0][0][1]

                    # B. Calcular posición real por triángulos semejantes
                    Dx = Ppx - Cx
                    Dy = Ppy - Cy
                    D = np.hypot(Dx, Dy)

                    if D != 0:
                        # d = D * (h / H)
                        d = D * (h_esfera / Cz)

                        # Componentes del offset (dx, dy)
                        dx = d * (Dx / D)
                        dy = d * (Dy / D)
                    else:
                        dx, dy = 0, 0

                    # Aplicar los offsets para acercar la coordenada real a la cámara
                    Ptx = Ppx - dx
                    Pty = Ppy - dy

                    data["posicion_xy_mm"] = (Ptx, Pty)

                    if drawn_frame is not None:
                        texto_pos = f"X:{int(Ptx)} Y:{int(Pty)}"
                        cv2.putText(
                            drawn_frame, texto_pos,
                            (int(u) - 40, int(v) + int(data["radio"]) + 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 153, 255), 2
                        )

        return drawn_frame
