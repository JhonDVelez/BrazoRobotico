from typing import Optional, Tuple
import numpy as np
from vision.chessboard import ChessboardDetector
from vision.camera import CameraControl


class CameraChessBoard(CameraControl):
    """Cámara especializada para detección de tableros de ajedrez - Versión optimizada"""

    def __init__(self, camera_index: int = 0, board_size: Tuple[int, int] = (7, 7)):
        super().__init__(camera_index)
        self.detector = ChessboardDetector(board_size)

        # Cache para optimización
        self._last_detection_result = None
        self._detection_cache_frames = 0
        self._detection_interval = 3  # Detectar tablero cada 3 frames para mejor performance

        # Configuración optimizada para threading
        self.processing_enabled = True

    def get_coordinates(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """Obtiene coordenadas del tablero de forma optimizada"""
        if not self.processing_enabled:
            return frame

        corners = self.detector.detect_corners(
            self.auto_gamma_correction(frame))
        self._last_detection_result = corners
        self._detection_cache_frames = 0

        # Dibujar grid si se detectó tablero
        if corners is not None:
            frame_copy = frame.copy()
            self.detector.draw_grid(frame_copy, corners, False, False)
            return frame_copy

        return frame

    def get_video_frame(self):
        """Obtiene un frame procesado de la cámara - Versión optimizada"""
        frame = self.take_frame()
        if frame is None:
            raise IOError("No se pudo obtener frame de la cámara")

        # Procesar frame de forma optimizada
        try:
            frame_processed = self.get_coordinates(frame)
            return frame_processed if frame_processed is not None else frame
        except RuntimeError as e:
            # En caso de error en procesamiento, devolver frame original
            print(f"Error procesando frame: {e}")
            return frame
