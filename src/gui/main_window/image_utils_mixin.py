""" Modulo donde se gestiona el comportamiento de los pixmap (imágenes) presentes en la interfaz 
    cuando algún proceso no esa en funcionamiento, o cuando es detenido por el usuario, por ejemplo
    al iniciar la interfaz se muestra un brazo, una cámara y unas gráficas estas imágenes son
    son gestionadas aquí asi como su comportamiento frente al cambio de tamaño de ventana y el tema.
"""
import numpy as np
import cv2
from PyQt6.QtGui import QPixmap, QResizeEvent, QImage
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget


class ImageUtilsMixin(QWidget):
    def load_image(self):
        """ Carga una imagen desde la raíz del proyecto y la establece como pixmap en el label.

        Args:
            image_path (str): Ruta de la imagen a cargar
        """

        if not self.pixmap.isNull():
            self.set_pixmap(self.pixmap)
        else:
            print(
                f"Error: No se pudo cargar la imagen desde {self.image_path_r}")

    def set_pixmap(self, pixmap: QPixmap):
        """ Método para establecer el pixmap del video en el label reescalado si es necesario.

        Args:
            pixmap (QPixmap): El pixmap del video a mostrar
        """
        if pixmap and not pixmap.isNull():
            label_size = self.image_label.size()
            if pixmap.size() != label_size:
                scaled_pixmap = pixmap.scaled(
                    label_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.FastTransformation
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
            self.pixmap = QPixmap(self.image_path_r)
        else:
            self.pixmap = QPixmap(self.image_path_b)

        if not self.process_running:
            self.load_image()

    def resizeEvent(self, event: QResizeEvent):
        """ Maneja el evento de redimensionamiento del widget.

        Args:
            event (QResizeEvent): Evento de redimensionamiento
        """
        super().resizeEvent(event)

        if not self.process_running:
            self.load_image()

    def showEvent(self, event):
        """Se ejecuta cuando el widget se vuelve visible"""
        super().showEvent(event)
        self.load_image()

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

    @classmethod
    def qpixmap_a_numpy(cls, pixmap):
        """ Convierte un QPixmap de PyQt6 a un array de OpenCV (numpy BGR).
        """
        # 1. Convertir QPixmap a QImage
        qimg = pixmap.toImage()

        # 2. Convertir QImage a formato RGBA8888 para asegurar compatibilidad
        qimg = qimg.convertToFormat(QImage.Format.Format_RGBA8888)

        width = qimg.width()
        height = qimg.height()

        # 3. Obtener los bits de la imagen y convertirlos a un array de NumPy
        ptr = qimg.bits()
        ptr.setsize(height * width * 4)
        arr = np.array(ptr).reshape(height, width, 4)  # RGBA

        # 4. Convertir de RGBA a BGR (formato estándar de OpenCV)
        return cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
