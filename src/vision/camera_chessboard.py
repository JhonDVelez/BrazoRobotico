from typing import Optional, Tuple
import cv2
import numpy as np
from PyQt6.QtCore import QThread
from vision.chessboard_detector import ChessboardDetector
from vision.camera_control import CameraControl
from vision import camera_utils


class CameraChessBoard(QThread):
    """Cámara especializada para detección de tableros de ajedrez usando preprocesado con UMat"""

    def __init__(self, board_size: Tuple[int, int] = (7, 7)):
        super().__init__()
        self.detector = ChessboardDetector(board_size)
        self.camera = CameraControl()
        self.detector.start()
        self.camera.start()

        # Cache para optimización
        self.corners = None
        self._detection_cache_frames = 0
        self._detection_interval = 4  # Detectar tablero cada N frames para mejor performance
        self._use_clahe = True
        self.process_enabled = True  # Controla si hace detección de esquinas
        self.show_grid = False
        self.show_phys = False

    def camera_on(self):
        """ Enciende la camara"""
        return self.camera.camera_on()

    def camera_off(self):
        """ Apaga la camara"""
        self.camera.camera_off()

    def get_coordinates(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """Actualiza esquinas y retorna frame con overlay si corresponde."""
        if frame is None:
            return None

        # Si no hay procesamiento requerido, devolvemos el frame directo rápido
        if not self.process_enabled and not self.show_grid and not self.show_phys:
            return frame

        self._detection_cache_frames += 1
        if self._detection_cache_frames >= self._detection_interval:
            try:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                if self._use_clahe:
                    pre = camera_utils.apply_division_trick(gray)
                else:
                    pre = gray
                self.corners = self.detector.detect_corners(pre)
            except Exception as e:
                print(f"Error detectando esquinas: {e}")
                self.corners = None
            self._detection_cache_frames = 0

        out_frame = frame
        if self.corners is not None and self.show_grid:
            out_frame = frame.copy()
            try:
                self.detector.draw_grid(
                    out_frame,
                    self.corners,
                    show_labels=False,
                    border_labels_only=True,
                    show_phys=self.show_phys,
                    origin='tl',
                    cell_size_mm=(25.0, 25.0),
                )
            except Exception as e:
                print(f"Error dibujando grid: {e}")

        return out_frame

    def get_video_frame(self):
        """Obtiene un frame procesado de la cámara"""
        frame = self.camera.take_frame()
        if frame is None:
            raise IOError("No se pudo obtener frame de la cámara")

        try:
            return self.get_coordinates(frame)
        except Exception as e:
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
