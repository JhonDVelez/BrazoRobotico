import os
import tempfile
import cv2
import numpy as np
from pathlib import Path
from PyQt6.QtGui import QPainter, QPen, QColor
from PyQt6.QtWidgets import QMessageBox
from gui import CameraInterface
from gui.main_window import ImageUtilsMixin
from data import config_manager as cfg


class CalibrationInterface(CameraInterface):
    save_pixmap = False
    _temporal_files = set()

    def __init__(self, parent):
        super().__init__(parent, is_calibration=True)
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(
            cv2.aruco.DICT_4X4_50)
        self.board = cv2.aruco.CharucoBoard(
            size=(12, 5),        # Número de cuadros (ancho, alto)
            squareLength=0.03,  # Tamaño del lado del cuadrado (metros)
            markerLength=0.022,  # Tamaño del lado del marcador ArUco (metros)
            dictionary=self.aruco_dict
        )

    def on_frame_ready(self, frame: np.ndarray | cv2.UMat):
        """Sobrescritura del método on_frame_ready para calibración (recibe numpy BGR)."""
        if frame is None:
            return

        if self.save_pixmap:
            self.save_temporal_frame(frame)
            self.save_pixmap = False
            return

        if not self.process_running:
            return
        pixmap = None
        # Convertir el frame numpy a pixmap solo para dibujar overlays
        if isinstance(frame, np.ndarray):
            pixmap = self.numpy_to_qpixmap(frame)
        elif isinstance(frame, cv2.UMat):
            pixmap = self.umat_to_pixmap(frame)

        if pixmap.isNull():
            return

        painter = QPainter(pixmap)
        w = pixmap.width()
        h = pixmap.height()

        w33 = int(w * .33)
        w66 = int(w * .66)
        h33 = int(h * .33)
        h66 = int(h * .66)

        pen = QPen(QColor(255, 255, 255, 127))
        pen.setWidth(1)
        painter.setPen(pen)

        painter.drawLine(w33, 0, w33, h)
        painter.drawLine(w66, 0, w66, h)
        painter.drawLine(0, h33, w, h33)
        painter.drawLine(0, h66, w, h66)
        painter.end()

        self.set_pixmap(pixmap)

    def save_temporal_frame(self, frame: np.ndarray, extension=".jpg"):
        """Guarda un frame numpy BGR en un archivo temporal."""
        try:
            if frame is None:
                return None

            fd, path_str = tempfile.mkstemp(suffix=extension)
            path = Path(path_str)
            os.close(fd)

            if cv2.imwrite(str(path), frame):
                self._temporal_files.add(path)
                return str(path)
            return None
        except Exception as e:
            print(f"Error al guardar frame temporal: {e}")
            return None

    def read_temporal_pixmap(self):
        """ Lee un archivo de imagen desde una ruta (string o Path).
        Retorna la imagen en formato OpenCV (BGR) o None si hay error.
        """
        try:
            all_corners, all_ids = [], []
            image_size = None

            # Convertimos a string por si se pasa un objeto Path,
            # ya que cv2.imread prefiere strings.
            for file in self._temporal_files:
                ruta_str = str(file)

                # Verificamos si el archivo existe antes de intentar leerlo
                if not os.path.exists(ruta_str):
                    print(f"Error: El archivo {ruta_str} no existe.")
                    return None

                # Leer la imagen
                img = cv2.imread(ruta_str)

                if img is None:
                    print(
                        f"Error: No se pudo decodificar la imagen en {ruta_str}")
                    return None

                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

                if image_size is None:
                    image_size = gray.shape[::-1]
                # Buscar las esquinas internas
                charuco_corners, charuco_ids, n = self.detect_corners(
                    gray, self.board, self.aruco_dict)
                if charuco_corners is not None and n >= 6:
                    all_corners.append(charuco_corners)
                    all_ids.append(charuco_ids)

                    # Feedback visual (presiona cualquier tecla para saltar a la siguiente foto más rápido)
                    # if charuco_corners is not None and charuco_ids is not None:
                    #     cv2.aruco.drawDetectedCornersCharuco(
                    #         img, charuco_corners, charuco_ids, (0, 255, 0))
                    # cv2.imshow('Detectando...', img)
                    # cv2.waitKey(500)
            print(f"Total de imágenes procesadas: {len(self._temporal_files)}")
            print(
                f"Imágenes con suficientes corners (>=6): {len(all_corners)}")
            camera_matrix = None
            dist_coeffs = None
            if len(all_corners) >= 10:
                ret, camera_matrix, dist_coeffs, _, _ = self.calibrate(
                    all_corners, all_ids, image_size, self.board)
                print(f"Error de reproyección: {ret}")
                if ret > 1.0:  # Umbral arbitrario, ajustar según necesidad
                    print("Error de reproyección alto, calibración posiblemente mala")
                    self.show_popup()
                    return

            if camera_matrix is None or dist_coeffs is None:
                self.show_popup()
                return

            print(f"matrix: {camera_matrix}")
            print(f"distortion: {dist_coeffs}")
            cfg.set_value("camera.json", "matrix",
                          value=np.array(camera_matrix).tolist())
            cfg.set_value("camera.json", "distortion coefficients",
                          value=np.array(dist_coeffs).tolist())
            # cfg.set_value("camera.json", "rvecs", np.array(rvecs).tolist())
            # cfg.set_value("camera.json", "tvecs", np.array(tvecs).tolist())
            # Limpiar archivos temporales
            for file in self._temporal_files:
                try:
                    os.remove(file)
                except OSError:
                    pass
            self._temporal_files.clear()
        except Exception as e:
            print(f"Error inesperado al leer el temporal: {e}")
            return

    def detect_corners(self, gray, board, aruco_dict):
        """Detecta corners ChArUco en una imagen en escala de grises."""
        params = cv2.aruco.DetectorParameters()

        detector = cv2.aruco.ArucoDetector(aruco_dict, params)
        marker_corners, marker_ids, _ = detector.detectMarkers(gray)

        print(
            f"Marcadores detectados: {len(marker_ids) if marker_ids is not None else 0}")
        if marker_ids is not None:
            print(f"IDs de marcadores: {marker_ids.flatten()}")

        if marker_ids is None or len(marker_ids) < 4:
            return None, None, 0

        charuco_detector = cv2.aruco.CharucoDetector(board)
        charuco_corners, charuco_ids, _, _ = charuco_detector.detectBoard(
            image=gray, markerCorners=marker_corners, markerIds=marker_ids
        )

        n = len(charuco_corners) if charuco_corners is not None else 0
        print(f"Corners ChArUco detectados: {n}")
        if charuco_corners is not None and n > 0:
            print(f"Primeros 5 corners: {charuco_corners[:5].flatten()}")
            print(
                f"IDs ChArUco: {charuco_ids.flatten() if charuco_ids is not None else 'None'}")
        return charuco_corners, charuco_ids, n

    def calibrate(self, all_corners, all_ids, image_size, board):
        """Ejecuta la calibración y retorna los parámetros."""
        flags = (
            cv2.CALIB_RATIONAL_MODEL       # Modelo de distorsión de 8 coeficientes
        )
        ret, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.aruco.calibrateCameraCharuco(
            charucoCorners=all_corners,
            charucoIds=all_ids,
            board=board,
            imageSize=image_size,
            cameraMatrix=None,
            distCoeffs=None,
            flags=flags
        )
        return ret, camera_matrix, dist_coeffs, rvecs, tvecs

    def show_popup(self):
        # Create a QMessageBox instance
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Error de Calibración")
        dlg.setText("No se pudo realizar la calibración. Verifica que el tablero ChArUco sea visible en las imágenes y que haya suficientes puntos detectados.")
        # Set standard buttons and icon
        dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
        dlg.setIcon(QMessageBox.Icon.Warning)
        # Execute the dialog (makes it modal and blocks interaction with the parent)
        dlg.exec()
