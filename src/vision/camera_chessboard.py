from typing import Optional, Tuple
import cv2
import numpy as np
from vision.chessboard_detector import ChessboardDetector
from vision.camera_control import CameraControl


class CameraChessBoard:
    """Cámara especializada para detección de tableros de ajedrez usando preprocesado con UMat"""

    def __init__(self, board_size: Tuple[int, int] = (7, 7)):
        # Cache para optimización
        self.image_processed = None
        self.detect_results = None
        self.prev_mask_corners = None
        self._detection_cache_frames = 0
        self._detection_interval = 4  # Detectar tablero cada N frames para mejor performance
        self._use_clahe = True
        self.process_enabled = True  # Controla si hace detección de esquinas
        self.show_grid = False
        self.show_phys = True

        dictionary_id = cv2.aruco.DICT_6X6_250
        aruco_dict = cv2.aruco.getPredefinedDictionary(dictionary_id)
        print(board_size)
        charuco_board = cv2.aruco.CharucoBoard(
            size=(12, 5),
            squareLength=0.03,
            markerLength=0.022,
            dictionary=aruco_dict
        )
        charuco_detector = cv2.aruco.CharucoDetector(charuco_board)

        self.detector = ChessboardDetector(
            board_size, aruco_dict, charuco_board, charuco_detector)
        self.camera = CameraControl()

    def camera_on(self):
        """ Enciende la camara"""
        return self.camera.camera_on()

    def camera_off(self):
        """ Apaga la camara"""
        self.camera.camera_off()

    def get_coordinates(self, frame: np.ndarray) -> tuple[np.ndarray, Optional[np.ndarray], Optional[np.ndarray]]:
        """Actualiza esquinas y retorna (frame con overlay, esquinas 9x9, esquinas 11x11)."""
        if frame is None:
            return None, None, None

        # Si no hay procesamiento requerido, devolvemos el frame directo rápido
        if not self.process_enabled and not self.show_grid and not self.show_phys:
            return frame, self.prev_mask_corners

        self._detection_cache_frames += 1
        if self._detection_cache_frames >= self._detection_interval:
            try:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                self.image_processed = self.camera.apply_division_trick(gray)
                self.detect_results = self.detector.detect_corners(
                    self.image_processed)
            except Exception as e:
                print(f"Error detectando esquinas (CameraChessboard): {e}")
                self.detect_results = None
                self.prev_mask_corners = None
            self._detection_cache_frames = 0

        drawn_image = frame
        if self.detect_results is not None and self.show_grid:
            drawn_image = frame.copy()
            try:
                drawn_image = self.detector.draw_grid(
                    drawn_image,
                    self.detect_results,
                    show_labels=False,
                    border_labels_only=True,
                    show_phys=self.show_phys,
                    origin='tl',
                    cell_size_mm=(30.0, 30.0),
                )
            except Exception as e:
                print(f"Error dibujando grid (CameraChessboard): {e}")

        return drawn_image, self.image_processed, self.detect_results, self.prev_mask_corners

    def get_video_frame(self):
        """Obtiene un frame procesado de la cámara"""
        frame = self.camera.take_frame()
        if frame is None:
            raise IOError(
                "No se pudo obtener frame de la cámara (CameraChessboard)")

        try:
            return self.get_coordinates(frame)
        except Exception as e:
            print(f"Error procesando frame (CameraChessboard): {e}")
            return frame, None, None, None
