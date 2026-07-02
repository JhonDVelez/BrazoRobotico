"""
Módulo de dibujo de resultados de detección sobre el frame.

Proporciona DetectionDrawer, un QRunnable que recibe los resultados
de detección de ChArUco y esferas y los dibuja sobre el frame antes
de mostrarlo en la interfaz.

Conexiones:
    - Ejecutado por un QThreadPool.
    - Recibe resultados de ChArUcoDetection y CircleDetection.
    - Entrega el frame final a traves de `frame_callback`.
"""

import numpy as np
import cv2
from PyQt6.QtCore import QRunnable


class DetectionDrawer(QRunnable):
    """Tarea ejecutable para dibujar resultados de detección sobre el frame.

    Dibuja la malla del tablero ChArUco (puntos interiores, ocultos y
    exteriores con coordenadas físicas) y las esferas detectadas
    (contorno, centro, radio y posicion 3D).

    Args:
        frame (np.ndarray): Frame original sobre el que dibujar.
        results (dict): Resultados combinados de charuco y circles.
        view (tuple): (charuco_view, circle_view) flags de visibilidad.
        custom_origin (tuple): Offset del origen personalizado en mm.
        frame_callback (callable): Función para devolver el frame final.
        error_callback (callable): Función para reportar errores.
    """

    def __init__(self, frame: np.ndarray, results: dict, view: tuple, custom_origin: tuple, camera_width: int, frame_callback, error_callback) -> None:
        super().__init__()
        self.frame = frame
        self.results = results
        self.charuco_view, self.circle_view = view
        self.custom_origin = custom_origin
        self.frame_callback = frame_callback
        self.error_callback = error_callback

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
        """Ejecuta el dibujo de todos los resultados sobre el frame.

        Dibuja la malla ChArUco y las esferas segun las flags de
        visibilidad, y entrega el frame final a traves del callback.
        """
        if self.results is None:
            self.frame_callback(self.frame)
            return

        grid_results = self.results.get("charuco", None)
        sphere_results = self.results.get("circles", None)
        pose_results = self.results.get("poses", None) or {}

        frame_out = self.frame.copy()

        if grid_results is not None and self.charuco_view:
            try:
                frame_out = self._draw_grid(frame_out, grid_results)
            except (cv2.error, KeyError, ValueError) as e:
                self.error_callback(
                    f"Error al dibujar ChArUco: {type(e).__name__}: {e} (DetectionDrawer)")

        if sphere_results is not None and self.circle_view:
            try:
                frame_out = self._draw_spheres(
                    frame_out, sphere_results, pose_results)
            except (cv2.error, KeyError, ValueError) as e:
                self.error_callback(
                    f"Error al dibujar esferas: {type(e).__name__}: {e} (DetectionDrawer)")

        self.frame_callback(frame_out)

    def _draw_grid(self, frame, results):
        """Dibuja la malla extrapolada del tablero ChArUco sobre la imagen.

        Muestra los puntos interiores visibles (verde), interiores
        ocultos (naranja) y exteriores estimados (azul), junto con
        las coordenadas físicas en milímetros de cada punto.

        Args:
            frame: Frame sobre el que dibujar.
            results: Resultados de detección de ChArUco.

        Returns:
            np.ndarray: Frame con la malla dibujada.
        """
        cols, rows = results["grid_shape"]
        corners = results["unified_corners"].reshape(rows, cols, 2)
        self._get_dynamic_font_scale(corners)

        for corner in results["visible_corners"]:
            pt = tuple(corner[0].astype(int))
            cv2.circle(frame, pt, self.dynamic_dot_size, (0, 230, 0), -1)

        for corner in results["estimated_interior"]:
            pt = tuple(corner[0].astype(int))
            cv2.circle(frame, pt, self.dynamic_dot_size,
                       (0, 140, 255), -1)

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

        return frame

    def _draw_spheres(self, frame, sphere_results: dict[str, dict], pose_results: dict):
        """Dibuja las esferas detectadas sobre el frame.

        Muestra el contorno, círculo circunscrito, centro y etiquetas
        con el color y la posición 3D de cada esfera.

        Args:
            frame: Frame sobre el que dibujar.
            sphere_results (dict): Resultados de detección de esferas.
            pose_results (dict): Resultados de estimación de pose.

        Returns:
            np.ndarray: Frame con las esferas dibujadas.
        """
        for color, datos in sphere_results.items():
            c = datos.get("center")
            radius = datos.get("radius")
            contour = datos.get("contour")

            if c is None or radius is None:
                continue

            center = (int(round(c[0])), int(round(c[1])))
            radius = int(round(radius))

            try:
                if contour is not None:
                    contour = np.asarray(contour.get(), dtype=np.int32)
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

            except (cv2.error, ValueError, AttributeError) as e:
                print(f"[WARN] Error dibujando esfera '{color}' ({type(e).__name__}): {e}")
                continue

        return frame

    def _draw_text_lines(self, frame, lines: list[str], origin: tuple[int, int]):
        """Dibuja múltiples líneas de texto con borde negro y relleno blanco.

        Args:
            frame: Frame sobre el que dibujar.
            lines (list[str]): Líneas de texto a mostrar.
            origin (tuple): Coordenadas (x, y) de inicio del texto.
        """
        x, y = origin
        line_height = 17
        for index, line in enumerate(lines):
            text_origin = (x, y + index * line_height)
            cv2.putText(frame, line, text_origin, cv2.FONT_HERSHEY_SIMPLEX,
                        0.45, (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(frame, line, text_origin, cv2.FONT_HERSHEY_SIMPLEX,
                        0.45, (255, 255, 255), 1, cv2.LINE_AA)

    def _get_dynamic_font_scale(self, corners: np.ndarray) -> float:
        """Calcula la escala de fuente basada en el ancho de celda medido en píxeles.

        Mide el ancho de celda en dos filas opuestas (superior e inferior)
        y calcula un promedio para ajustar la escala del texto de forma
        dinámica según la distancia de la cámara al tablero.

        Args:
            corners (np.ndarray): Esquinas de la malla con forma (rows, cols, 2).

        Returns:
            float: Escala de fuente ajustada dinámicamente.
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
        except (IndexError, ValueError) as e:
            print(f"[DEBUG] Error calculando escala de fuente dinámica ({type(e).__name__}): {e}")
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
