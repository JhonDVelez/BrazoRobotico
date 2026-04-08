import numpy as np
import cv2


class CircleEstimation:
    COLORES = {
        # Formato: (H_min, S_min, V_min, H_max, S_max, V_max)
        "amarillo": (20, 100, 100, 30, 255, 255),
        "verde":    (40, 70, 70, 80, 255, 255),
        "azul":     (100, 150, 50, 130, 255, 255),
        "naranja":  (5, 150, 150, 15, 255, 255),
        "morado":   (130, 50, 50, 160, 255, 255),
    }

    def __init__(self) -> None:
        pass

    def single_scale_retinex(self, img_umat, sigma):
        img_f32 = cv2.add(img_umat, 1.0, dtype=cv2.CV_32F)
        blur = cv2.GaussianBlur(img_f32, (0, 0), sigma)
        log_img = cv2.log(img_f32)
        log_blur = cv2.log(blur)
        retinex = cv2.subtract(log_img, log_blur)
        return retinex

    def get_all_circles(
        self,
        frame_umat: cv2.UMat,
        drawn_frame_umat: cv2.UMat,
        search_mask_corners: np.ndarray,
    ) -> dict:
        """Detecta la esfera más grande de cada color en el frame.

        Returns:
            dict con forma:
            {
                "amarillo": {"centro": np.array([x, y]), "radio": int, "area": float},
                ...
            }
            Solo incluye colores encontrados.
        """
        if search_mask_corners is not None:
            mask = np.zeros(frame_umat.get().shape[:2], dtype="uint8")
            cv2.fillPoly(mask, [search_mask_corners], color=255)
            hsv = cv2.cvtColor(
                cv2.bitwise_and(frame_umat, cv2.cvtColor(
                    mask, cv2.COLOR_GRAY2BGR)),
                cv2.COLOR_BGR2HSV,
            )
        else:
            hsv = cv2.cvtColor(frame_umat, cv2.COLOR_BGR2HSV)

        resultados = {}

        for nombre_color, (hmin, smin, vmin, hmax, smax, vmax) in self.COLORES.items():
            lower = np.array([hmin, smin, vmin], dtype="uint8")
            upper = np.array([hmax, smax, vmax], dtype="uint8")

            mask = cv2.inRange(hsv, lower, upper)

            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

            contours, _ = cv2.findContours(
                mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            if contours:
                largest_contour = max(contours, key=cv2.contourArea)
                area = cv2.contourArea(largest_contour)

                if area > 500:
                    ((x, y), radius) = cv2.minEnclosingCircle(largest_contour)
                    centro = np.array((int(x), int(y)), dtype=np.int32)

                    # Resultado como dict con claves explícitas
                    resultados[nombre_color] = {
                        "centro": centro,       # np.array([u, v])
                        "radio":  int(radius),  # int
                        "area":   area,         # float
                    }

        return resultados if resultados else None

    def _draw_detection(self, frame: cv2.UMat, sphere_results: dict):
        """Dibuja círculo y etiqueta sobre cada esfera detectada."""
        for color, datos in sphere_results.items():
            # ✅ Acceso correcto por clave de diccionario
            c = datos["centro"]   # np.array([u, v])
            r = datos["radio"]    # int

            cv2.circle(frame, c, r, (0, 255, 0), 2)
            cv2.circle(frame, c, 5, (0, 0, 255), -1)
            cv2.putText(
                frame, color,
                (c[0] - 20, c[1] - r - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2,
            )
