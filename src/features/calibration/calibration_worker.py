"""
Módulo encargado del procesamiento de datos para la calibración de cámaras.

Este módulo define la clase CalibrationWorker, la cual gestiona la detección de
tableros ChArUco, la acumulación de puntos de control y el cálculo de los
parámetros intrínsecos de la cámara (matriz de cámara y coeficientes de distorsión).

Conexiones:
    - Emite `frame_processed` para visualizar la detección en tiempo real.
    - Emite `calibration_success` al finalizar el cálculo exitosamente.
    - Emite `error_occurred` en caso de fallos en el proceso.
"""

from typing import Any

import cv2
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot


class CalibrationWorker(QObject):
    """
    Worker encargado exclusivamente del procesamiento de datos de calibración.

    Maneja la detección de corners ChArUco, acumulación de frames y cálculo de
    matrices de calibración utilizando OpenCV.

    Attributes:
        frame_processed (pyqtSignal): Emite (frame, n_corners, status_text, color).
        calibration_success (pyqtSignal): Emite (matrix, dist_coeffs, reprojection_error).
        error_occurred (pyqtSignal): Emite un mensaje de error (str).
    """
    # Señales para comunicación con el controlador
    # frame, n_corners, status_text, color
    frame_processed = pyqtSignal(np.ndarray, int, str, object)
    calibration_success = pyqtSignal(
        np.ndarray, np.ndarray, float)  # matrix, dist, error
    error_occurred = pyqtSignal(str)

    def __init__(self) -> None:
        """
        Inicializa el worker con la configuración del tablero ChArUco por defecto.
        """
        super().__init__()
        # Configuración del tablero ChArUco (Valores originales)
        self._aruco_dict = cv2.aruco.getPredefinedDictionary(
            cv2.aruco.DICT_4X4_50)
        self._board = cv2.aruco.CharucoBoard(
            size=(12, 5),
            squareLength=0.03,
            markerLength=0.022,
            dictionary=self._aruco_dict
        )

        # Variables de estado y acumulación
        self._all_corners = []
        self._all_ids = []
        self._image_size = None
        self._calibration_frames_count = 0
        self._should_capture = False
        self._last_detection = None

    @pyqtSlot(object)
    def process_frame(self, frame) -> None:
        """
        Procesa un frame para detectar corners ChArUco y gestionar la captura.

        Args:
            frame (np.ndarray | cv2.UMat): Frame de video a procesar.
        """
        if frame is None:
            return

        # Convertir a numpy si es UMat
        if isinstance(frame, cv2.UMat):
            frame_np = frame.get()
        else:
            frame_np = frame.copy()

        gray = cv2.cvtColor(frame_np, cv2.COLOR_BGR2GRAY)

        if self._image_size is None:
            self._image_size = gray.shape[::-1]

        # Detección de marcadores
        params = cv2.aruco.DetectorParameters()
        detector = cv2.aruco.ArucoDetector(self._aruco_dict, params)
        marker_corners, marker_ids, _ = detector.detectMarkers(gray)

        if marker_ids is None:
            return

        charuco_corners = None
        charuco_ids = None
        n = 0

        if marker_ids is not None and len(marker_ids) >= 6:
            charuco_detector = cv2.aruco.CharucoDetector(self._board)
            charuco_corners, charuco_ids, _, _ = charuco_detector.detectBoard(
                image=gray, markerCorners=marker_corners, markerIds=marker_ids
            )
            n = len(charuco_corners) if charuco_corners is not None else 0

        # Lógica de dibujo y estado
        status_text = ""
        status_color = (0, 0, 255)  # Rojo por defecto

        if charuco_corners is not None and n >= 6:
            self._last_detection = (charuco_corners, charuco_ids, n)
            cv2.aruco.drawDetectedCornersCharuco(
                frame_np, charuco_corners, charuco_ids, (0, 255, 0))

            if self._should_capture:
                self._all_corners.append(charuco_corners.copy())
                self._all_ids.append(charuco_ids.copy())
                self._calibration_frames_count += 1
                self._should_capture = False
                status_text = f"¡Frame capturado! Total: {self._calibration_frames_count} (min. 10)"
                status_color = (0, 255, 0)
            else:
                status_text = f"Presiona 'Capturar Imagen' para guardar (Total: {self._calibration_frames_count})"
                status_color = (255, 165, 0)
        else:
            status_text = "Posiciona el tablero ChArUco en la camara"
            status_color = (0, 0, 255)

        cv2.putText(frame_np, status_text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)

        self.frame_processed.emit(frame_np, n, status_text, status_color)

    def set_should_capture(self, value: bool) -> bool:
        """
        Activa el flag para capturar el siguiente frame valido detectado.

        Args:
            value (bool): Valor para el flag de captura.

        Returns:
            bool: True si se pudo activar (hay detección valida), False en caso contrario.
        """
        if self._last_detection is not None and self._last_detection[2] >= 6:
            self._should_capture = value
            return True
        return False

    def run_calibration(self) -> None:
        """
        Ejecuta el algoritmo de calibración de OpenCV con los datos acumulados.

        Calcula la matriz intrínseca y los coeficientes de distorsión.
        Emite `calibration_success` si tiene éxito o `error_occurred` si falla.
        """
        if self._calibration_frames_count < 10:
            self.error_occurred.emit(
                f"Se necesitan al menos 10 frames. Capturados: {self._calibration_frames_count}")
            return

        try:
            valid_object_points = []
            valid_image_points = []

            for corners, ids in zip(self._all_corners, self._all_ids):
                if corners is not None and ids is not None:
                    corners = np.asarray(corners, dtype=np.float32)
                    ids = np.asarray(ids, dtype=np.int32)
                    if len(corners) >= 4:
                        if corners.ndim == 2:
                            corners = corners.reshape(-1, 1, 2)

                        object_points, image_points = self._board.matchImagePoints(
                            corners, ids.reshape(-1, 1))

                        if object_points is None or image_points is None:
                            continue

                        if len(object_points) >= 4 and len(image_points) >= 4:
                            valid_object_points.append(
                                np.asarray(object_points, dtype=np.float32))
                            valid_image_points.append(
                                np.asarray(image_points, dtype=np.float32))

            if len(valid_object_points) < 10:
                self.error_occurred.emit(
                    f"Se necesitan al menos 10 capturas válidas. Válidas: {len(valid_object_points)}")
                return

            flags = cv2.CALIB_RATIONAL_MODEL
            ret, camera_matrix, dist_coeffs, _, _ = cv2.calibrateCamera(
                objectPoints=valid_object_points,
                imagePoints=valid_image_points,
                imageSize=self._image_size,
                cameraMatrix=None,
                distCoeffs=None,
                flags=flags
            )

            self.calibration_success.emit(camera_matrix, dist_coeffs, ret)

            # Limpiar datos tras éxito
            self.reset_data()

        except (cv2.error, ValueError, np.linalg.LinAlgError) as e:
            print(
                f"[DEBUG] Error en calibración de cámara ({type(e).__name__}): {e}")
            self.error_occurred.emit(
                f"Error en calibración: {type(e).__name__}: {str(e)}")

    def reset_data(self) -> None:
        """
        Resetea todos los acumuladores de puntos y el contador de frames.
        """
        self._all_corners = []
        self._all_ids = []
        self._calibration_frames_count = 0
        self._last_detection = None

    # Getters explícitos
    def get_captured_count(self) -> int:
        """
        Obtiene el número de frames capturados exitosamente.

        Returns:
            int: Número de frames.
        """
        return self._calibration_frames_count

    def get_image_size(self) -> None | Any:
        """
        Obtiene el tamaño de imagen detectado.

        Returns:
            tuple: (ancho, alto) o None.
        """
        return self._image_size

    def get_last_detection(self):
        """
        Obtiene los datos de la última detección de corners ChArUco.

        Returns:
            tuple: (corners, ids, n) o None.
        """
        return self._last_detection
