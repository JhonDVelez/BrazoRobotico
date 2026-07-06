"""
Módulo encargado del procesamiento de color en el espacio HSV.

Este módulo define la clase ColorWorker, la cual aplica filtros de color
dinámicos sobre el feed de video para ayudar en la calibración de detección
de objetos por color.

Conexiones:
    - Recibe frames de `CameraWorker`.
    - Emite `processing_finished` con el frame original, máscara y resultado.
"""

import cv2
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot


class ColorWorker(QObject):
    """
    Worker encargado del procesamiento de imágenes para calibración de color HSV.

    Calcula máscaras binarias y aplica operaciones bitwise para aislar colores
    específicos basados en rangos de Hue, Saturation y Value.

    Attributes:
        processing_finished (pyqtSignal): Emite (original, máscara, resultado) en formato np.ndarray.
    """
    # Señal que envía los frames procesados: (original, máscara, resultado)
    processing_finished = pyqtSignal(np.ndarray, np.ndarray, np.ndarray)

    def __init__(self):
        """
        Inicializa el worker con rangos HSV que abarcan todo el espectro por defecto.
        """
        super().__init__()
        self._hsv_ranges = {
            "h_min": 0, "s_min": 0, "v_min": 0,
            "h_max": 180, "s_max": 255, "v_max": 255
        }

    @pyqtSlot(object)
    def process_frame(self, frame):
        """
        Aplica el filtro HSV al frame recibido y genera la visualización de calibración.

        Args:
            frame (np.ndarray | cv2.UMat): Imagen original capturada por la cámara.
        """
        if frame is None:
            return

        if isinstance(frame, cv2.UMat):
            frame_np = frame.get()
        else:
            frame_np = frame.copy()

        # Convertir a HSV para facilitar el filtrado de color
        hsv = cv2.cvtColor(frame_np, cv2.COLOR_BGR2HSV)

        # Definir limites del filtro
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

        # Generar máscara binaria y aplicar al frame original
        mask = cv2.inRange(hsv, lower, upper)
        result = cv2.bitwise_and(frame_np, frame_np, mask=mask)

        # Convertir máscara a BGR para visualización uniforme en los widgets de imagen
        mask_bgr = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)

        self.processing_finished.emit(frame_np, mask_bgr, result)

    def set_hsv_ranges(self, ranges: dict):
        """
        Actualiza los rangos de filtrado HSV.

        Args:
            ranges (dict): Diccionario con claves h_min, h_max, etc.
        """
        self._hsv_ranges.update(ranges)

    def get_hsv_ranges(self):
        """
        Obtiene una copia de los rangos HSV actuales.

        Returns:
            dict: Configuración de filtrado.
        """
        return self._hsv_ranges.copy()
