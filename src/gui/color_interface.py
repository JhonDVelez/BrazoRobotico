
"""Funcionalidad de calibración HSV para ColorWindow."""
import cv2
import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel
from data import config_manager as cfg


class ColorInterface:
    """Coordina cámara, procesamiento HSV y guardado para ColorWindow."""

    COLORS = ["amarillo", "verde", "azul", "naranja", "morado"]
    VALUE_ORDER = ["h_min", "s_min", "v_min", "h_max", "s_max", "v_max"]
    DEFAULT_VALUES = {
        "h_min": 0,
        "s_min": 0,
        "v_min": 0,
        "h_max": 180,
        "s_max": 255,
        "v_max": 255,
    }

    def __init__(self, window):
        self.window = window
        self._last_frame = None

    @classmethod
    def load_default_values(cls):
        """Carga valores HSV iniciales para construir los sliders."""
        hsv_config = cfg.get("camera.json", "hsv_colors", default={})
        default_color = list(hsv_config.values())[0] if hsv_config else None
        if not default_color or len(default_color) < len(cls.VALUE_ORDER):
            return cls.DEFAULT_VALUES.copy()

        return {
            key: default_color[index]
            for index, key in enumerate(cls.VALUE_ORDER)
        }

    def setup_connections(self):
        """Conecta las señales de la ventana con la funcionalidad HSV."""
        if hasattr(self.window, 'save_button'):
            self.window.save_button.clicked.connect(self.save_color_config)
        if hasattr(self.window, 'camera_toggle_button'):
            self.window.camera_toggle_button.clicked.connect(self.toggle_camera)
        if hasattr(self.window, 'camera_interface'):
            self.window.camera_interface.frame_ready.connect(
                self._on_frame_received)

        for key, data in self.window.hsv_sliders.items():
            data["slider"].valueChanged.connect(
                lambda val, key=key: self.on_slider_changed(key, val))
            data["spinbox"].valueChanged.connect(
                lambda val, key=key: self.on_spinbox_changed(key, val))

    def on_slider_changed(self, key: str, value: int):
        """Sincroniza el spinbox y reprocesa la imagen."""
        spinbox = self.window.hsv_sliders[key]["spinbox"]
        spinbox.blockSignals(True)
        spinbox.setValue(value)
        spinbox.blockSignals(False)
        self._update_processed_views()

    def on_spinbox_changed(self, key: str, value: int):
        """Sincroniza el slider y reprocesa la imagen."""
        slider = self.window.hsv_sliders[key]["slider"]
        slider.blockSignals(True)
        slider.setValue(value)
        slider.blockSignals(False)
        self._update_processed_views()

    def toggle_camera(self):
        """Enciende o apaga la cámara del panel de calibración de color."""
        if self.window.camera_toggle_button.isChecked():
            self.window.camera_toggle_button.setText("Cámara ON")
            self.window.camera_interface.start_video()
        else:
            self.window.camera_toggle_button.setText("Cámara OFF")
            self.window.camera_interface.stop_video()
            self._clear_processed_images()

    def save_color_config(self):
        """Guarda la configuración HSV del color seleccionado."""
        values = [
            self.window.hsv_sliders[key]["spinbox"].value()
            for key in self.VALUE_ORDER
        ]
        color = self.window.color_selector.currentText()
        cfg.set_value("camera.json", "hsv_colors", color, value=values)
        print(f"Configuración de color guardada para {color}: {values}")

    def close(self):
        """Detiene la cámara al cerrar la ventana."""
        if hasattr(self.window, "camera_interface"):
            self.window.camera_interface.stop_video()

    def _get_hsv_values(self):
        """Obtiene los valores HSV actuales desde los spinbox."""
        return {
            key: data["spinbox"].value()
            for key, data in self.window.hsv_sliders.items()
        }

    def _on_frame_received(self, frame: np.ndarray | cv2.UMat):
        """Procesa cada frame recibido para actualizar máscara y resultado."""
        if frame is None:
            return

        if isinstance(frame, cv2.UMat):
            frame = frame.get()

        if not isinstance(frame, np.ndarray):
            return

        self._last_frame = frame.copy()
        self._update_processed_views(self._last_frame)

    def _update_processed_views(self, frame: np.ndarray | None = None):
        """Actualiza la máscara HSV y la imagen resultante."""
        frame = self._last_frame if frame is None else frame
        if frame is None:
            return

        values = self._get_hsv_values()
        lower = np.array([
            values["h_min"],
            values["s_min"],
            values["v_min"],
        ], dtype=np.uint8)
        upper = np.array([
            values["h_max"],
            values["s_max"],
            values["v_max"],
        ], dtype=np.uint8)

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, lower, upper)
        result = cv2.bitwise_and(frame, frame, mask=mask)
        mask_bgr = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)

        self._set_processed_image(self.window.mask_label, mask_bgr)
        self._set_processed_image(self.window.result_label, result)

    def _set_processed_image(self, label: QLabel, frame: np.ndarray):
        """Convierte un frame BGR a pixmap y lo ajusta al QLabel."""
        pixmap = self.window.camera_interface.numpy_to_qpixmap(frame)
        if pixmap.isNull():
            return

        label.setPixmap(pixmap.scaled(
            label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation
        ))

    def _clear_processed_images(self):
        """Limpia las vistas procesadas al apagar la cámara."""
        self._last_frame = None
        self.window.mask_label.clear()
        self.window.mask_label.setText("Máscara HSV")
        self.window.result_label.clear()
        self.window.result_label.setText("Resultado HSV")
