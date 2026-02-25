import cv2
import numpy as np


class ChessboardDetector:
    """ Clase separada para detección de tableros de ajedrez.
        Proporciona métodos para localizar esquinas internas y extrapolar la red completa.
    """

    def __init__(self, board_size):
        """ Inicializa el detector de tableros de ajedrez.

        Args:
            board_size (Tuple[int, int]): Tamaño del tablero (esquinas internas: filas, columnas).
        """
        self.board_size = board_size
        # Criterios de terminación para el refinamiento de esquinas (SubPix)
        # Se detiene tras 30 iteraciones o si se alcanza una precisión de 0.001
        self.criteria = (cv2.TERM_CRITERIA_EPS +
                         cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

    def detect_corners(self, frame):
        """ Detecta las esquinas del tablero de ajedrez en un frame dado.

        Args:
            frame (np.ndarray): Imagen del frame donde se buscará el tablero de ajedrez.

        Returns:
            Optional[np.ndarray]: Matriz de esquinas detectadas y extrapoladas o None.
        """
        if frame is None:
            return None

        # Convertir a escala de grises para facilitar el procesamiento de OpenCV
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Intentar detección básica con el algoritmo SB (Sector Based), más robusto que el estándar
        # CALIB_CB_ADAPTIVE_THRESH ayuda en condiciones de iluminación variable
        ret, corners = cv2.findChessboardCornersSB(
            gray, self.board_size, cv2.CALIB_CB_ADAPTIVE_THRESH)

        if not ret:
            return None

        # Refinar las esquinas detectadas para obtener precisión a nivel de sub-píxel
        # Esto es vital para la precisión en aplicaciones de robótica
        corners_refined = cv2.cornerSubPix(
            gray, corners, self.board_size, (-1, -1), self.criteria)
        
        # Una vez refinadas las internas, calculamos las externas por extrapolación
        return self.__extrapolate_corners(corners_refined)

    def __extrapolate_corners(self, corners):
        """ Extrapola las esquinas externas del tablero mediante homografía.
            Permite proyectar puntos más allá de los detectados inicialmente.
        """
        rows, cols = self.board_size

        # Crear una cuadrícula de puntos ideales (coordenadas teóricas planas)
        ideal_points = np.array([
            [j, i] for i in range(rows) for j in range(cols)
        ], dtype=np.float32)

        # Calcular la matriz de homografía que relaciona los puntos ideales con las esquinas reales
        corners_flat = corners.reshape(-1, 2).astype(np.float32)
        homography, _ = cv2.findHomography(ideal_points, corners_flat)

        # Crear un grid ideal extendido (añadiendo una fila y columna extra hacia afuera: -1 a rows+1)
        extended_ideal = np.array([
            [j, i] for i in range(-1, rows + 1) for j in range(-1, cols + 1)
        ], dtype=np.float32)

        # Aplicar la transformación de perspectiva para proyectar los puntos extendidos al plano de la imagen
        extended_corners = cv2.perspectiveTransform(
            extended_ideal.reshape((-1, 1, 2)), homography
        ).reshape(-1, 2)

        # Retornar la matriz reformateada incluyendo los nuevos bordes (rows+2, cols+2)
        return extended_corners.reshape(rows + 2, cols + 2, 2)

    def draw_grid(self, frame, corners, show_labels, border_labels_only):
        """ Dibuja la red final obtenida luego de la extrapolación sobre la imagen.

        Args:
            frame (numpy.ndarray): Imagen tomada de la cámara.
            corners (numpy.ndarray): Matriz de posiciones extendida (x, y).
            show_labels (bool): Si True, muestra las coordenadas numéricas en los puntos.
            border_labels_only (bool): Si True, limita el texto solo al perímetro del tablero.
        """
        if corners is None:
            return frame

        rows, cols = corners.shape[:2]

        # --- DIBUJO DE PUNTOS Y ETIQUETAS ---
        for i in range(rows):
            for j in range(cols):
                point = corners[i, j].astype(int)
                # Identificar si el punto pertenece al borde exterior
                is_border = (not i or i == rows-1 or not j or j == cols-1)
                
                # Color distintivo: Rojo para el borde, Amarillo/Dorado para el interior
                color = (0, 0, 255) if is_border else (0, 240, 255)
                cv2.circle(frame, tuple(point), 5, color, -1)
                
                # Lógica para mostrar las coordenadas de cada punto en el video
                if show_labels and (not border_labels_only or is_border):
                    cv2.putText(frame,
                                f"[{point[0]},{point[1]}]",
                                tuple(point + [-25, 15]), # Offset para no tapar el punto
                                cv2.FONT_HERSHEY_COMPLEX_SMALL,
                                0.4,
                                (0, 0, 255),
                                1,
                                cv2.LINE_AA)

        # --- DIBUJO DE LÍNEAS DE LA RED ---
        # Dibujar líneas horizontales conectando los puntos de cada fila
        for i in range(rows):
            for j in range(cols-1):
                pt1 = tuple(corners[i, j].astype(int))
                pt2 = tuple(corners[i, j+1].astype(int))
                cv2.line(frame, pt1, pt2, (255, 0, 0), 1)

        # Dibujar líneas verticales conectando los puntos de cada columna
        for i in range(rows-1):
            for j in range(cols):
                pt1 = tuple(corners[i, j].astype(int))
                pt2 = tuple(corners[i+1, j].astype(int))
                cv2.line(frame, pt1, pt2, (255, 0, 0), 1)

        return frame