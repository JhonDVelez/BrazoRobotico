import cv2
import numpy as np


class RastreadorEsferaBlanca:
    def __init__(self, esquinas_x, esquinas_y, lado_cuadro_mm):
        self.patron_size = (esquinas_x, esquinas_y)
        self.lado_mm = lado_cuadro_mm
        self.H = None
        self.H_inv = None  # Necesaria para dibujar el origen
        self.caja_recorte = None
        self.img_plano_recortada = None
        # Punto exacto en píxeles del origen real (para el indicador)
        self.origen_px_roi = None

    def etapa1_calibrar_plano(self, ruta_img_plano):
        """Calibra definiendo la esquina sup. izq. como (0,0)mm."""
        img = cv2.imread(ruta_img_plano)
        if img is None:
            raise ValueError("No se pudo cargar la imagen.")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        ret, esquinas_img = cv2.findChessboardCorners(
            gray, self.patron_size, None)

        if not ret:
            raise ValueError("No se detectó el tablero.")

        # Refinar esquinas
        criterios = (cv2.TERM_CRITERIA_EPS +
                     cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
        esquinas_img_ref = cv2.cornerSubPix(
            gray, esquinas_img, (11, 11), (-1, -1), criterios)

        # ----------------------------------------------------------------------
        # PASO CLAVE: Identificar la esquina Sup. Izq. en la IMAGEN
        # ----------------------------------------------------------------------
        # Aplanamos el array de esquinas (shape: N, 2)
        puntos_px = esquinas_img_ref.reshape(-1, 2)

        # Buscamos el punto con menor coordenada Y (más arriba)
        idx_sup_izq = np.argmin(puntos_px[:, 1])
        # Si hubiera empate en Y, habría que buscar el menor X entre esos,
        # pero para simplificar y dado que hay ángulo, argmin(Y) suele bastar.

        esquina_sup_izq_px = puntos_px[idx_sup_izq]
        print(
            f"Esquina Sup. Izq. detectada en píxeles (Imagen Completa): {esquina_sup_izq_px}")

        # --- ROI y ZOOM (15% margen) ---
        x_min, x_max = np.min(puntos_px[:, 0]), np.max(puntos_px[:, 0])
        y_min, y_max = np.min(puntos_px[:, 1]), np.max(puntos_px[:, 1])
        m_x, m_y = int((x_max-x_min)*0.15), int((y_max-y_min)*0.15)

        h_i, w_i = img.shape[:2]
        self.caja_recorte = (max(0, int(x_min-m_x)), max(0, int(y_min-m_y)),
                             min(w_i, int(x_max+m_x)), min(h_i, int(y_max+m_y)))

        c_x1, c_y1, c_x2, c_y2 = self.caja_recorte
        self.img_plano_recortada = gray[c_y1:c_y2, c_x1:c_x2]

        # Ajustar TODAS las esquinas detectadas para que coincidan con el recorte
        puntos_px_roi = puntos_px.copy()
        puntos_px_roi[:, 0] -= c_x1
        puntos_px_roi[:, 1] -= c_y1

        # Guardar la ubicación del origen dentro del ROI para el indicador visual
        self.origen_px_roi = (
            puntos_px_roi[idx_sup_izq][0], puntos_px_roi[idx_sup_izq][1])

        # ----------------------------------------------------------------------
        # PASO CLAVE 2: Generar Coordenadas Reales alineadas a esa esquina
        # ----------------------------------------------------------------------
        # Creamos una cuadrícula estándar
        grid = np.mgrid[0:self.patron_size[0],
                        0:self.patron_size[1]].T.reshape(-1, 2)

        # Asumimos que el grid estándar (0,0) corresponde al idx_sup_izq detectado
        # Esto es lo más directo: simplemente reordenamos las esquinas del mundo
        # para que la primera coincida con la esquina sup izq detectada.

        # *Nota*: Esto es complejo. La forma más robusta es reordenar los *puntos_px_roi*
        # para que sigan un orden estricto de cuadrícula que coincida con esquinas_mundo.

        # Enfoque simplificado: Usaremos la detección por defecto de OpenCV para calcular H,
        # y luego usaremos *pos_x, pos_y = H * punto_img*. Si (0,0) sale en otra esquina,
        # simplemente sumaremos el desfase (offset).

        esquinas_mundo = grid * self.lado_mm

        # Calculamos Homografía estándar
        self.H, _ = cv2.findHomography(
            puntos_px_roi, esquinas_mundo, cv2.RANSAC, 5.0)

        # Calculamos la posición del punto (0,0) real *calculado* en píxeles.
        test_orig_mundo = np.array([[[0.0, 0.0]]], dtype=np.float32)
        self.H_inv = np.linalg.inv(self.H)
        test_orig_px = cv2.perspectiveTransform(test_orig_mundo, self.H_inv)

        print(
            f"La homografía estándar ubica el (0,0)mm en: {test_orig_px[0][0]} px (en ROI)")
        print(
            f"Nosotros queremos el (0,0)mm en: {self.origen_px_roi} px (en ROI)")

        # Calcular Offset si no coinciden (OpenCV detectó otra esquina como primera)
        # Esto corrige la homografía para que el (0,0)mm real esté donde identificamos visualmente
        diff_px = test_orig_px[0][0] - np.array(self.origen_px_roi)

        # Es más fácil desplazar los puntos del mundo:
        puntos_mundo_corregidos = esquinas_mundo + \
            cv2.perspectiveTransform(
                test_orig_px - diff_px.reshape(1, 1, 2), self.H)[0][0]
        # Esto se vuelve muy complejo matemáticamente.

        # --- Enfoque Alternativo Robustisimo (Reordenar puntos de imagen) ---
        # 1. Definimos las 4 esquinas físicas del patrón detectado
        esquinas_4_indices = [idx_sup_izq,
                              # Sup. Der. (aprox por mayor X)
                              np.argmax(puntos_px[:, 0]),
                              # Inf. Der. (aprox por mayor Y)
                              np.argmax(puntos_px[:, 1]),
                              # Inf. Izq. (aprox por menor X)
                              np.argmin(puntos_px[:, 0])]

        # 2. Asignamos coordenadas reales a esas 4 esquinas específicas
        esquinas_4_mundo = np.array([
            # Sup Izq (Origen definido)
            [0, 0],
            [(self.patron_size[0]-1)*self.lado_mm, 0],          # Sup Der
            [(self.patron_size[0]-1)*self.lado_mm,
             (self.patron_size[1]-1)*self.lado_mm],  # Inf Der
            [0, (self.patron_size[1]-1)*self.lado_mm]           # Inf Izq
        ], dtype=np.float32)

        # 3. Tomamos los puntos de imagen correspondientes en el ROI
        esquinas_4_px_roi = puntos_px_roi[esquinas_4_indices]

        # 4. Calculamos Homografía solo usando las 4 esquinas externas (muy robusto a orden interno)
        self.H = cv2.getPerspectiveTransform(
            esquinas_4_px_roi.astype(np.float32), esquinas_4_mundo)
        self.H_inv = np.linalg.inv(self.H)  # Guardar inversa para indicador

        print("Etapa 1: Calibración finalizada forzando el (0,0)mm en la esquina Sup. Izq.")

    def etapa2_localizar_y_marcar_origen(self, ruta_img_esfera):
        if self.H is None:
            raise ValueError("Ejecuta Etapa 1 primero.")

        img_full = cv2.imread(ruta_img_esfera)
        c_x1, c_y1, c_x2, c_y2 = self.caja_recorte
        # Creamos una copia para dibujar sin alterar la detección de color
        roi_dibujo = img_full[c_y1:c_y2, c_x1:c_x2].copy()
        roi_gray = cv2.cvtColor(roi_dibujo, cv2.COLOR_BGR2GRAY)

        diff = cv2.absdiff(self.img_plano_recortada, roi_gray)
        _, thresh = cv2.threshold(diff, 50, 255, cv2.THRESH_BINARY)
        kernel = np.ones((5, 5), np.uint8)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

        contornos, _ = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # --- Detección y Medición ---
        pos_x_medida, pos_y_medida = None, None
        if contornos:
            c = max(contornos, key=cv2.contourArea)
            ((x, y), radio) = cv2.minEnclosingCircle(c)

            if radio > 5:
                # Ajuste de paralaje (punto de contacto inferior)
                punto_img = np.array([[[x, y + radio]]], dtype=np.float32)
                punto_mundo = cv2.perspectiveTransform(punto_img, self.H)

                pos_x_medida, pos_y_medida = punto_mundo[0][0][0], punto_mundo[0][0][1]
                print(
                    f"Esfera Blanca Medida desde Sup. Izq: X={pos_x_medida:.2f}mm, Y={pos_y_medida:.2f}mm")

                # Dibujar esfera y punto de contacto
                cv2.circle(roi_dibujo, (int(x), int(y)),
                           int(radio), (0, 255, 0), 2)
                cv2.circle(roi_dibujo, (int(x), int(y+radio)),
                           4, (0, 0, 255), -1)

        # ----------------------------------------------------------------------
        # PASO REQUERIDO: Indicador Visual del Origen (0,0)mm
        # ----------------------------------------------------------------------
        # Usamos la posición guardada en la Etapa 1
        orig_x_px, orig_y_px = int(
            self.origen_px_roi[0]), int(self.origen_px_roi[1])

        # Dibujar una cruz grande y el texto (0,0)
        color_origen = (255, 0, 255)  # Magenta para que resalte
        largo_cruz = 20
        # Línea horizontal
        cv2.line(roi_dibujo, (orig_x_px - largo_cruz, orig_y_px),
                 (orig_x_px + largo_cruz, orig_y_px), color_origen, 2)
        # Línea vertical
        cv2.line(roi_dibujo, (orig_x_px, orig_y_px - largo_cruz),
                 (orig_x_px, orig_y_px + largo_cruz), color_origen, 2)
        # Círculo central
        cv2.circle(roi_dibujo, (orig_x_px, orig_y_px), 5, color_origen, -1)
        # Texto
        cv2.putText(roi_dibujo, "(0,0)mm Origin", (orig_x_px + 10, orig_y_px - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color_origen, 2)

        if pos_x_medida is not None:
            # Texto con la medida cerca de la esfera
            cv2.putText(roi_dibujo, f"Pos: ({pos_x_medida:.1f}, {pos_y_medida:.1f})mm",
                        (int(x) + 15, int(y) + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        cv2.imshow("Deteccion y Verificacion de Origen (Zoom)", roi_dibujo)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        return pos_x_medida, pos_y_medida


# USO (Asegúrate de tener imágenes válidas)
# Supongamos un tablero de 7x7 esquinas internas (8x8 cuadros), cuadros de 20mm
rastreador = RastreadorEsferaBlanca(
    esquinas_x=7, esquinas_y=7, lado_cuadro_mm=25.0)

try:
    rastreador.etapa1_calibrar_plano('Codigos_test/plano_vacio.jpg')
    rastreador.etapa2_localizar_y_marcar_origen(
        'Codigos_test/plano_con_esfera.jpg')
except Exception as e:
    print(f"Error: {e}")
    # Si no tienes imágenes, el código fallará aquí, pero la lógica está implementada.
