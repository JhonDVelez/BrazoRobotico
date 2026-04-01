from unittest import result

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
        # 1. Aseguramos que trabajamos con float32 en GPU
        # cv2.add es compatible con UMat y evita usar numpy
        img_f32 = cv2.add(img_umat, 1.0, dtype=cv2.CV_32F)

        # 2. GaussianBlur nativo en UMat (OpenCL)
        blur = cv2.GaussianBlur(img_f32, (0, 0), sigma)

        # 3. Sustituir np.log por cv2.log
        # cv2.log solo acepta floats positivos, por eso el +1.0 previo es clave
        log_img = cv2.log(img_f32)
        log_blur = cv2.log(blur)

        # 4. Resta de logaritmos en GPU
        retinex = cv2.subtract(log_img, log_blur)

        # NOTA SOBRE nan/inf:
        # cv2.log en UMat es más seguro que np.log. Si img > 0,
        # no deberías tener NaN o Inf. Si aun así necesitas limpiar:
        # retinex = cv2.patchNaNs(retinex, 0) # Disponible en versiones recientes

        return retinex

    def get_all_circles(self, frame_umat: cv2.UMat, drawn_frame_umat: cv2.UMat, search_mask_corners: np.ndarray):

        if search_mask_corners is not None:
            mask = np.zeros(frame_umat.get().shape[:2], dtype="uint8")
            cv2.fillPoly(mask, [search_mask_corners], color=255)
            hsv = cv2.cvtColor(cv2.bitwise_and(
                frame_umat, cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)), cv2.COLOR_BGR2HSV)
        else:
            hsv = cv2.cvtColor(frame_umat, cv2.COLOR_BGR2HSV)

        resultados = {}

        for nombre_color, (hmin, smin, vmin, hmax, smax, vmax) in self.COLORES.items():
            # 2. Crear máscara para el color actual
            lower = np.array([hmin, smin, vmin], dtype="uint8")
            upper = np.array([hmax, smax, vmax], dtype="uint8")

            # inRange funciona perfectamente con UMat
            mask = cv2.inRange(hsv, lower, upper)

            # 3. Limpieza morfológica rápida
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

            # 4. Encontrar contornos del color actual
            contours, _ = cv2.findContours(
                mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if contours:
                # Tomamos el contorno más grande que parezca una esfera
                largest_contour = max(contours, key=cv2.contourArea)
                area = cv2.contourArea(largest_contour)

                if area > 500:  # Filtro de tamaño mínimo
                    ((x, y), radius) = cv2.minEnclosingCircle(largest_contour)
                    centro = np.array((int(x), int(y)), dtype=np.int32)

                    # Guardar resultado
                    resultados[nombre_color] = {
                        "centro": centro,
                        "radio": int(radius),
                        "area": area
                    }

        return resultados

    def _draw_detection(self, frame: cv2.UMat, sphere_results: dict):
        # Dibujamos círculo y etiqueta
        for color, (center, radio, area) in sphere_results.items():
            sphere = sphere_results.get(color)
            c = sphere.get(center)
            r = sphere.get(radio)
            cv2.circle(frame, c, r, (0, 255, 0), 2)
            cv2.circle(frame, c, 5, (0, 0, 255), -1)
            cv2.putText(frame, color, (c[0] - 20, c[1] - r - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

    def get_color_mask(self, frame: cv2.UMat):
        # 1. Convertir a LAB para aislar el amarillo
        # return self.segmentar_esfera_precision(original_frame)
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)

        # 2. Separar canales
        l, a, b = cv2.split(lab)

        _, mask_yellow = cv2.threshold(b, 155, 255, cv2.THRESH_BINARY)

        # 3. Limpieza morfológica (Elimina ruido de la sombra o reflejos)
        kernel = np.ones((5, 5), np.uint8)
        mask_yellow = cv2.morphologyEx(mask_yellow, cv2.MORPH_OPEN, kernel)
        mask_yellow = cv2.morphologyEx(mask_yellow, cv2.MORPH_CLOSE, kernel)

        # 4. Encontrar el círculo usando Hough o Contornos
        # Usamos la máscara limpia para detectar bordes solo del objeto amarillo
        edges = cv2.Canny(mask_yellow, 100, 200)

        # Visualización (como en tu código original)
        mask_bgr = cv2.cvtColor(mask_yellow, cv2.COLOR_GRAY2BGR)
        edge_bgr = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)

        return mask_bgr
