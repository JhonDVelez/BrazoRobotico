from PyQt6.QtCore import QRunnable
import numpy as np
import cv2


class EllipseDetection(QRunnable):
    COLORES = {
        # Formato: (H_min, S_min, V_min, H_max, S_max, V_max)
        "amarillo": (20, 100, 100, 30, 255, 255),
        "verde":    (40, 70, 70, 80, 255, 255),
        "azul":     (100, 150, 50, 130, 255, 255),
        "naranja":  (5, 150, 150, 15, 255, 255),
        "morado":   (130, 50, 50, 160, 255, 255),
    }

    def __init__(self, frame_umat: cv2.UMat, frame_id: int, roi: np.ndarray, detection_callback, error_callback) -> None:
        super().__init__()
        self.show_geometry = False
        self.frame_umat = frame_umat
        self.frame_id = frame_id
        self.roi = roi
        self.detection_callback = detection_callback
        self.error_callback = error_callback

    def run(self):
        """Detecta la esfera más grande de cada color en el frame.

        Callback:
            dict con forma:
            {
                "amarillo": {"center": (x, y), "radius": float, "area": float},
                ...
            }
            Solo incluye colores encontrados.
        """
        try:
            frame = self.frame_umat.get()

            if self.roi is not None:
                mask = np.zeros(frame.shape[:2], dtype="uint8")
                cv2.fillPoly(mask, [self.roi], color=255)
                masked_frame = cv2.bitwise_and(frame, frame, mask=mask)
            else:
                masked_frame = frame

            hsv = cv2.cvtColor(masked_frame, cv2.COLOR_BGR2HSV)

            resultados = {}

            for nombre_color, (hmin, smin, vmin, hmax, smax, vmax) in self.COLORES.items():
                lower = np.array([hmin, smin, vmin], dtype="uint8")
                upper = np.array([hmax, smax, vmax], dtype="uint8")

                mask = cv2.inRange(hsv, lower, upper)

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

                        ellipse = None
                        if len(largest_contour) >= 5:
                            ellipse = cv2.fitEllipse(largest_contour)

                        resultados[nombre_color] = {
                            "model": "circle",
                            "ellipse": ellipse,
                            "center": center,
                            "circle_center": enclosing_center,
                            "radius": float(enclosing_radius),
                            "area_radius": area_radius,
                            "circularity": circularity,
                            "area":   area,
                            "contour": largest_contour
                        }
            self.detection_callback(
                self.frame_id, resultados if resultados else None)
        except Exception as e:
            self.error_callback(
                f"Error al detectar esfera: {e} (EllipseDetection)")
