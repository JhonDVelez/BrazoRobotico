import cv2
import numpy as np
from typing import Optional, Tuple

class chessboard_detector:
    """Clase separada para detección de tableros de ajedrez
    """
    
    def __init__(self, board_size):
        """ Inicializa el detector de tableros de ajedrez

        Args:
            board_size (Tuple[int, int], optional):  Tamaño del tablero de ajedrez (filas, columnas). Por defecto es (7, 7).
        """
        self.board_size = board_size
        self.criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
    
    def detect_corners(self, frame):
        """ Detecta las esquinas del tablero de ajedrez en un frame dado.

        Args:
            frame (np.ndarray): Imagen del frame donde se buscará el tablero de ajedrez.

        Returns:
            Optional[np.ndarray]: Matriz de esquinas detectadas o None si no se detecta el tablero.
        """
        if frame is None:
            return None
            
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Intentar detección básica
        ret, corners = cv2.findChessboardCornersSB(gray, self.board_size, cv2.CALIB_CB_ADAPTIVE_THRESH)
        
        if not ret:
            # Segundo intento con normalización
            ret, corners = cv2.findChessboardCornersSB(
                gray, self.board_size, 
                cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE
            )
            
        if not ret:
            return None
        
        # Refinar esquinas
        corners_refined = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), self.criteria)
        return self.__extrapolate_corners(corners_refined)
    
    def __extrapolate_corners(self, corners):
        """Extrapola las esquinas externas del tablero"""
        rows, cols = self.board_size
        
        # Crear puntos ideales
        ideal_points = np.array([
            [j, i] for i in range(rows) for j in range(cols)
        ], dtype=np.float32)
        
        # Calcular homografía
        corners_flat = corners.reshape(-1, 2).astype(np.float32)
        homography, _ = cv2.findHomography(ideal_points, corners_flat)
        
        # Crear grid extendido
        extended_ideal = np.array([
            [j, i] for i in range(-1, rows + 1) for j in range(-1, cols + 1)
        ], dtype=np.float32)
        
        # Aplicar transformación
        extended_corners = cv2.perspectiveTransform(
            extended_ideal.reshape(-1, 1, 2), homography
        ).reshape(-1, 2)
        
        return extended_corners.reshape(rows + 2, cols + 2, 2)
    
    def draw_grid(self, frame, corners, show_labels, border_labels_only):
        """Dibuja la red final obtenida luego de la extrapolación sobre la imagen de referencia
        del tablero de ajedrez

        Args:
            frame (numpy.ndarray): Imagen tomada de la cámara
            corners (numpy.ndarray): Matriz de posiciones extendida por extrapolación
            show_labels (bool): Si True, muestra etiquetas de texto en los puntos. Por defecto False.
            border_labels_only (bool): Si True, muestra etiquetas solo en los puntos de borde. Por defecto True.
        """
        if corners is None:
            return frame
            
        rows, cols = corners.shape[:2]
        
        # Dibujar puntos
        for i in range(rows):
            for j in range(cols):
                point = corners[i, j].astype(int)
                is_border = (i == 0 or i == rows-1 or j == 0 or j == cols-1)
                color = (0, 0, 255) if is_border else (0, 240, 255)
                cv2.circle(frame, tuple(point), 5, color, -1)
                if show_labels and (not border_labels_only or is_border):
                    cv2.putText(frame,
                                f"[{point[0]},{point[1]}]",
                                tuple(point + [-25, 15]),
                                cv2.FONT_HERSHEY_COMPLEX_SMALL,
                                0.4,
                                (0, 0, 255),
                                1,
                                cv2.LINE_AA)
        
        # Dibujar líneas horizontales
        for i in range(rows):
            for j in range(cols-1):
                pt1 = tuple(corners[i, j].astype(int))
                pt2 = tuple(corners[i, j+1].astype(int))
                cv2.line(frame, pt1, pt2, (255, 0, 0), 1)
        
        # Dibujar líneas verticales
        for i in range(rows-1):
            for j in range(cols):
                pt1 = tuple(corners[i, j].astype(int))
                pt2 = tuple(corners[i+1, j].astype(int))
                cv2.line(frame, pt1, pt2, (255, 0, 0), 1)
        
        return frame