import traceback
import numpy as np
import cv2
from PyQt6.QtCore import QRunnable
from data import config_manager as cfg


class DetectionDrawer(QRunnable):
    def __init__(self, frame: cv2.UMat, results: dict, view: tuple, frame_callback, error_callback) -> None:
        super().__init__()
        self.frame = frame.get().copy()
        self.results = results
        self.charuco_view, self.ellipse_view = view
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
        ellipses_results = self.results.get("ellipses", None)

        frame_out = self.frame.copy()

        # print(
        #     f"charuco: {grid_results is not None}\tellipses: {ellipses_results is not None}")

        # Dibujar ChArUco — fallo aislado
        if grid_results is not None and self.charuco_view:
            try:
                frame_out = self._draw_grid(frame_out, grid_results)
            except Exception:
                self.error_callback(
                    f"Error al dibujar ChArUco: {traceback.format_exc()} (DetectionDrawer)")

        # Dibujar elipses — fallo aislado
        if ellipses_results is not None and self.ellipse_view:
            try:
                frame_out = self._draw_ellipse(frame_out, ellipses_results)
            except Exception:
                self.error_callback(
                    f"Error al dibujar elipses: {traceback.format_exc()} (DetectionDrawer)")

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
            cv2.putText(
                frame,
                f"[{phy_corner[1]},{phy_corner[0]}]",
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

    def _draw_ellipse(self, frame, ellipse_results: dict[str, dict]):
        for color, datos in ellipse_results.items():
            ellipse = datos.get("ellipse")
            c = datos.get("center")
            a = datos.get("major")

            # Validaciones robustas
            if ellipse is None:
                continue

            if c is None or a is None:
                continue

            try:
                # Asegurar tipos correctos
                center, axes, angle = ellipse

                center = (int(center[0]), int(center[1]))
                axes = (int(axes[0]), int(axes[1]))
                angle = float(angle)

                cv2.ellipse(frame, (center, axes, angle), (0, 255, 0), 2)

                cv2.putText(
                    frame,
                    str(color),
                    (int(c[0] - 20), int(c[1] - a - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA
                )

            except Exception as e:
                print(f"[WARN] Error dibujando elipse: {e}")
                continue

        return frame

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
