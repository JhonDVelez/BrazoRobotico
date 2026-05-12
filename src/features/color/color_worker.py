import cv2
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

class ColorWorker(QObject):
    """
    Worker encargado exclusivamente del procesamiento de imágenes para calibración de color HSV.
    Calcula la máscara y el resultado final basándose en los rangos proporcionados.
    """
    # Señal que envía los frames procesados: (original, mascara, resultado)
    processing_finished = pyqtSignal(np.ndarray, np.ndarray, np.ndarray)
    
    def __init__(self):
        super().__init__()
        self._hsv_ranges = {
            "h_min": 0, "s_min": 0, "v_min": 0,
            "h_max": 180, "s_max": 255, "v_max": 255
        }

    @pyqtSlot(object)
    def process_frame(self, frame):
        """
        Aplica el filtro HSV al frame recibido.
        """
        if frame is None:
            return

        if isinstance(frame, cv2.UMat):
            frame_np = frame.get()
        else:
            frame_np = frame.copy()

        # Convertir a HSV
        hsv = cv2.cvtColor(frame_np, cv2.COLOR_BGR2HSV)
        
        # Definir rangos
        lower = np.array([
            self._hsv_ranges["h_min"],
            self._hsv_ranges["s_min"],
            self._hsv_ranges["v_min"]
        ], dtype=np.uint8)
        
        upper = np.array([
            self._hsv_ranges["h_max"],
            self._hsv_ranges["s_max"],
            self._hsv_ranges["v_max"]
        ], dtype=np.uint8)

        # Generar máscara y resultado
        mask = cv2.inRange(hsv, lower, upper)
        result = cv2.bitwise_and(frame_np, frame_np, mask=mask)
        
        # Convertir máscara a BGR para visualización uniforme
        mask_bgr = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
        
        self.processing_finished.emit(frame_np, mask_bgr, result)

    def set_hsv_ranges(self, ranges: dict):
        """ Setter explícito para los rangos HSV """
        self._hsv_ranges.update(ranges)

    def get_hsv_ranges(self):
        """ Getter explícito para los rangos HSV """
        return self._hsv_ranges.copy()
