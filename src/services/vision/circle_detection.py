"""
Módulo de detección de esferas de color mediante segmentación HSV.

Proporciona CircleDetection, un QRunnable que procesa un frame y
detecta las esferas más grandes de cada color configurado, devolviendo
su centro, radio, área y circularidad.

Conexiones:
    - Ejecutado por un QThreadPool.
    - Reporta resultados a traves de `detection_callback`.
    - Reporta errores a traves de `error_callback`.
"""

from PyQt6.QtCore import QRunnable
import numpy as np
import cv2


class CircleDetection(QRunnable):
    """Tarea ejecutable para detectar esferas de color por segmentación HSV.

    Detecta la esfera más grande de cada color en el frame usando
    rangos HSV predefinidos o personalizados. Aplica operaciones
    morfológicas para limpiar la máscara y calcula centro, radio,
    área y circularidad de cada objeto detectado.

    Attributes:
        COLORES (dict): Rangos HSV por defecto para cada color.
    """

    COLORES = {
        "amarillo": (20, 100, 100, 30, 255, 255),
        "verde":    (40, 70, 70, 80, 255, 255),
        "azul":     (100, 150, 50, 130, 255, 255),
        "naranja":  (5, 150, 150, 15, 255, 255),
        "morado":   (130, 94, 117, 180, 255, 255),
    }

    def __init__(self, frame_umat: cv2.UMat, frame_id: int, roi: np.ndarray | None, hsv_colors: dict | None, detection_callback, error_callback) -> None:
        """
        Args:
            frame_umat (cv2.UMat): Frame como UMat para procesamiento OpenCL.
            frame_id (int): Identificador único del frame.
            roi (np.ndarray): Polígono de región de interés (máscara).
            hsv_colors (dict): Rangos HSV personalizados o None para usar predeterminados.
            detection_callback (callable): Función para reportar resultados.
            error_callback (callable): Función para reportar errores.
        """
        super().__init__()
        self.show_geometry = False
        self.frame_umat = frame_umat
        self.frame_id = frame_id
        self.roi = roi
        self.hsv_colors = hsv_colors or self.COLORES
        self.detection_callback = detection_callback
        self.error_callback = error_callback

    def run(self):
        """Detecta la esfera más grande de cada color en el frame.

        Aplica máscara de ROI si está definida, convierte a HSV,
        segmenta por rango de color, aplica morfología, encuentra
        contornos y calcula propiedades geométricas.

        Callback:
            dict con forma:
            {
                "amarillo": {"center": (x, y), "radius": float, "area": float},
                ...
            }
            Solo incluye colores encontrados.
        """
        try:
            if self.roi is not None:
                mask = cv2.cvtColor(cv2.multiply(
                    self.frame_umat, 0), cv2.COLOR_BGR2GRAY)
                roi_umat = cv2.UMat(self.roi.astype('int32'))
                cv2.drawContours(mask, [roi_umat], 0,
                                 (255, 255, 255, 1), thickness=-1)
                masked_frame = cv2.bitwise_and(
                    self.frame_umat, self.frame_umat, mask=mask)
            else:
                masked_frame = self.frame_umat
            hsv = cv2.cvtColor(masked_frame, cv2.COLOR_BGR2HSV)

            resultados = {}

            for nombre_color, (hmin, smin, vmin, hmax, smax, vmax) in self.hsv_colors.items():
                lower = cv2.UMat(np.array([hmin, smin, vmin], dtype="uint8"))
                upper = cv2.UMat(np.array([hmax, smax, vmax], dtype="uint8"))
                mask = cv2.inRange(hsv, lower, upper, None)

                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
                mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
                mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

                contours, _ = cv2.findContours(
                    mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )

                if contours:
                    largest_contour = max(contours, key=cv2.contourArea)
                    area = cv2.contourArea(largest_contour)

                    if area > 500:
                        moments = cv2.moments(largest_contour)
                        if abs(moments["m00"]) < 1e-9:
                            continue

                        center = (
                            moments["m10"] / moments["m00"],
                            moments["m01"] / moments["m00"],
                        )
                        enclosing_center, enclosing_radius = cv2.minEnclosingCircle(
                            largest_contour)
                        area_radius = float(np.sqrt(area / np.pi))
                        perimeter = cv2.arcLength(largest_contour, True)
                        circularity = 0.0
                        if perimeter > 1e-9:
                            circularity = float(
                                4.0 * np.pi * area / (perimeter * perimeter))

                        circle = None
                        if len(largest_contour.get()) >= 5:
                            circle = cv2.fitEllipse(largest_contour)

                        resultados[nombre_color] = {
                            "circle": circle,
                            "center": center,
                            # "circle_center": enclosing_center,
                            "radius": float(enclosing_radius),
                            # "area_radius": area_radius,
                            # "circularity": circularity,
                            # "area":   area,
                            # "contour": largest_contour
                        }
            self.detection_callback(
                self.frame_id, resultados if resultados else None)
        except (cv2.error, ValueError, AttributeError) as e:
            self.error_callback(
                f"Error al detectar esfera: {type(e).__name__}: {e} (CircleDetection)")
