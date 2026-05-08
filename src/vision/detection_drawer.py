import traceback
import numpy as np
import cv2
from PyQt6.QtCore import QRunnable
from data import config_manager as cfg


class DetectionDrawer(QRunnable):
    def __init__(self, frame: np.ndarray, results: dict, view: tuple, custom_origin: tuple, frame_callback, error_callback) -> None:
        super().__init__()
        self.frame = frame
        self.results = results
        self.charuco_view, self.ellipse_view = view
        self.custom_origin = custom_origin
        self.frame_callback = frame_callback
        self.error_callback = error_callback

        # Configuraciones guardadas de la cámara
        camera = cfg.load("camera.json")
        camera_resolution = camera.get("resolution", {})
        camera_width = camera_resolution.get("width", 1280)

        # Inicializa la configuración de escala automática de texto e indicadores del tablero.
        font_scale_base = 0.3
        thickness_base = 0.4
        self.base_font_scale = (camera_width / 1280) * font_scale_base
        self.font_scale = self.base_font_scale
        self.font_scale_min = 0.25
        self.font_scale_max = 0.6
        self.font = cv2.FONT_HERSHEY_DUPLEX
        self.thickness = max(
            0.6, int(self.base_font_scale * thickness_base / font_scale_base)
        )
        self.label_thickness = None
        self.dynamic_dot_size = None

    def run(self):
        if self.results is None:
            self.frame_callback(self.frame)
            return

        grid_results = self.results.get("charuco", None)
        sphere_results = self.results.get("ellipses", None)
        pose_results = self.results.get("poses", None) or {}

        frame_out = self.frame.copy()

        # print(
        #     f"charuco: {grid_results is not None}\tellipses: {ellipses_results is not None}")

        # Dibujar ChArUco
        if grid_results is not None and self.charuco_view:
            try:
                frame_out = self._draw_grid(frame_out, grid_results)
            except Exception:
                self.error_callback(
                    f"Error al dibujar ChArUco: {traceback.format_exc()} (DetectionDrawer)")

        # Dibujar esferas
        if sphere_results is not None and self.ellipse_view:
            try:
                frame_out = self._draw_spheres(
                    frame_out, sphere_results, pose_results)
            except Exception:
                self.error_callback(
                    f"Error al dibujar esferas: {traceback.format_exc()} (DetectionDrawer)")

        # Siempre se entrega el frame, con lo que haya podido dibujarse
        self.frame_callback(frame_out)

    def _draw_grid(self, frame, results):
        """ Dibuja la red final obtenida luego de la extrapolación sobre la imagen de referencia
            del tablero de ajedrez.
        """
        cols, rows = results["grid_shape"]
        corners = results["unified_corners"].reshape(rows, cols, 2)
        self._get_dynamic_font_scale(corners)

        # Corners interiores visibles → verde
        for corner in results["visible_corners"]:
            pt = tuple(corner[0].astype(int))
            cv2.circle(frame, pt, self.dynamic_dot_size, (0, 230, 0), -1)

        # Corners interiores ocultos → naranja
        for corner in results["estimated_interior"]:
            pt = tuple(corner[0].astype(int))
            cv2.circle(frame, pt, self.dynamic_dot_size,
                       (0, 140, 255), -1)

        # Corners exteriores estimados → azul
        for corner in results["exterior_corners"]:
            pt = tuple(corner[0].astype(int))
            cv2.circle(frame, pt, self.dynamic_dot_size, (220, 60, 0), -1)

        physical_corners = results["physical_corners"]
        for corner, phy_corner in zip(corners.reshape(-1, 1, 2), physical_corners.reshape(-1, 1, 2)):
            corner = corner[0]
            phy_corner = phy_corner[0]
            adjusted_x = phy_corner[1] - self.custom_origin[1]
            adjusted_y = phy_corner[0] - self.custom_origin[0]
            cv2.putText(
                frame,
                f"[{adjusted_y:.1f},{adjusted_x:.1f}]",
                tuple(corner.astype(int) + [-25, 15]),
                cv2.FONT_HERSHEY_COMPLEX_SMALL,
                self.font_scale,
                (0, 0, 255),
                self.label_thickness,
                cv2.LINE_AA
            )

            # Leyenda
            # legends = [
            #     ((0, 230, 0),   "Interior visible"),
            #     ((0, 140, 255), "Interior oculto"),
            #     ((220, 60, 0),  "Exterior estimado"),
            # ]
            # for i, (color, label) in enumerate(legends):
            #     y = 25 + i * 22
            #     cv2.circle(vis, (15, y), 6, color, -1)
            #     cv2.putText(vis, label, (26, y + 5),
            #                 cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1, cv2.LINE_AA)

        return frame

    def _draw_spheres(self, frame, sphere_results: dict[str, dict], pose_results: dict):
        for color, datos in sphere_results.items():
            c = datos.get("center")
            radius = datos.get("radius") or datos.get("area_radius")
            contour = datos.get("contour")

            if c is None or radius is None:
                continue

            center = (int(round(c[0])), int(round(c[1])))
            radius = int(round(radius))

            try:
                if contour is not None:
                    contour = np.asarray(contour, dtype=np.int32)
                    cv2.drawContours(frame, [contour], -1, (0, 220, 255), 1)

                cv2.circle(frame, center, radius, (0, 255, 0), 2)
                cv2.circle(frame, center, 3, (0, 0, 255), -1)

                position = datos.get("position") or pose_results.get(color)
                label_lines = [str(color)]
                if position is not None and len(position) >= 3:
                    label_lines.extend([
                        f"X={position[0]:.3f} Y={position[1]:.3f}",
                        f"Z={-position[2]:.3f} mm",
                    ])

                label_x = center[0] + radius + 8
                label_y = center[1] - max(0, radius // 2)
                if label_x > frame.shape[1] - 190:
                    label_x = max(5, center[0] - radius - 185)
                label_y = max(18, label_y)
                self._draw_text_lines(frame, label_lines, (label_x, label_y))

            except Exception as e:
                print(f"[WARN] Error dibujando esfera: {e}")
                continue

        return frame

    def _draw_text_lines(self, frame, lines: list[str], origin: tuple[int, int]):
        x, y = origin
        line_height = 17
        for index, line in enumerate(lines):
            text_origin = (x, y + index * line_height)
            cv2.putText(frame, line, text_origin, cv2.FONT_HERSHEY_SIMPLEX,
                        0.45, (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(frame, line, text_origin, cv2.FONT_HERSHEY_SIMPLEX,
                        0.45, (255, 255, 255), 1, cv2.LINE_AA)

    def _get_dynamic_font_scale(self, corners: np.ndarray) -> float:
        """Calcula la escala de fuente basada en ancho de celda medida en pixeles.

        Se hacen dos mediciones en filas opuestas para estimar el ancho de celda y
        se promedian. Se aplican límites mínimo y máximo preestablecidos.
        """
        if corners is None:
            return self.base_font_scale

        rows, cols = corners.shape[:2]
        if rows < 2 or cols < 2:
            return self.base_font_scale

        try:
            top_left = corners[0, 0].astype(float)
            top_right = corners[0, cols - 1].astype(float)
            bottom_left = corners[rows - 1, 0].astype(float)
            bottom_right = corners[rows - 1, cols - 1].astype(float)
        except Exception:
            return self.base_font_scale

        width_top = np.linalg.norm(top_right - top_left) / max(1, cols - 1)
        width_bottom = np.linalg.norm(
            bottom_right - bottom_left) / max(1, cols - 1)
        avg_cell_width = (width_top + width_bottom) / 2.0

        if avg_cell_width <= 0:
            return self.base_font_scale

        dynamic_scale = (avg_cell_width / 30.0) * self.base_font_scale
        self.font_scale = float(
            np.clip(dynamic_scale, self.font_scale_min, self.font_scale_max))

        self.label_thickness = int(max(
            1, round(self.thickness * self.font_scale /
                     max(0.01, self.base_font_scale)))
        )
        self.dynamic_dot_size = int(self.font_scale * 8)
