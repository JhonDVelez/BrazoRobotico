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

        self.sphere_radius_mm = 0.0
        self.board_cell_size_mm = 0.0

    def set_sphere_radius(self, radius_mm: float) -> None:
        self.sphere_radius_mm = float(radius_mm)

    def set_board_cell_size(self, cell_size_mm: float) -> None:
        self.board_cell_size_mm = float(cell_size_mm)

    # ──────────────────────────────────────────────────────────────────────────
    # POSE PRINCIPAL
    # ──────────────────────────────────────────────────────────────────────────

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

        if charuco_results is None or sphere_results is None:
            return drawn_frame

        cam_pos, rvec, tvec, R = self.get_camera_pose(charuco_results)
        if cam_pos is None:
            return drawn_frame

        for color, datos in sphere_results.items():
            centro = datos["centro"]   # np.array([u, v])
            xyz = self.find_sphere_center_on_board(
                pixel_point=centro,
                c_world=cam_pos,
                rvec=rvec,
                R_cam=R,
                sphere_radius=self.sphere_radius_mm,
            )
            if xyz is not None:
                print(f"[{color}] Posición 3D en tablero: {xyz}")

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
        punto_np = np.array([[pixel_point]], dtype=np.float32)
        punto_undist = cv2.undistortPoints(
            punto_np, self.camera_matrix, self.dist_coeffs
        )
        x_prime, y_prime = punto_undist[0, 0]

        # Dirección del rayo en coordenadas de cámara (vector normalizado)
        d_cam = np.array([x_prime, y_prime, 1.0])

        # 2. Rotar el rayo al sistema de coordenadas del tablero
        d_world = (R_cam.T @ d_cam).flatten()

        # 3. Verificar que el rayo no sea paralelo al plano Z=sphere_radius
        if abs(d_world[2]) < 1e-9:
            print(
                "[WARN] El rayo es paralelo al plano de la esfera. No hay intersección.")
            return None

        # 4. Parámetro k de la intersección con el plano Z = sphere_radius
        k = (sphere_radius - c_world[2]) / d_world[2]

        if k < 0:
            print("[WARN] La intersección está detrás de la cámara.")
            return None

        # 5. Punto 3D en coordenadas del tablero
        x_sphere = c_world[0] + k * d_world[0]
        y_sphere = c_world[1] + k * d_world[1]

        return np.array([x_sphere, y_sphere, sphere_radius])

    # ──────────────────────────────────────────────────────────────────────────
    # MÉTODO ALTERNATIVO — triángulos semejantes (equivale al RBE3001 original)
    # Útil si ya tienes world_points 2D de otra fuente y quieres corregirlos.
    # ──────────────────────────────────────────────────────────────────────────

    def world_points_to_object_points(
        self,
        world_points: np.ndarray,
        c_world: np.ndarray,
        object_height: float,
    ) -> np.ndarray:
        """Corrección de paralaje por triángulos semejantes.

        Equivale a worldPointsToObjectPoints() del proyecto RBE3001 (MATLAB).
        Usar cuando ya tienes puntos 2D proyectados en Z=0 y quieres corregirlos.

        Las ecuaciones del paper (Fig. 12) son:
            d   = D · (h / H)           ← corrección total
            dx  = d · (Dx / D)  =  (h/H) · Dx
            dy  = d · (Dy / D)  =  (h/H) · Dy

        donde:
            H  = c_world[2]         altura de la cámara
            h  = object_height      altura de la esfera
            Dx = nadir_x - point_x  componente X del vector nadir→punto
            Dy = nadir_y - point_y  componente Y del vector nadir→punto
            D  = sqrt(Dx²+Dy²)      distancia horizontal nadir→punto

        Args:
            world_points  : np.ndarray (N, 2) — puntos 2D en el plano Z=0.
            c_world       : np.ndarray [nadir_x, nadir_y, cam_height].
                            Viene directamente de get_camera_pose().
            object_height : float — altura del objeto (radio de la esfera).

        Returns:
            np.ndarray (N, 3) — posición corregida [X, Y, object_height] por fila.
        """
        world_points = np.asarray(world_points, dtype=float)

        cam_height = c_world[2]   # H
        nadir_x = c_world[0]   # equivale al "400" hardcodeado en RBE3001
        nadir_y = c_world[1]   # equivale al "0"   hardcodeado en RBE3001

        # Vectores desde cada punto hacia el nadir de la cámara
        Dx = nadir_x - world_points[:, 0]   # componente X
        Dy = nadir_y - world_points[:, 1]   # componente Y

        # Escala de corrección: h/H
        scale = object_height / cam_height

        # dx = scale·Dx  ;  dy = scale·Dy  (triángulos semejantes simplificados)
        corrected_x = world_points[:, 0] + scale * Dx
        corrected_y = world_points[:, 1] + scale * Dy
        z_col = np.full(len(world_points), object_height)

        # np.column_stack une vectores 1D como columnas de una matriz 2D:
        # [corrected_x[0], corrected_y[0], z_col[0]]   ← punto 0
        # [corrected_x[1], corrected_y[1], z_col[1]]   ← punto 1  ...
        return np.column_stack([corrected_x, corrected_y, z_col])
