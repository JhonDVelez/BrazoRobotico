from typing import Optional, Tuple
import numpy as np
from vision.chessboard import ChessboardDetector
from vision.camera import CameraControl


class CameraChessBoard():
    """Cámara especializada para detección de tableros de ajedrez usando preprocesado con UMat"""

    def __init__(self, board_size: Tuple[int, int] = (7, 7)):
        self.detector = ChessboardDetector(board_size)
        self.camera = CameraControl()

        # Cache para optimización
        self.corners = None
        self._detection_cache_frames = 0
        self._detection_interval = 3  # Detectar tablero cada N frames para mejor performance

    def camera_on(self):
        """ Enciende la camara"""
        return self.camera.camera_on()

    def camera_off(self):
        """ Apaga la camara"""
        self.camera.camera_off()

    def get_coordinates(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """ Obtiene coordenadas del tablero.
            Aplica preprocesado acelerado (UMat) para la corrección gamma y luego realiza
            la detección cada N frames. La detección de esquinas se hace en CPU.
        """
        if frame is None:
            return None
        try:
            pre = self.camera.auto_gamma_correction(frame)
        except Exception:
            pre = frame

        # Detección cada N frames
        self._detection_cache_frames += 1
        if self._detection_cache_frames >= self._detection_interval:
            try:
                self.corners = self.detector.detect_corners(pre)
            except Exception as e:
                print(f"Error detectando esquinas: {e}")
                self.corners = None
            self._detection_cache_frames = 0

        # Dibujar grid si se detectó tablero
        out_frame = frame.copy()
        if self.corners is not None:
            try:
                self.detector.draw_grid(
                    out_frame, self.corners, False, False, True, 'tl', (25.0, 25.0))
            except Exception as e:
                print(f"Error dibujando grid: {e}")

        return out_frame

    def get_video_frame(self):
        """Obtiene un frame procesado de la cámara"""
        frame = self.camera.take_frame()
        if frame is None:
            raise IOError("No se pudo obtener frame de la cámara")

        try:
            frame_processed = self.get_coordinates(frame)
            return frame_processed if frame_processed is not None else frame
        except RuntimeError as e:
            print(f"Error procesando frame: {e}")
            return frame

    # ------------------------------------------------------------
    def get_spatial_matrix(
        self,
        frame: np.ndarray,
        origin: "str | tuple[int,int]" = "tl",
        cell_size_mm: tuple[float, float] = (25.0, 25.0),
    ) -> Optional[np.ndarray]:
        """Devuelve las coordenadas físicas (mm) de la malla detectada.

        El método asegura que haya habido una actualización de esquinas mediante
        ``get_coordinates``; si no se detecta tablero retorna ``None``. El origen
        puede ser especificado como una cadena entre ``'tl','tr','bl','br'`` ('top left', 
        'top right', 'bottom left', 'bottom right')o directamente con índices de 
        la matriz de esquinas.

        Args:
            frame: Imagen de la cámara como en ``get_coordinates``.
            origin: Esquina elegida como (0,0) en la rejilla.
            cell_size_mm: Dimensiones de cada casilla en milímetros.

        Returns:
            Matriz ``(rows,cols,2)`` de coordenadas físicas o ``None`` si no hay
            tablero detectado.
        """
        # actualizar esquinas en caché
        self.get_coordinates(frame)
        if self.corners is None:
            return None
        return self.detector.to_physical_coordinates(
            self.corners, origin, cell_size_mm
        )
