"""Módulo para la interfaz de calibración de colores HSV.

Maneja el procesamiento y visualización de:
- Imagen original
- Máscara de color aplicada
- Máscara aplicada a la imagen original
"""
import numpy as np
import cv2
from PyQt6.QtWidgets import QWidget, QGridLayout, QLabel
from PyQt6.QtCore import Qt
from gui import CameraInterface


class ColorInterface(CameraInterface):
    """Interfaz para calibración de colores HSV con visualización de 3 imágenes."""

    def __init__(self, parent):
        super().__init__(parent, is_calibration=True)
        self.hsv_values = {
            "h_min": 0,
            "s_min": 0,
            "v_min": 0,
            "h_max": 180,
            "s_max": 255,
            "v_max": 255,
        }
        self._setup_image_display()

    def _setup_image_display(self):
        """Configura el layout para mostrar las 3 imágenes."""
        # Limpiamos el layout anterior
        while self.main_layout.count():
            self.main_layout.takeAt(0).widget().deleteLater()

        # Creamos un widget contenedor para las 3 imágenes
        images_container = QWidget()
        images_layout = QGridLayout(images_container)
        images_layout.setContentsMargins(5, 5, 5, 5)
        images_layout.setSpacing(5)

        # Imagen 1: Original
        self.label_original = QLabel()
        self.label_original.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_original.setMinimumSize(200, 150)
        images_layout.addWidget(self.label_original, 0, 0)

        # Imagen 2: Máscara de color
        self.label_mask = QLabel()
        self.label_mask.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_mask.setMinimumSize(200, 150)
        images_layout.addWidget(self.label_mask, 0, 1)

        # Imagen 3: Máscara aplicada
        self.label_result = QLabel()
        self.label_result.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_result.setMinimumSize(200, 150)
        images_layout.addWidget(self.label_result, 1, 0)

        self.main_layout.addWidget(images_container)

    def update_hsv_values(self, h_min: int, s_min: int, v_min: int,
                          h_max: int, s_max: int, v_max: int):
        """Actualiza los valores HSV para el filtrado.

        Args:
            h_min, s_min, v_min: Valores mínimos
            h_max, s_max, v_max: Valores máximos
        """
        self.hsv_values = {
            "h_min": h_min,
            "s_min": s_min,
            "v_min": v_min,
            "h_max": h_max,
            "s_max": s_max,
            "v_max": v_max,
        }

    def on_frame_ready(self, frame: np.ndarray | cv2.UMat):
        """Sobrescritura del método on_frame_ready para calibración.

        Recibe un frame y lo procesa para mostrar:
        1. Imagen original
        2. Máscara de color
        3. Máscara aplicada a la imagen original

        Args:
            frame: Frame BGR (numpy.ndarray o cv2.UMat)
        """
        if frame is None or not self.process_running:
            return

        # Convertir a numpy si es UMat
        if isinstance(frame, cv2.UMat):
            frame = frame.get()

        # Convertir BGR a HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Crear máscara con los valores HSV actuales
        lower = np.array([
            self.hsv_values["h_min"],
            self.hsv_values["s_min"],
            self.hsv_values["v_min"]
        ], dtype=np.uint8)

        upper = np.array([
            self.hsv_values["h_max"],
            self.hsv_values["s_max"],
            self.hsv_values["v_max"]
        ], dtype=np.uint8)

        mask = cv2.inRange(hsv, lower, upper)

        # Aplicar la máscara a la imagen original
        result = cv2.bitwise_and(frame, frame, mask=mask)

        # Mostrar las 3 imágenes
        # 1. Original
        pixmap_original = self.numpy_to_qpixmap(frame)
        if not pixmap_original.isNull():
            scaled = pixmap_original.scaledToWidth(
                300, Qt.TransformationMode.SmoothTransformation)
            self.label_original.setPixmap(scaled)

        # 2. Máscara de color
        mask_bgr = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
        pixmap_mask = self.numpy_to_qpixmap(mask_bgr)
        if not pixmap_mask.isNull():
            scaled = pixmap_mask.scaledToWidth(
                300, Qt.TransformationMode.SmoothTransformation)
            self.label_mask.setPixmap(scaled)

        # 3. Máscara aplicada a la original
        pixmap_result = self.numpy_to_qpixmap(result)
        if not pixmap_result.isNull():
            scaled = pixmap_result.scaledToWidth(
                300, Qt.TransformationMode.SmoothTransformation)
            self.label_result.setPixmap(scaled)
