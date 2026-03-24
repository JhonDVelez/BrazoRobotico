from unittest import result

import numpy as np
import cv2


class CircleEstimation:
    COLORES = {
        "amarillo": [(18,  80, None, 38,  255, 255)],
        "verde":    [(35,  60, None, 85,  255, 255)],
        "azul":     [(100, 60, None, 130, 255, 255)],
        "naranja":  [(10,  80, None, 20,  255, 255)],
        "morado":   [(130, 50, None, 160, 255, 255)],
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

    def get_circle_center(self, original_frame, umat_frame):
        mask_lab = self.get_color_mask(umat_frame)
        mask_hsv = self.mascara_color_adaptativa(
            umat_frame, self.COLORES["amarillo"])

        mask_hsv = cv2.cvtColor(mask_hsv, cv2.COLOR_GRAY2BGR)

        h2 = cv2.hconcat([cv2.resize(mask_lab, (640, 360)),
                          cv2.resize(mask_hsv, (640, 360))])
        return h2

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

    def mascara_color_adaptativa(self, imagen, rangos):
        hsv = cv2.cvtColor(imagen, cv2.COLOR_BGR2HSV)
        V = cv2.split(hsv)[2]

        # Otsu siempre devuelve escalar Python aunque V sea UMat
        umbral_v, _ = cv2.threshold(
            V, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        v_min_auto = max(0, int(umbral_v * 0.6))

        # ✓ Antes: np.zeros(V.shape) → falla con UMat (no tiene .shape)
        # cero del mismo tipo y tamaño que V
        mascara_total = cv2.subtract(V, V)

        for (h_min, s_min, v_min, h_max, s_max, v_max) in rangos:
            v_min_final = v_min_auto if v_min is None else v_min
            lower = np.array([h_min, s_min, v_min_final])
            upper = np.array([h_max, s_max, v_max])

            # ✓ Antes: mascara_total |= ... → falla con UMat
            mascara_total = cv2.bitwise_or(
                mascara_total, cv2.inRange(hsv, lower, upper))

        # ✓ Kernel como UMat para mantener toda la operación en GPU
        kernel = cv2.UMat(np.ones((5, 5), np.uint8))
        mascara_total = cv2.morphologyEx(
            mascara_total, cv2.MORPH_OPEN,  kernel)
        mascara_total = cv2.morphologyEx(
            mascara_total, cv2.MORPH_CLOSE, kernel)

        resultado = cv2.bitwise_and(imagen, imagen, mask=mascara_total)

        return mascara_total
