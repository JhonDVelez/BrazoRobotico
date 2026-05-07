import cv2
import numpy as np
from PyQt6.QtGui import QPainter, QPen, QColor, QFont
from PyQt6.QtWidgets import QMessageBox, QWidget, QGridLayout, QLabel, QVBoxLayout, QDialog, QPushButton
from PyQt6.QtCore import Qt
from gui import CameraInterface
from gui.main_window import ImageUtilsMixin
from data import config_manager as cfg


class CalibrationInterface(CameraInterface):
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
        # Variables para almacenar datos de calibración
        self.all_corners = []
        self.all_ids = []
        self.image_size = None
        self.calibration_frames_count = 0
        self.should_capture = False  # Flag para captura manual
        self.last_detection = None  # Almacena la última detección para mostrar

    def on_frame_ready(self, frame: np.ndarray | cv2.UMat):
        """Procesamiento de frames para calibración con detección visualización en vivo."""
        if frame is None or not self.process_running:
            return

        # Convertir frame a numpy BGR si es necesario
        if isinstance(frame, cv2.UMat):
            frame = cv2.UMat.get(frame)

        # Convertir a escala de grises para detección
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Guardar tamaño de imagen en la primera detección
        if self.image_size is None:
            self.image_size = gray.shape[::-1]

        # Detectar corners en tiempo real
        charuco_corners, charuco_ids, n = self.detect_corners(
            gray, self.board, self.aruco_dict)

        # Dibujar los puntos detectados en el frame
        frame_display = frame.copy()

        # Si se detectaron suficientes corners
        if charuco_corners is not None and n >= 6:
            self.last_detection = (charuco_corners, charuco_ids, n)

            # Dibujar los corners detectados con color verde
            cv2.aruco.drawDetectedCornersCharuco(
                frame_display, charuco_corners, charuco_ids, (0, 255, 0))

            # Si se presionó el botón de captura, guardar datos
            if self.should_capture:
                self.all_corners.append(charuco_corners.copy())
                self.all_ids.append(charuco_ids.copy())
                self.calibration_frames_count += 1
                self.should_capture = False
                text = f"✓ Frame capturado! Total: {self.calibration_frames_count} (min. 10)"
                color = (0, 255, 0)  # Verde para captura exitosa
            else:
                text = f"Presiona 'Capturar Imagen' para guardar (Total: {self.calibration_frames_count})"
                color = (255, 165, 0)  # Naranja para standby

            cv2.putText(frame_display, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                        0.6, color, 2)
        else:
            # Mostrar mensaje si no se detectaron suficientes corners
            text = "Posiciona el tablero ChArUco en la camara"
            cv2.putText(frame_display, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (0, 0, 255), 2)

        # Convertir a pixmap y mostrar
        pixmap = self.numpy_to_qpixmap(frame_display)
        if not pixmap.isNull():
            self.set_video_image(pixmap)

    def calibrate_camera_from_data(self):
        """Calibra la cámara usando los datos detectados guardados."""
        try:
            if len(self.all_corners) < 10:
                self.show_popup(
                    "Error de Calibración",
                    f"Se necesitan al menos 10 frames con puntos detectados.\n"
                    f"Frames capturados: {len(self.all_corners)}"
                )
                return

            # print(f"Total de frames capturados: {len(self.all_corners)}")

            # Validar y limpiar datos
            valid_corners = []
            valid_ids = []

            for corners, ids in zip(self.all_corners, self.all_ids):
                if corners is not None and ids is not None:
                    # Convertir a formato numpy si es necesario
                    corners = np.asarray(corners, dtype=np.float32)
                    ids = np.asarray(ids, dtype=np.int32)

                    # Verificar que tengan la forma correcta
                    if len(corners) >= 4 and len(ids) >= 4:
                        # Asegurar que corners sea (n, 1, 2)
                        if corners.ndim == 2:
                            corners = corners.reshape(-1, 1, 2)
                        elif corners.ndim == 3 and corners.shape[1] != 1:
                            corners = corners.reshape(-1, 1, 2)

                        valid_corners.append(corners.astype(np.float32))
                        valid_ids.append(ids.reshape(-1, 1).astype(np.int32))

            if len(valid_corners) < 10:
                self.show_popup(
                    "Error de Calibración",
                    f"Solo se encontraron {len(valid_corners)} frames con datos válidos.\n"
                    f"Se necesitan al menos 10 frames."
                )
                return

            # print(f"Frames válidos para calibración: {len(valid_corners)}")

            camera_matrix = None
            dist_coeffs = None

            try:
                ret, camera_matrix, dist_coeffs, _, _ = self.calibrate(
                    valid_corners, valid_ids, self.image_size, self.board)

                # print(f"Error de reproyección: {ret}")

                if ret > 1.0:
                    # print("Error de reproyección alto, calibración posiblemente mala")
                    self.show_popup(
                        "Advertencia de Calibración",
                        f"El error de reproyección es alto ({ret:.4f}).\n"
                        f"La calibración puede no ser óptima.\n"
                        f"Intenta de nuevo con más frames o mejor iluminación."
                    )

            except cv2.error as cv_error:
                error_msg = str(cv_error)
                # print(f"Error de OpenCV: {error_msg}")
                self.show_popup(
                    "Error de OpenCV",
                    f"Error durante la calibración:\n{error_msg}\n\n"
                    f"Verifica que:\n"
                    f"- El tablero ChArUco sea visible claramente\n"
                    f"- Los frames sean capturados desde ángulos diferentes\n"
                    f"- La iluminación sea adecuada"
                )
                return

            if camera_matrix is None or dist_coeffs is None:
                self.show_popup(
                    "Error de Calibración",
                    "No se pudo realizar la calibración. Verifica que el tablero ChArUco "
                    "sea visible en las imágenes."
                )
                return

            # Guardar en configuración
            cfg.set_value("camera.json", "matrix",
                          value=np.array(camera_matrix).tolist())
            cfg.set_value("camera.json", "distortion coefficients",
                          value=np.array(dist_coeffs).tolist())

            # Mostrar popup con la matriz formateada
            self.show_calibration_popup(camera_matrix, dist_coeffs, ret)

            # Limpiar datos después de calibración exitosa
            self.all_corners = []
            self.all_ids = []
            self.image_size = None
            self.calibration_frames_count = 0

        except Exception as e:
            # print(f"Error inesperado durante la calibración: {e}")
            import traceback
            traceback.print_exc()
            self.show_popup(
                "Error de Calibración",
                f"Error inesperado: {str(e)}"
            )

    def capture_frame(self):
        """Activa la captura del siguiente frame con detección de corners."""
        if self.last_detection is None or self.last_detection[2] < 6:
            self.show_popup(
                "Error de Captura",
                "No se detectan suficientes corners en la imagen actual.\n"
                "Posiciona el tablero ChArUco correctamente."
            )
            return

        self.should_capture = True

    def detect_corners(self, gray, board, aruco_dict):
        """Detecta corners ChArUco en una imagen en escala de grises."""
        params = cv2.aruco.DetectorParameters()

        detector = cv2.aruco.ArucoDetector(aruco_dict, params)
        marker_corners, marker_ids, _ = detector.detectMarkers(gray)

        # print(
            # f"Marcadores detectados: {len(marker_ids) if marker_ids is not None else 0}")
        # if marker_ids is not None:
            # print(f"IDs de marcadores: {marker_ids.flatten()}")

        if marker_ids is None or len(marker_ids) < 6:
            return None, None, 0

        charuco_detector = cv2.aruco.CharucoDetector(board)
        charuco_corners, charuco_ids, _, _ = charuco_detector.detectBoard(
            image=gray, markerCorners=marker_corners, markerIds=marker_ids
        )

        n = len(charuco_corners) if charuco_corners is not None else 0
        # print(f"Corners ChArUco detectados: {n}")
        # if charuco_corners is not None and n > 0:
            # print(f"Primeros 5 corners: {charuco_corners[:5].flatten()}")
            # print(
                # f"IDs ChArUco: {charuco_ids.flatten() if charuco_ids is not None else 'None'}")
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

    def show_popup(self, title, text):
        """Muestra un popup de mensaje simple."""
        dlg = QMessageBox(self)
        dlg.setWindowTitle(title)
        dlg.setText(text)
        dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
        dlg.setIcon(QMessageBox.Icon.Warning)
        dlg.exec()

    def show_calibration_popup(self, camera_matrix, dist_coeffs, reprojection_error):
        """Muestra un popup con la matriz de calibración en formato visual con QLabels."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Calibración Completada")
        dlg.setMinimumWidth(500)

        main_layout = QVBoxLayout(dlg)

        # Título de éxito
        title_label = QLabel("✓ La calibración ha sido exitosa")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title_label.setFont(title_font)
        main_layout.addWidget(title_label)

        # Error de reproyección
        error_label = QLabel(
            f"Error de reproyección: {reprojection_error:.4f}")
        main_layout.addWidget(error_label)

        # Matriz de cámara
        matrix_title = QLabel("Matriz de Cámara (3×3):")
        matrix_title_font = QFont()
        matrix_title_font.setBold(True)
        matrix_title.setFont(matrix_title_font)
        main_layout.addWidget(matrix_title)

        # Grid para la matriz
        matrix_grid = QGridLayout()
        matrix_grid.setSpacing(5)

        for i in range(3):
            for j in range(3):
                # Crear label para cada elemento
                value = camera_matrix[i, j]
                label = QLabel(f"{value:.4f}")
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)

                # Estilizar con bordes típicos de matrices
                if j == 0:
                    label.setStyleSheet(
                        "border: 1px solid black; border-right: 1px solid black; "
                        "padding: 8px; font-family: monospace; font-weight: bold;"
                    )
                elif j == 2:
                    label.setStyleSheet(
                        "border: 1px solid black; border-left: 1px solid black; "
                        "padding: 8px; font-family: monospace; font-weight: bold;"
                    )
                else:
                    label.setStyleSheet(
                        "border: 1px solid black; "
                        "padding: 8px; font-family: monospace; font-weight: bold;"
                    )

                # Agregar paréntesis visuales a los lados
                if j == 0 and i == 0:
                    label.setStyleSheet(
                        "border: 1px solid black; border-right: 1px solid black; "
                        "padding: 8px; font-family: monospace; font-weight: bold; "
                        "border-top-left-radius: 5px;"
                    )
                elif j == 2 and i == 0:
                    label.setStyleSheet(
                        "border: 1px solid black; border-left: 1px solid black; "
                        "padding: 8px; font-family: monospace; font-weight: bold; "
                        "border-top-right-radius: 5px;"
                    )
                elif j == 0 and i == 2:
                    label.setStyleSheet(
                        "border: 1px solid black; border-right: 1px solid black; "
                        "padding: 8px; font-family: monospace; font-weight: bold; "
                        "border-bottom-left-radius: 5px;"
                    )
                elif j == 2 and i == 2:
                    label.setStyleSheet(
                        "border: 1px solid black; border-left: 1px solid black; "
                        "padding: 8px; font-family: monospace; font-weight: bold; "
                        "border-bottom-right-radius: 5px;"
                    )

                matrix_grid.addWidget(label, i, j)

        main_layout.addLayout(matrix_grid)

        # Coeficientes de distorsión
        dist_title = QLabel("Coeficientes de Distorsión:")
        dist_title_font = QFont()
        dist_title_font.setBold(True)
        dist_title.setFont(dist_title_font)
        main_layout.addWidget(dist_title)

        # Manejo robusto de los coeficientes de distorsión (pueden ser 1D o 2D)
        if dist_coeffs.ndim == 2:
            dist_values = dist_coeffs[0]
        else:
            dist_values = dist_coeffs.flatten()

        dist_label = QLabel(", ".join([f"{x:.6f}" for x in dist_values]))
        dist_label.setStyleSheet(
            "font-family: monospace; border: 1px solid black; padding: 8px;")
        main_layout.addWidget(dist_label)

        # Botón OK
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(dlg.accept)
        main_layout.addWidget(ok_button)

        dlg.exec()

    def format_matrix(self, mat):
        """Formatea una matriz como string para mostrar en la consola."""
        str_mat = [[str(x) for x in row] for row in mat]
        max_width = max(len(x) for row in str_mat for x in row)

        lines = []
        for row in str_mat:
            formatted_row = " ".join(f"{x:^{max_width}}" for x in row)
            lines.append(f"| {formatted_row} |")

        return "\n".join(lines)
