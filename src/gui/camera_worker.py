""" Modulo donde se implementa el hilo de procesamiento para la captura y el procesamiento de las 
    imágenes provenientes de la cámara
"""
import numpy as np
import cv2
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage
from vision.camera_chessboard import CameraChessBoard


class VideoWorker(QThread):
    """ Worker thread para manejar la captura y procesamiento de video.
        Funciona de forma asíncrona para no bloquear el hilo principal de la GUI.
    """

    # Señales para comunicación con el hilo principal (GUI)
    # frame_ready envía la imagen lista para mostrar, error_occurred notifica fallos
    frame_ready = pyqtSignal(QPixmap)
    error_occurred = pyqtSignal(str)

    def __init__(self, camera_index: int = 0):
        super().__init__()
        self.camera_index = camera_index
        self.camera_chess_board = None

        # Variables de control de estado del hilo
        self._running = True # Controla si el bucle while sigue activo
        self._paused = False # Controla si se saltan los pasos de captura
        
        # Inicialización del objeto de visión encargado de la lógica de cámara y calibración
        self.camera_chess_board = CameraChessBoard()

    def run(self):
        """ Método principal que se ejecuta al llamar a .start(). 
            Contiene el bucle de captura de video.
        """
        try:
            # Intento de encendido de la cámara física a través del objeto de visión
            if not self.camera_chess_board.camera_on():
                self.error_occurred.emit("No se pudo inicializar la cámara")
                return

            # Bucle infinito de procesamiento de frames
            while self._running:
                if not self._running:
                    break
                
                # Solo procesa si no está en estado de pausa
                if not self._paused:
                    try:
                        # Obtiene el frame procesado (puede incluir detección de tablero u otros)
                        frame = self.camera_chess_board.get_video_frame()
                        
                        if frame is not None:
                            # Conversión crítica: de formato NumPy (OpenCV) a QPixmap (Qt)
                            pixmap = self.__numpy_to_qpixmap(frame)
                            
                            # Si la conversión es exitosa, se emite la señal hacia la interfaz
                            if not pixmap.isNull():
                                self.frame_ready.emit(pixmap)

                    except (AttributeError, ValueError, TypeError) as e:
                        # Captura errores de formato en el flujo de datos
                        self.error_occurred.emit(f"Frame inválido: {e}")

                    except cv2.error as e:
                        # Errores específicos de la librería de visión computacional OpenCV
                        self.error_occurred.emit(f"Error de OpenCV: {e}")

        except (OSError, RuntimeError) as e:
            # Errores de hardware o de ejecución del hilo
            self.error_occurred.emit(f"Error en worker thread: {e}")

    def __numpy_to_qpixmap(self, frame: np.ndarray) -> QPixmap:
        """ Método privado para convertir un frame de tipo numpy (BGR) a QPixmap.
            Este paso es necesario porque Qt no puede renderizar matrices de NumPy directamente.
        """
        try:
            # Asegura que los datos en memoria estén alineados y sean del tipo correcto (8 bits)
            frame = np.ascontiguousarray(frame, dtype=np.uint8)

            height, width, channels = frame.shape
            
            # Caso estándar: Imágenes a color de 3 canales (Blue, Green, Red)
            if channels == 3:
                bytes_per_line = channels * width
                # Se crea una QImage interpretando los datos como BGR888
                q_image = QImage(frame.data, width, height,
                                  bytes_per_line, QImage.Format.Format_BGR888)
                return QPixmap.fromImage(q_image)
            else:
                # Caso especial: Imágenes con canal Alpha (transparencia) o formatos no estándar
                # Se intenta normalizar a BGR para su correcta visualización
                bgr = cv2.cvtColor(
                    frame, cv2.COLOR_RGBA2BGR) if channels == 4 else frame
                bgr = np.ascontiguousarray(bgr)
                bytes_per_line = 3 * width
                q_image = QImage(bgr.data, width, height,
                                  bytes_per_line, QImage.Format.Format_BGR888)
                return QPixmap.fromImage(q_image)

        except (AttributeError, ValueError, TypeError) as e:
            # Notificación de error de formato en consola
            print(f"El frame no cuenta con el formato adecuado: {e}")
            return QPixmap()

        except cv2.error as e:
            # Notificación de error de procesamiento OpenCV en consola
            print(f"Error de OpenCV en conversión de frame: {e}")
            return QPixmap()

    def stop(self):
        """ Detiene el hilo de forma segura, dando tiempo a que el bucle actual termine.
        """
        self._running = False
        self._paused = False

        # Se otorga un tiempo de espera (2 seg) antes de forzar la terminación
        if not self.wait(2000):
            print("Warning: Video thread no terminó correctamente, forzando terminación")
            self.terminate() # Cierre forzoso si el hilo se queda colgado
            self.wait(1000)

    def pause(self):
        """ Activa la bandera de pausa para detener la captura sin cerrar la cámara.
        """
        self._paused = True

    def resume(self):
        """ Desactiva la bandera de pausa para continuar con la captura.
        """
        self._paused = False