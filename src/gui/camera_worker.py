import numpy as np
import cv2
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage
from vision.camera_chessboard import CameraChessBoard


class VideoWorker(QThread):
    """Worker thread para manejar la captura y procesamiento de video
    """

    # Señales para comunicación con el hilo principal
    frame_ready = pyqtSignal(QPixmap)
    error_occurred = pyqtSignal(str)

    def __init__(self, camera_index: int = 0):
        super().__init__()
        self.camera_index = camera_index
        self.camera_chess_board = None

        # Control de hilo
        self._running = True
        self._paused = False
        # Inicializar cámara en el hilo de trabajo
        self.camera_chess_board = CameraChessBoard(self.camera_index)

    def run(self):
        """ Bucle principal del hilo de video
        """
        try:

            if not self.camera_chess_board.camera_on():
                self.error_occurred.emit("No se pudo inicializar la cámara")
                return

            while self._running:
                if not self._running:
                    break
                if not self._paused:
                    try:
                        # Capturar y procesar frame
                        frame = self.camera_chess_board.get_video_frame()
                        if frame is not None:
                            # Convertir a QPixmap en el hilo de trabajo
                            pixmap = self.__numpy_to_qpixmap(frame)
                            if not pixmap.isNull():
                                self.frame_ready.emit(pixmap)

                    except (AttributeError, ValueError, TypeError) as e:
                        # Errores típicos de conversión/validación del frame
                        self.error_occurred.emit(f"Frame inválido: {e}")

                    except cv2.error as e:
                        # Errores propios de OpenCV
                        self.error_occurred.emit(f"Error de OpenCV: {e}")

        except (OSError, RuntimeError) as e:
            # Errores al inicializar la cámara u otros recursos
            self.error_occurred.emit(f"Error en worker thread: {e}")

    def __numpy_to_qpixmap(self, frame: np.ndarray) -> QPixmap:
        """ Convierte frame numpy BGR a QPixmap
        """
        try:
            # Asegurarse de uint8 contiguous
            frame = np.ascontiguousarray(frame, dtype=np.uint8)

            # frame shape
            if frame.ndim == 2:
                height, width = frame.shape
                bytes_per_line = width
                q_image = QImage(frame.data, width, height,
                                 bytes_per_line, QImage.Format.Format_Grayscale8)
                return QPixmap.fromImage(q_image)

            height, width, channels = frame.shape
            if channels == 3:
                bytes_per_line = channels * width
                q_image = QImage(frame.data, width, height,
                                 bytes_per_line, QImage.Format.Format_BGR888)
                return QPixmap.fromImage(q_image)
            else:
                # si no es 3 canales, intentar convertir a BGR
                bgr = cv2.cvtColor(
                    frame, cv2.COLOR_RGBA2BGR) if channels == 4 else frame
                bgr = np.ascontiguousarray(bgr)
                bytes_per_line = 3 * width
                q_image = QImage(bgr.data, width, height,
                                 bytes_per_line, QImage.Format.Format_BGR888)
                return QPixmap.fromImage(q_image)

        except (AttributeError, ValueError, TypeError) as e:
            print(f"El frame no cuenta con el formato adecuado: {e}")
            return QPixmap()

        except cv2.error as e:
            print(f"Error de OpenCV en conversión de frame: {e}")
            return QPixmap()

    def stop(self):
        """ Detiene el hilo de video"""
        self._running = False
        self._paused = False

        # Esperar a que termine el hilo
        if not self.wait(2000):  # 2 segundos
            print("Warning: Video thread no terminó correctamente, forzando terminación")
            self.terminate()
            self.wait(1000)  # Esperar 1 segundo tras terminate

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

