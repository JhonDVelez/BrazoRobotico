from typing import Optional, Tuple
import numpy as np
from vision.chessboard import ChessboardDetector
from vision.camera import CameraControl


class CameraChessBoard():
    """ Cámara especializada para detección de tableros de ajedrez usando preprocesado con UMat.
        Esta clase orquesta la captura de video, la mejora de imagen y la localización
        del tablero para proporcionar coordenadas espaciales al robot.
    """

    def __init__(self, board_size: Tuple[int, int] = (7, 7)):
        """ Inicializa los controladores de visión y cámara.
        
        Args:
            board_size (Tuple): Número de esquinas internas del tablero (columnas, filas).
                                Por defecto (7, 7) para un tablero estándar.
        """
        self.detector = ChessboardDetector(board_size) # Instancia el detector de esquinas
        self.camera = CameraControl()                  # Instancia el control de hardware de la cámara

        # Cache para optimización de rendimiento
        self.corners = None                # Almacena las últimas esquinas detectadas exitosamente
        self._detection_cache_frames = 0   # Contador interno de frames procesados
        self._detection_interval = 3       # Define que la detección pesada solo ocurre cada 3 frames

    def camera_on(self):
        """ Inicializa el flujo de video del hardware.
            Returns: bool indicando si la cámara se activó correctamente.
        """
        return self.camera.camera_on()

    def camera_off(self):
        """ Libera el recurso de la cámara y detiene la captura. """
        self.camera.camera_off()

    def get_coordinates(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """ Obtiene coordenadas del tablero y retorna el frame con el feedback visual.
            Aplica preprocesado acelerado (UMat) para la corrección gamma y luego realiza
            la detección cada N frames. La detección de esquinas se hace en CPU.
            
            Args:
                frame: Imagen cruda capturada por la cámara.
            Returns:
                Frame procesado con el grid dibujado o None si el frame es inválido.
        """
        if frame is None:
            return None
            
        try:
            # Mejora la imagen automáticamente (brillo/contraste) antes de buscar el tablero
            pre = self.camera.auto_gamma_correction(frame)
        except Exception:
            # Si la corrección falla, continúa con el frame original para no detener el flujo
            pre = frame

        # Lógica de detección intermitente (Detección cada N frames para ahorrar CPU)
        self._detection_cache_frames += 1
        if self._detection_cache_frames >= self._detection_interval:
            try:
                # Intenta localizar las esquinas del tablero en la imagen preprocesada
                self.corners = self.detector.detect_corners(pre)
            except Exception as e:
                print(f"Error detectando esquinas: {e}")
                self.corners = None
            # Reinicia el contador de frames para la siguiente detección
            self._detection_cache_frames = 0

        # Preparar la salida visual: Copia el frame original para dibujar sobre él
        out_frame = frame.copy()
        if self.corners is not None:
            try:
                # Si hay esquinas en caché, dibuja la cuadrícula sobre el video
                # El parámetro False, False indica que no se requiere rotación o dibujo de ejes extra aquí
                self.detector.draw_grid(out_frame, self.corners, False, False)
            except Exception as e:
                print(f"Error dibujando grid: {e}")

        return out_frame

    def get_video_frame(self):
        """ Método principal para obtener un frame listo para ser mostrado en la GUI.
            Realiza la captura y el procesamiento en una sola llamada.
            
            Returns:
                np.ndarray: Frame procesado listo para la interfaz.
            Raises:
                IOError: Si no hay comunicación con la cámara.
        """
        frame = self.camera.take_frame() # Captura frame de la cámara
        if frame is None:
            raise IOError("No se pudo obtener frame de la cámara")

        try:
            # Intenta procesar el tablero en el frame capturado
            frame_processed = self.get_coordinates(frame)
            # Retorna el frame con grid si fue exitoso, de lo contrario el frame original
            return frame_processed if frame_processed is not None else frame
        except RuntimeError as e:
            print(f"Error procesando frame: {e}")
            return frame