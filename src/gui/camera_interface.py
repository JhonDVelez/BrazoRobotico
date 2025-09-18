import os
from PyQt6.QtWidgets import QWidget, QSizePolicy, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, QSize, QRect
from PyQt6.QtGui import QResizeEvent, QPixmap, QIcon
from gui.camera_worker import VideoWorker
from gui.main_window.main_theme import ThemeManager


class videoInterface(QWidget):
    """ Manejo del widged de video que muestra las imagenes de la camara en un label de la interfaz

    Args:
        QWidget (_type_): _description_
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.video_worker = None
        self.video_active = False
        self.app_running = None
        self.theme_manager = ThemeManager.get_instance()
        self.__setup_ui()
        self.__setup_connections()

    def __setup_ui(self):
        """ Configura la interfaz de usuario del widget de video
        """
        self.setObjectName("OverlayButtonWidget")
        self.resize(640, 480)

        # SizePolicy
        sizePolicy = QSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        self.setSizePolicy(sizePolicy)

        # sizeIncrement
        self.setSizeIncrement(QSize(160, 120))

        self.setWindowTitle("Form")

        # Main layout
        self.mainLayout = QVBoxLayout(self)
        self.mainLayout.setObjectName("mainLayout")
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(0)

        # QLabel (videoLabel)
        self.videoLabel = QLabel(self)
        self.videoLabel.setObjectName("videoLabel")
        sizePolicy = QSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        self.videoLabel.setSizePolicy(sizePolicy)
        self.videoLabel.setMinimumSize(QSize(160, 120))
        self.videoLabel.setText("")
        self.videoLabel.setScaledContents(True)
        self.videoLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.mainLayout.addWidget(self.videoLabel)

        # QPushButton (videoButton) -> posición absoluta
        self.videoButton = QPushButton(self)
        self.videoButton.setObjectName("videoButton")
        self.videoButton.setGeometry(QRect(10, 10, 50, 30))
        self.videoButton.setToolTip("Toggle Camera")
        self.videoButton.setText("")
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)
        self.setMinimumSize(160, 120)

        self.videoLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.videoLabel.setScaledContents(False)
        self.videoLabel.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.videoButton.setIcon(QIcon(os.path.join(
            os.path.dirname(__file__), 'icons', 'camera.png')))
        self.videoButton.setIconSize(QSize(25, 25))
        self.videoButton.setStyleSheet(
            "background-color: white;")
        self.videoButton.setFixedSize(30, 30)
        self.videoButton.raise_()
        self.image_path_r = os.path.join(os.path.dirname(
            __file__), "img", 'camera_r.png')
        self.image_path_b = os.path.join(os.path.dirname(
            __file__), "img", 'camera_b.png')
        self.pixmap = QPixmap(self.image_path_r)

    def __setup_connections(self):
        """Configura las conexiones de eventos
        """
        if hasattr(self, 'videoButton'):
            self.videoButton.clicked.connect(self.toggle_video)
        self.theme_manager.theme_changed.connect(self.toggle_theme)

    def set_video_pixmap(self, pixmap: QPixmap):
        """ Método para establecer el pixmap del video en el label reescalado si es necesario.

        Args:
            pixmap (QPixmap): El pixmap del video a mostrar
        """
        if pixmap and not pixmap.isNull():
            # Escalar solo si es necesario
            label_size = self.videoLabel.size()
            if pixmap.size() != label_size:
                scaled_pixmap = pixmap.scaled(
                    label_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.FastTransformation
                )
                self.videoLabel.setPixmap(scaled_pixmap)
            else:
                self.videoLabel.setPixmap(pixmap)
        else:
            self.videoLabel.clear()

    def load_image(self):
        """ Carga una imagen desde la raiz del proyecto y la establece como pixmap en el label.

        Args:
            image_path (str): Ruta de la imagen a cargar
        """

        if not self.pixmap.isNull():
            self.set_video_pixmap(self.pixmap)
        else:
            print(
                f"Error: No se pudo cargar la imagen desde {self.image_path_r}")

    def on_frame_ready(self, pixmap: QPixmap):
        """ Slot para manejar el frame listo del worker thread.

        Args:
            pixmap (QPixmap): El pixmap del frame de video listo
        """
        if self.video_active:
            self.set_video_pixmap(pixmap)

    def on_video_error(self, error_message):
        """ Maneja errores del worker thread de video.

        Args:
            error_message (str): Mensaje de error recibido del worker thread
        """
        print(f"Error de video: {error_message}")
        self.stop_video()

    def start_video(self):
        """ Inicia la captura de video desde la cámara y configura el worker
            thread para recibir frames.
        """
        if self.video_worker is not None:
            self.stop_video()

        try:
            self.video_worker = VideoWorker()

            # Conectar señales
            self.video_worker.frame_ready.connect(self.on_frame_ready)
            self.video_worker.error_occurred.connect(self.on_video_error)

            # Iniciar el hilo
            self.video_worker.start()
            self.video_active = True

        except (RuntimeError, OSError) as e:
            print(f"Error al iniciar video: {e}")
            self.on_video_error(str(e))

    def stop_video(self):
        """ Detiene la captura de video
        """
        self.video_active = False

        if self.video_worker is not None:
            try:
                # Desconectar señales ANTES de detener el worker
                self.video_worker.frame_ready.disconnect()
                self.video_worker.error_occurred.disconnect()

                self.video_worker.stop()
                self.video_worker.wait(3000)
                self.video_worker.deleteLater()
                self.video_worker = None
            except (RuntimeError, OSError) as e:
                print(f"Error en la ejecucion al detener el video: {e}")

        self.load_image()

    def pause_video(self):
        """ Pausa la actualizacion de frames de la camara
        """
        if self.video_worker is not None:
            self.video_worker.pause()

    def resume_video(self):
        """ Vuelve a activar la actualizacion de frames de la camara
        """

        if self.video_worker is not None:
            self.video_worker.resume()

    def resizeEvent(self, event: QResizeEvent):
        """ Maneja el evento de redimensionamiento del widget.

        Args:
            event (QResizeEvent): Evento de redimensionamiento
        """
        super().resizeEvent(event)

        # Reescalar imagen actual si existe (de forma optimizada)

        if not self.video_active:
            self.load_image()

    def showEvent(self, event):
        """Se ejecuta cuando el widget se vuelve visible"""
        super().showEvent(event)
        self.load_image()

    def toggle_video(self):
        """ Alterna el estado de la captura de video.
        """
        if not self.parent.cameraBox.isVisible() or not self.videoLabel.isEnabled():
            return

        if self.video_active:
            self.stop_video()
        else:
            self.start_video()

    def toggle_theme(self, dark_t):
        """ Alterna el estado de la captura de video.
        """
        if dark_t:
            self.pixmap = QPixmap(self.image_path_r)
        else:
            self.pixmap = QPixmap(self.image_path_b)
        self.load_image()
