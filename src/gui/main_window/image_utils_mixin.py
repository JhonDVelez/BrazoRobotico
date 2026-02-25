""" Modulo donde se gestiona el comportamiento de los pixmap (imágenes) presentes en la interfaz 
    cuando algún proceso no esa en funcionamiento, o cuando es detenido por el usuario, por ejemplo
    al iniciar la interfaz se muestra un brazo, una cámara y unas gráficas estas imágenes son
    son gestionadas aquí asi como su comportamiento frente al cambio de tamaño de ventana y el tema.
"""
from PyQt6.QtGui import QPixmap, QResizeEvent
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget


class ImageUtilsMixin(QWidget):
    """ Clase Mixin que proporciona utilidades para el manejo de imágenes (QPixmap).
        Permite que los widgets hijos hereden capacidades de redimensionamiento
        automático y adaptación de iconos según el tema visual.
    """

    def load_image(self):
        """ Carga una imagen desde la memoria (atributo self.pixmap) y la proyecta 
            en el contenedor visual (label). Verifica la integridad del recurso antes de asignarlo.

        Args:
            image_path (str): Nota: El argumento en la firma del docstring original no se usa 
                             directamente ya que consume atributos de instancia.
        """

        # Validación de que el objeto QPixmap contiene datos válidos
        if not self.pixmap.isNull():
            self.set_pixmap(self.pixmap)
        else:
            # Reporte de error en caso de que la ruta del recurso sea inválida o inaccesible
            print(
                f"Error: No se pudo cargar la imagen desde {self.image_path_r}")

    def set_pixmap(self, pixmap: QPixmap):
        """ Gestiona la asignación del pixmap al QLabel, aplicando una transformación
            de escala para que la imagen se ajuste al tamaño actual del contenedor.

        Args:
            pixmap (QPixmap): El objeto de imagen a mostrar.
        """
        if pixmap and not pixmap.isNull():
            # Obtiene las dimensiones actuales del label para el cálculo del escalado
            label_size = self.image_label.size()
            
            # Solo escala si el tamaño de la imagen difiere del tamaño del label
            if pixmap.size() != label_size:
                scaled_pixmap = pixmap.scaled(
                    label_size,
                    Qt.AspectRatioMode.KeepAspectRatio, # Mantiene la proporción original
                    Qt.TransformationMode.FastTransformation # Optimiza la velocidad de renderizado
                )
                self.image_label.setPixmap(scaled_pixmap)
            else:
                self.image_label.setPixmap(pixmap)
        else:
            # Si el pixmap es nulo, limpia el contenido del label para evitar residuos visuales
            self.image_label.clear()

    def toggle_theme(self, dark_t):
        """ Actualiza el recurso gráfico cargado en memoria cuando se cambia el tema 
            de la aplicación (Modo Oscuro vs Modo Claro).

        Args:
            dark_t (bool): Flag que indica si el tema actual es oscuro (True).
        """
        # Intercambio de rutas de imagen según la estética del tema seleccionado
        if dark_t:
            self.pixmap = QPixmap(self.image_path_r) # Versión para fondo oscuro
        else:
            self.pixmap = QPixmap(self.image_path_b) # Versión para fondo claro

        # Si no hay un proceso activo (video/simulación), refresca la imagen estática
        if not self.process_running:
            self.load_image()

    def resizeEvent(self, event: QResizeEvent):
        """ Evento de Qt que se dispara automáticamente al cambiar el tamaño del widget.
            Garantiza que las imágenes estáticas se reescalen junto con la ventana.

        Args:
            event (QResizeEvent): Contiene los datos del tamaño anterior y nuevo.
        """
        # Asegura que la lógica base de QWidget para redimensionamiento se ejecute
        super().resizeEvent(event)

        # Refresca el escalado de la imagen solo si no hay un flujo de datos activo
        if not self.process_running:
            self.load_image()

    def showEvent(self, event):
        """ Evento de Qt disparado cuando el widget se renderiza por primera vez o
            vuelve a ser visible, asegurando que la imagen se cargue correctamente.
        """
        super().showEvent(event)
        self.load_image()