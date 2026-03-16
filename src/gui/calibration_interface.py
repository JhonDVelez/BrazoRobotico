import os
import tempfile
import cv2
import numpy as np
from pathlib import Path
from PyQt6.QtGui import QPainter, QPen, QColor
from PyQt6.QtCore import Qt
from gui import CameraInterface
from gui.main_window import ImageUtilsMixin
from data import config_manager as cfg


class CalibrationInterface(CameraInterface):
    save_pixmap = False
    _temporal_files = set()

    def __init__(self, parent):
        super().__init__(parent)

    def on_frame_ready(self, frame: np.ndarray):
        """Sobrescritura del método on_frame_ready para calibración (recibe numpy BGR)."""
        if frame is None:
            return

        if self.save_pixmap:
            self.save_temporal_frame(frame)
            self.save_pixmap = False
            return

        if not self.process_running:
            return

        # Convertir el frame numpy a pixmap solo para dibujar overlays
        pixmap = self.numpy_to_qpixmap(frame)
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
            columnas = 7
            filas = 7
            dimensiones_tablero = (columnas, filas)

            # Tamaño real de un cuadrado del tablero en tu unidad de medida (ej. 25.0 milímetros)
            tamano_cuadrado = 25.0

            # --- 2. PREPARACIÓN DE PUNTOS ---
            criterios = (cv2.TERM_CRITERIA_EPS +
                         cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

            # Preparar la cuadrícula 3D teórica: (0,0,0), (25,0,0), (50,0,0)...
            puntos_obj_base = np.zeros((filas * columnas, 3), np.float32)
            puntos_obj_base[:, :2] = np.mgrid[0:columnas,
                                              0:filas].T.reshape(-1, 2)
            puntos_obj_base = puntos_obj_base * tamano_cuadrado

            puntos_objeto = []  # Puntos 3D reales en el espacio
            puntos_imagen = []  # Puntos 2D detectados en las imágenes

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

                gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                # Buscar las esquinas internas
                ret, esquinas = cv2.findChessboardCorners(
                    gris, dimensiones_tablero, None)

                if ret == True:
                    puntos_objeto.append(puntos_obj_base)

                    # Refinar las coordenadas para precisión sub-píxel
                    esquinas_refinadas = cv2.cornerSubPix(
                        gris, esquinas, (11, 11), (-1, -1), criterios)
                    puntos_imagen.append(esquinas_refinadas)

                    # Feedback visual (presiona cualquier tecla para saltar a la siguiente foto más rápido)
                    # cv2.drawChessboardCorners(
                    #     img, dimensiones_tablero, esquinas_refinadas, ret)
                    # cv2.imshow('Detectando...', img)
                    # cv2.waitKey(500)

            # cv2.destroyAllWindows()
            ret, camera_matrix, dist_coeffs, _, _ = cv2.calibrateCamera(
                puntos_objeto, puntos_imagen, gris.shape[::-1], None, None
            )
            cfg.set_value("camera.json", "matrix",
                          np.array(camera_matrix).tolist())
            cfg.set_value("camera.json", "distortion coefficients",
                          np.array(dist_coeffs).tolist())
            # cfg.set_value("camera.json", "rvecs", np.array(rvecs).tolist())
            # cfg.set_value("camera.json", "tvecs", np.array(tvecs).tolist())
        except Exception as e:
            print(f"Error inesperado al leer el temporal: {e}")
            return None
