""" Modulo donde se gestiona el comportamiento de los pixmap (imágenes) presentes en la interfaz 
    cuando algún proceso no esa en funcionamiento, o cuando es detenido por el usuario, por ejemplo
    al iniciar la interfaz se muestra un brazo, una cámara y unas gráficas estas imágenes son
    son gestionadas aquí asi como su comportamiento frente al cambio de tamaño de ventana y el tema.
"""
from .main_theme_mixin import ThemeManager
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QSize
from PyQt6.QtWidgets import QWidget, QLabel, QGraphicsOpacityEffect
from PyQt6.QtGui import QPixmap, QResizeEvent, QImage, QPainter
from PyQt6.QtSvg import QSvgRenderer
import numpy as np
import cv2


class ImageUtilsMixin(QWidget):
    def set_static_image(self):
        """ Carga una imagen desde la raíz del proyecto y la establece como pixmap en el label.
        """

        if not self.pixmap.isNull():
            self.image_label.setContentsMargins(10, 10, 10, 10)
            self.set_pixmap(
                self.pixmap, Qt.TransformationMode.SmoothTransformation)
        else:
            raise Exception(
                f"Error: No se pudo cargar la imagen desde {self.image_path_d}")

    def set_video_image(self, pixmap: QPixmap):
        """ Envía los frames procesados de la cámara al QLabel

        Args:
            pixmap (QPixmap): frame obtenido de la cámara
        """
        if pixmap:
            self.image_label.setContentsMargins(0, 0, 0, 0)
            self.set_pixmap(
                self.pixmap, Qt.TransformationMode.FastTransformation)
        else:
            raise Exception("El frame obtenido no es valido")

    def set_pixmap(self, pixmap: QPixmap, transform_type: Qt.TransformationMode):
        """ Método para establecer el pixmap del video en el label reescalado si es necesario.

        Args:
            pixmap (QPixmap): El pixmap del video a mostrar
        """
        if pixmap and not pixmap.isNull():
            label_size = self.image_label.size()

            # Obtener los márgenes del label
            margins = self.image_label.contentsMargins()
            available_width = label_size.width() - margins.left() - margins.right()
            available_height = label_size.height() - margins.top() - margins.bottom()

            # Crear el tamaño disponible considerando los márgenes
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

    def toggle_theme(self, dark_t):
        """ Alterna el estado de la captura de video.
        """
        if dark_t:
            self.pixmap = QPixmap(self.image_path_d)
        else:
            self.pixmap = QPixmap(self.image_path_l)

        if not self.process_running:
            self.set_static_image()

    def resizeEvent(self, event: QResizeEvent):
        """ Maneja el evento de redimensionamiento del widget.

        Args:
            event (QResizeEvent): Evento de redimensionamiento
        """
        super().resizeEvent(event)

        if not self.process_running:
            self.set_static_image()

    def showEvent(self, event):
        """Se ejecuta cuando el widget se vuelve visible"""
        super().showEvent(event)
        self.set_static_image()

    @classmethod
    def numpy_to_qpixmap(cls, frame: np.ndarray) -> QPixmap:
        """ Convierte frame numpy BGR a QPixmap
        """
        try:
            # Asegurarse de uint8 contiguous

            frame = np.ascontiguousarray(frame, dtype=np.uint8)
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

    @classmethod
    def umat_to_pixmap(cls, u_mat: cv2.UMat) -> QPixmap:
        """ Convierte frame UMat a QPixmap
        """
        # 1. Convertir UMat a numpy array (CPU)
        frame = u_mat.get()

        # 2. Convertir de BGR a RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # 3. Obtener dimensiones
        height, width, channels = frame_rgb.shape
        bytes_per_line = channels * width

        # 4. Crear QImage
        q_img = QImage(
            frame_rgb.data,
            width,
            height,
            bytes_per_line,
            QImage.Format.Format_RGB888
        )

        # 5. Convertir a QPixmap
        return QPixmap.fromImage(q_img)


class ToastLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setGraphicsEffect(QGraphicsOpacityEffect(self))
        self.opacity = self.graphicsEffect()

        self.anim = QPropertyAnimation(self.opacity, b"opacity")
        self.anim.setDuration(300)

        # 🔥 bandera para saber qué animación está corriendo
        self.fading_out = False

        # ✅ conectar UNA sola vez
        self.anim.finished.connect(self.on_animation_finished)

        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.fade_out)

        self.hide()

        self.theme_manager = ThemeManager().get_instance()
        self.theme_manager.theme_changed.connect(self.change_theme)

    def show_message(self, text, duration=2000):
        self.timer.stop()          # 🔥 importante
        self.anim.stop()           # 🔥 importante

        self.setText(text)
        self.adjustSize()

        if self.parent():
            parent_rect = self.parent().rect()
            self.move(
                (parent_rect.width() - self.width()) // 2,
                parent_rect.height() - self.height() - 20
            )

        self.fading_out = False

        self.show()
        self.raise_()

        # Fade in
        self.anim.setStartValue(0)
        self.anim.setEndValue(1)
        self.anim.start()

        self.timer.start(duration)

    def fade_out(self):
        self.anim.stop()

        self.fading_out = True

        self.anim.setStartValue(1)
        self.anim.setEndValue(0)
        self.anim.start()

    def on_animation_finished(self):
        if self.fading_out:
            self.hide()

    def change_theme(self, dark_t: bool):
        if dark_t:
            self.setStyleSheet("""
                QLabel {
                    background-color: rgba(57.000, 61.000, 65.000, 1.000);
                    color: white;
                    border-radius: 10px;
                    padding: 10px 20px;
                }
            """)
        else:
            self.setStyleSheet("""
                QLabel {
                    background-color: rgba(218.000, 220.000, 224.000, 1.000);
                    color: rgba(77.000, 81.000, 87.000, 1.000);
                    border-radius: 10px;
                    padding: 10px 20px;
                }
            """)
