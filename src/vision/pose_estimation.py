import numpy as np
import cv2
from data import config_manager as cfg


class PoseEstimation:
    def __init__(self) -> None:
        self.prevCircles = None
        self.mask_corners = None
        self.show_mask = False
        self.show_circles = True
        self.show_mask_contour = True

        # Parámetros físicos conocidos
        self.sphere_radius_mm = 20.0
        self.board_cell_size_mm = 25.0
        self.chessboard_corners = None
        self.mask_corners = None

    def set_sphere_radius(self, radius_mm: float) -> None:
        self.sphere_radius_mm = float(radius_mm)

    def set_board_cell_size(self, cell_size_mm: float) -> None:
        self.board_cell_size_mm = float(cell_size_mm)

    def _estimate_board_pose(self, camera_matrix, dist_coeffs, grid_9x9):
        if grid_9x9 is None or grid_9x9.ndim != 3:
            return None, None
        rows, cols = grid_9x9.shape[:2]
        if rows < 2 or cols < 2:
            return None, None

        obj_pts = np.zeros((rows * cols, 3), dtype=np.float32)
        ij = np.indices((rows, cols), dtype=np.float32)
        obj_pts[:, 0] = (ij[1].reshape(-1) * self.board_cell_size_mm)
        obj_pts[:, 1] = (ij[0].reshape(-1) * self.board_cell_size_mm)

        img_pts = grid_9x9.reshape(-1, 2).astype(np.float32)
        try:
            success, rvec, tvec = cv2.solvePnP(
                obj_pts,
                img_pts,
                camera_matrix,
                dist_coeffs,
                flags=cv2.SOLVEPNP_ITERATIVE,
            )
        except Exception:
            return None, None

        if not success:
            return None, None

        return rvec, tvec

    def sphere_pose_estimation(self, img, pixel_u, pixel_v, radius_sphere, camera_matrix, dist_coeffs, rvec, tvec):
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
            # Prevención de división por cero (rayo paralelo al plano)
            return None

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

    def get_sphere_pose(self, original_img, drawn_img, processed_img, chessboard_corners, mask_corners):
        data = cfg.load("camera.json")
        camera_matrix = np.array(data.get("matrix", []), dtype=np.float64)
        dist_coeff = np.array(
            data.get("distortion coefficients", []), dtype=np.float64)

        self.chessboard_corners = chessboard_corners
        self.mask_corners = mask_corners

        drawn_img, self.prevCircles = self.get_circle_center(
            original_img, drawn_img, processed_img, mask_corners)

        pose_found = False
        rvec, tvec = None, None
        if self.chessboard_corners is not None:
            rvec, tvec = self._estimate_board_pose(
                camera_matrix, dist_coeff, self.chessboard_corners)
            if rvec is not None and tvec is not None:
                pose_found = True

        circle_pose_info = []
        for circ in self.prevCircles or []:
            x = float(circ["x"])
            y = float(circ["y"])
            r = float(circ["r"])
            color_name = circ["color"]

            contact_xy = None
            if pose_found:
                sphere_xy = self.sphere_pose_estimation(
                    drawn_img,
                    x,
                    y,
                    self.sphere_radius_mm,
                    camera_matrix,
                    dist_coeff,
                    rvec,
                    tvec,
                )
                if sphere_xy is not None:
                    contact_xy = (float(sphere_xy[0]), float(sphere_xy[1]))

            circle_pose_info.append({
                "x_px": x,
                "y_px": y,
                "radius_px": r,
                "color": color_name,
                "contact_xy_mm": contact_xy,
            })

            xi = int(round(x))
            yi = int(round(y))
            ri = int(round(r))
            if self.show_circles:
                cv2.circle(drawn_img, (xi, yi), 2, (0, 255, 0), -1)
                cv2.circle(drawn_img, (xi, yi), ri, (0, 255, 255), 2)
                label = f"{color_name}"
                if contact_xy is not None:
                    label = f"{color_name} ({contact_xy[0]:.0f},{contact_xy[1]:.0f})"
                cv2.putText(
                    drawn_img,
                    label,
                    (xi - ri, yi - ri - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45,
                    (255, 255, 255),
                    1,
                    cv2.LINE_AA,
                )

        self.last_circle_pose_info = circle_pose_info
        return drawn_img

    def _estimate_circle_color(self, img, x, y, r):
        if not np.isfinite(x) or not np.isfinite(y) or not np.isfinite(r) or r <= 0:
            return "unknown", (255, 255, 255)

        h, w = img.shape[:2]
        x0 = max(0, int(round(x - r)))
        x1 = min(w, int(round(x + r)))
        y0 = max(0, int(round(y - r)))
        y1 = min(h, int(round(y + r)))

        if x1 <= x0 or y1 <= y0:
            return "unknown", (255, 255, 255)

        patch = img[y0:y1, x0:x1]
        mask = np.zeros((patch.shape[0], patch.shape[1]), dtype=np.uint8)
        cv2.circle(mask, (int(round(x - x0)), int(round(y - y0))),
                   max(1, int(round(r))), 255, -1)
        mean_bgr = cv2.mean(patch, mask=mask)
        bgr_color = (int(mean_bgr[0]), int(mean_bgr[1]), int(mean_bgr[2]))

        hsv = cv2.cvtColor(np.uint8([[bgr_color]]), cv2.COLOR_BGR2HSV)[0][0]
        h_val, s_val, v_val = int(hsv[0]), int(hsv[1]), int(hsv[2])

        if v_val < 50:
            color_name = "negro"
        elif s_val < 40 and v_val > 100:
            color_name = "blanco"
        elif (h_val <= 10 or h_val >= 170):
            color_name = "rojo"
        elif 10 < h_val <= 30:
            color_name = "naranja"
        elif 30 < h_val <= 80:
            color_name = "verde"
        elif 80 < h_val <= 130:
            color_name = "azul"
        elif 130 < h_val <= 170:
            color_name = "violeta"
        else:
            color_name = "otro"

        return color_name, bgr_color

    def _smooth_tracked_circles(self, detections, alpha=0.4, max_dist=60):
        next_tracked = []
        used = set()

        for det in detections:
            x, y, r, color = det
            best_idx = None
            best_dist = float("inf")
            for i, prev in enumerate(self.prevCircles or []):
                if i in used:
                    continue
                dist = np.hypot(prev["x"] - x, prev["y"] - y)
                if dist < best_dist and dist < max_dist:
                    best_dist = dist
                    best_idx = i

            if best_idx is not None:
                used.add(best_idx)
                prev = self.prevCircles[best_idx]
                x_s = alpha * x + (1 - alpha) * prev["x"]
                y_s = alpha * y + (1 - alpha) * prev["y"]
                r_s = alpha * r + (1 - alpha) * prev["r"]
                age = prev.get("age", 1) + 1
            else:
                x_s, y_s, r_s = x, y, r
                age = 1

            next_tracked.append({
                "x": float(x_s),
                "y": float(y_s),
                "r": float(r_s),
                "color": color,
                "age": age,
            })

        # Keep old circles briefly if they disappear
        if self.prevCircles is not None:
            for i, prev in enumerate(self.prevCircles):
                if i in used:
                    continue
                if prev.get("age", 1) < 3:
                    next_tracked.append({
                        "x": prev["x"],
                        "y": prev["y"],
                        "r": prev["r"],
                        "color": prev["color"],
                        "age": prev.get("age", 1) + 1,
                    })

        self.prevCircles = next_tracked

    def get_circle_center(self, original_img, drawn_img, processed_img, mask_corners):
        try:
            blur = cv2.GaussianBlur(processed_img, (9, 9), 2)

            if mask_corners is not None:
                pts = np.array(mask_corners, dtype=np.int32)
                if pts.ndim == 2 and pts.shape[1] == 2:
                    pts = pts.reshape((-1, 1, 2))
                self.mask_corners = pts

            if self.mask_corners is not None and len(self.mask_corners) > 0:
                mask = np.zeros_like(blur)
                cv2.fillPoly(mask, [self.mask_corners], 255)
                masked_img = cv2.bitwise_and(blur, blur, mask=mask)
                if self.show_mask:
                    return masked_img, self.prevCircles
                if self.show_mask_contour:
                    cv2.polylines(drawn_img, [self.mask_corners], isClosed=True,
                                  color=(255, 255, 0), thickness=2)
            else:
                masked_img = blur
        except (cv2.error, TypeError, ValueError) as e:
            print(e)
            return drawn_img, self.prevCircles

        circles = cv2.HoughCircles(masked_img,
                                   cv2.HOUGH_GRADIENT,  # Método de búsqueda
                                   dp=1,  # Relación inversa de la resolución del acumulador y la imagen
                                   minDist=100,  # Distancia minima entre los centros de los circulos detectados
                                   param1=350,  # Sensibilidad entre mas alta menos circulos
                                   param2=35,  # Precision de la detección indica la cantidad de puntos de borde
                                   minRadius=10,
                                   maxRadius=250)

        detections = []
        if circles is not None:
            circles = np.around(circles[0]).astype(float)
            for (x, y, r) in circles:
                if not (np.isfinite(x) and np.isfinite(y) and np.isfinite(r) and r > 0):
                    continue
                if r > 500 or x < 0 or y < 0 or x > original_img.shape[1] or y > original_img.shape[0]:
                    continue
                color_name, _ = self._estimate_circle_color(
                    original_img, x, y, r)
                detections.append((float(x), float(y), float(r), color_name))

        self._smooth_tracked_circles(detections)

        return drawn_img, self.prevCircles
