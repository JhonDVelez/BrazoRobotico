import numpy as np
import cv2
from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QWaitCondition
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
        self._running = False
        self._paused = False
        self.mutex = QMutex()
        self.wait_condition = QWaitCondition()

    def run(self):
        """Bucle principal del hilo de video
        """
        try:
            # Inicializar cámara en el hilo de trabajo
            self.camera_chess_board = CameraChessBoard(self.camera_index)

            if not self.camera_chess_board.camera_on():
                self.error_occurred.emit("No se pudo inicializar la cámara")
                return

            self._running = True

            while self._running:
                # Verificar si está pausado
                self.mutex.lock()
                if self._paused:
                    self.wait_condition.wait(self.mutex)
                self.mutex.unlock()

                if not self._running:
                    break

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

        finally:
            self.__cleanup()

    def __numpy_to_qpixmap(self, frame: np.ndarray) -> QPixmap:
        """ Convierte frame numpy a QPixmap
        """
        try:
            height, width, channels = frame.shape
            bytes_per_line = channels * width

            # Asegurarse de que los datos están en formato continuo
            frame = np.ascontiguousarray(frame)

            # Crear QImage
            q_image = QImage(
                frame.data,
                width,
                height,
                bytes_per_line,
                QImage.Format.Format_RGB888
            )

            # Convertir a QPixmap
            return QPixmap.fromImage(q_image)

        except (AttributeError, ValueError, TypeError) as e:
            print(f"El frame no cuenta con el formato adecuado: {e}")
            return QPixmap()

        except cv2.error as e:
            print(f"Error de OpenCV en conversión de frame: {e}")
            return QPixmap()

    def stop(self):
        """ Detiene el hilo de video
        """
        self.mutex.lock()
        self._running = False
        self._paused = False
        self.wait_condition.wakeAll()
        self.mutex.unlock()

        # Esperar a que termine el hilo
        if not self.wait(2000):  # Reducido a 2 segundos
            print("Warning: Video thread no terminó correctamente, forzando terminación")
            self.terminate()
            self.wait(1000)  # Esperar 1 segundo más tras terminate

    def __cleanup(self):
        """ Limpia recursos al terminar
        """
        if self.camera_chess_board:
            try:
                self.camera_chess_board.camera_off()
            except (AttributeError, TypeError) as e:
                print(f"No fue posible apagar la camara: {e}")
            self.camera_chess_board = None
