""" Modulo donde se gestiona la estructura y comportamiento de la cámara cuyas imágenes se muestran
    en la interfaz
"""
import os
from PyQt6.QtWidgets import QSizePolicy, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, QSize, QRect
from PyQt6.QtGui import QPixmap, QIcon
from gui.camera_worker import VideoWorker
from gui.main_window.main_theme_mixin import ThemeManager
from gui.main_window.image_utils_mixin import ImageUtilsMixin


class CameraInterface(ImageUtilsMixin):
    """ Manejo del widget de video que muestra las imágenes de la cámara en un label de la interfaz
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.video_worker = None
        self.process_running = False
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
        size_policy = QSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        size_policy.setHorizontalStretch(0)
        size_policy.setVerticalStretch(0)
        self.setSizePolicy(size_policy)

        # sizeIncrement
        self.setSizeIncrement(QSize(160, 120))

        self.setWindowTitle("Form")

        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setObjectName("mainLayout")
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # QLabel (videoLabel)
        self.image_label = QLabel(self)
        self.image_label.setObjectName("videoLabel")
        self.image_label.setSizePolicy(size_policy)
        self.image_label.setMinimumSize(QSize(160, 120))
        self.image_label.setText("")
        self.image_label.setScaledContents(True)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.main_layout.addWidget(self.image_label)

        # QPushButton (videoButton) -> posición absoluta
        self.video_button = QPushButton(self)
        self.video_button.setObjectName("videoButton")
        self.video_button.setGeometry(QRect(10, 10, 50, 30))
        self.video_button.setToolTip("Toggle Camera")
        self.video_button.setText("")
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)
        self.setMinimumSize(160, 120)

        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setScaledContents(False)
        self.image_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.video_button.setIcon(QIcon(os.path.join(
            os.path.dirname(__file__), 'icons', 'camera.png')))
        self.video_button.setIconSize(QSize(25, 25))
        self.video_button.setStyleSheet(
            "background-color: white;")
        self.video_button.setFixedSize(30, 30)
        self.video_button.raise_()

        self.image_path_r = os.path.join(os.path.dirname(
            __file__), "img", 'camera_r.png')
        self.image_path_b = os.path.join(os.path.dirname(
            __file__), "img", 'camera_b.png')
        self.pixmap = QPixmap(self.image_path_r)

    def __setup_connections(self):
        """Configura las conexiones de eventos
        """
        self.video_button.clicked.connect(self.toggle_video)
        self.theme_manager.theme_changed.connect(self.toggle_theme)

    def on_frame_ready(self, pixmap: QPixmap):
        """ Slot para manejar el frame listo del worker thread.

        Args:
            pixmap (QPixmap): El pixmap del frame de video listo
        """
        if self.process_running:
            self.set_pixmap(pixmap)

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
            self.process_running = True

        except (RuntimeError, OSError) as e:
            print(f"Error al iniciar video: {e}")
            self.on_video_error(str(e))

    def stop_video(self):
        """ Detiene la captura de video
        """
        self.process_running = False

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
        """ Pausa la actualización de frames de la cámara
        """
        if self.video_worker is not None:
            self.video_worker.pause()

    def resume_video(self):
        """ Vuelve a activar la actualización de frames de la cámara
        """

        if self.video_worker is not None:
            self.video_worker.resume()

    def toggle_video(self):
        """ Alterna el estado de la captura de video.
        """
        if hasattr(self.parent, 'cameraBox'):
            if not self.parent.cameraBox.isVisible():
                return

        if not self.image_label.isEnabled():
            return

        if self.process_running:
            self.stop_video()
        else:
            self.start_video()
