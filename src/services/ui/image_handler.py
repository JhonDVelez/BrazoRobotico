from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QSize, QObject, QEvent
from PyQt6.QtWidgets import QWidget, QLabel, QGraphicsOpacityEffect
from PyQt6.QtGui import QPixmap, QImage, QResizeEvent
import numpy as np
import cv2


class ImageHandler(QObject):
    def __init__(self, image_label, image_path_d, image_path_l):
        super().__init__(parent=image_label)
        self.image_label = image_label
        self.image_path_d = image_path_d
        self.image_path_l = image_path_l
        self.pixmap = QPixmap(image_path_d)
        self.process_running = False

        # Instalar event filter para manejar redimensionamiento automático
        self.image_label.installEventFilter(self)

    def eventFilter(self, watched, event):
        if watched == self.image_label and event.type() == QEvent.Type.Resize:
            if not self.process_running:
                self.set_static_image()
        return super().eventFilter(watched, event)

    def set_static_image(self):
        if self.pixmap and not self.pixmap.isNull():
            self.image_label.setContentsMargins(10, 10, 10, 10)
            self._apply_pixmap(
                self.pixmap, Qt.TransformationMode.SmoothTransformation)
        else:
            print("Error: No se pudo cargar la imagen")

    def set_video_image(self, pixmap: QPixmap):
        if not self.process_running:
            return
        if pixmap and not pixmap.isNull():
            self.image_label.setContentsMargins(0, 0, 0, 0)
            self._apply_pixmap(pixmap, Qt.TransformationMode.FastTransformation)
        else:
            print("El frame obtenido no es valido")


    def _apply_pixmap(self, pixmap: QPixmap, transform_type: Qt.TransformationMode):
        if pixmap and not pixmap.isNull():
            label_size = self.image_label.size()
            margins = self.image_label.contentsMargins()
            available_width = label_size.width() - margins.left() - margins.right()
            available_height = label_size.height() - margins.top() - margins.bottom()
            available_size = QSize(available_width, available_height)

            if pixmap.size() != available_size:
                scaled_pixmap = pixmap.scaled(
                    available_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    transform_type
                )
                self.image_label.setPixmap(scaled_pixmap)
            else:
                self.image_label.setPixmap(pixmap)
        else:
            self.image_label.clear()

    def update_theme(self, dark_t: bool):
        self.pixmap = QPixmap(
            self.image_path_d if dark_t else self.image_path_l)
        if not self.process_running:
            self.set_static_image()

    def set_process_running(self, running: bool):
        self.process_running = running

    @staticmethod
    def numpy_to_qpixmap(frame: np.ndarray) -> QPixmap:
        try:
            frame = np.ascontiguousarray(frame, dtype=np.uint8)
            height, width, channels = frame.shape
            if channels == 3:
                bytes_per_line = channels * width
                q_image = QImage(frame.data, width, height,
                                 bytes_per_line, QImage.Format.Format_BGR888)
                return QPixmap.fromImage(q_image)
            else:
                bgr = cv2.cvtColor(
                    frame, cv2.COLOR_RGBA2BGR) if channels == 4 else frame
                bgr = np.ascontiguousarray(bgr)
                bytes_per_line = 3 * width
                q_image = QImage(bgr.data, width, height,
                                 bytes_per_line, QImage.Format.Format_BGR888)
                return QPixmap.fromImage(q_image)
        except Exception as e:
            print(f"Error conversión: {e}")
            return QPixmap()

    @staticmethod
    def umat_to_pixmap(u_mat: cv2.UMat) -> QPixmap:
        frame = u_mat.get()
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channels = frame_rgb.shape
        bytes_per_line = channels * width
        q_img = QImage(frame_rgb.data, width, height,
                       bytes_per_line, QImage.Format.Format_RGB888)
        return QPixmap.fromImage(q_img)
