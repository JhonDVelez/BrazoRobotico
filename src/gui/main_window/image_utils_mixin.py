""" Modulo donde se gestiona el comportamiento de los pixmap (imágenes) presentes en la interfaz 
    cuando algún proceso no esa en funcionamiento, o cuando es detenido por el usuario, por ejemplo
    al iniciar la interfaz se muestra un brazo, una cámara y unas gráficas estas imágenes son
    son gestionadas aquí asi como su comportamiento frente al cambio de tamaño de ventana y el tema.
"""
from PyQt6.QtGui import QPixmap, QResizeEvent
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
