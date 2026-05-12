import cv2
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot


class CalibrationWorker(QObject):
    """
    Worker encargado exclusivamente del procesamiento de datos de calibración.
    Maneja la detección de corners ChArUco, acumulación de frames y cálculo de matrices.
    """
    # Señales para comunicación con el controlador
    # frame, n_corners, status_text, color
    frame_processed = pyqtSignal(np.ndarray, int, str, object)
    calibration_success = pyqtSignal(
        np.ndarray, np.ndarray, float)  # matrix, dist, error
    error_occurred = pyqtSignal(str)

    def __init__(self):
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
    def process_frame(self, frame):
        """
        Procesa un frame para detectar corners ChArUco.
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
                status_text = f"✓ Frame capturado! Total: {self._calibration_frames_count} (min. 10)"
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

    def set_should_capture(self, value: bool):
        """ Setter para el flag de captura """
        if self._last_detection is not None and self._last_detection[2] >= 6:
            self._should_capture = value
            return True
        return False

    def run_calibration(self):
        """ Ejecuta el algoritmo de calibración con los datos acumulados """
        if self._calibration_frames_count < 10:
            self.error_occurred.emit(
                f"Se necesitan al menos 10 frames. Capturados: {self._calibration_frames_count}")
            return

        try:
            valid_corners = []
            valid_ids = []

            for corners, ids in zip(self._all_corners, self._all_ids):
                if corners is not None and ids is not None:
                    corners = np.asarray(corners, dtype=np.float32)
                    ids = np.asarray(ids, dtype=np.int32)
                    if len(corners) >= 4:
                        if corners.ndim == 2:
                            corners = corners.reshape(-1, 1, 2)
                        valid_corners.append(corners)
                        valid_ids.append(ids.reshape(-1, 1))

            flags = cv2.CALIB_RATIONAL_MODEL
            ret, camera_matrix, dist_coeffs, _, _ = cv2.aruco.calibrateCameraCharuco(
                charucoCorners=valid_corners,
                charucoIds=valid_ids,
                board=self._board,
                imageSize=self._image_size,
                cameraMatrix=None,
                distCoeffs=None,
                flags=flags
            )

            self.calibration_success.emit(camera_matrix, dist_coeffs, ret)

            # Limpiar datos tras éxito
            self.reset_data()

        except Exception as e:
            self.error_occurred.emit(f"Error en calibración: {str(e)}")

    def reset_data(self):
        """ Resetea los acumuladores """
        self._all_corners = []
        self._all_ids = []
        self._calibration_frames_count = 0
        self._last_detection = None

    # Getters explícitos
    def get_captured_count(self):
        return self._calibration_frames_count

    def get_image_size(self):
        return self._image_size

    def get_last_detection(self):
        return self._last_detection
