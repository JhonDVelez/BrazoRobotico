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
    """ Manejo del widget de video que muestra las imágenes de la cámara en un label de la interfaz.
        Hereda de ImageUtilsMixin para facilitar el redimensionado y carga de imágenes estáticas.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.video_worker = None      # Hilo encargado de la captura de OpenCV
        self.process_running = False  # Estado de la captura de video
        self.app_running = None
        self.theme_manager = ThemeManager.get_instance()
        self.__setup_ui()
        self.__setup_connections()

    def __setup_ui(self):
        """ Configura la interfaz de usuario del widget de video, definiendo el label de imagen
            y el botón de control superpuesto.
        """
        self.setObjectName("OverlayButtonWidget")
        self.resize(640, 480)

        # Configuración de la política de tamaño para que el widget sea elástico
        size_policy = QSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        size_policy.setHorizontalStretch(0)
        size_policy.setVerticalStretch(0)
        self.setSizePolicy(size_policy)

        # Incrementos de tamaño basados en el ratio de aspecto común (4:3)
        self.setSizeIncrement(QSize(160, 120))
        self.setWindowTitle("Form")

        # Layout principal vertical que contendrá el label de la imagen
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setObjectName("mainLayout")
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # --- QLabel (image_label) ---
        # Es el contenedor donde se proyectarán los frames de video o la imagen de "cámara apagada"
        self.image_label = QLabel(self)
        self.image_label.setObjectName("videoLabel")
        self.image_label.setSizePolicy(size_policy)
        self.image_label.setMinimumSize(QSize(160, 120))
        self.image_label.setText("")
        self.image_label.setScaledContents(True)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.main_layout.addWidget(self.image_label)

        # --- QPushButton (video_button) ---
        # Botón configurado con posición absoluta para actuar como un "overlay" sobre el video
        self.video_button = QPushButton(self)
        self.video_button.setObjectName("videoButton")
        self.video_button.setGeometry(QRect(10, 10, 50, 30)) # Posicionado en la esquina superior izquierda
        self.video_button.setToolTip("Toggle Camera")
        self.video_button.setText("")
        
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)
        self.setMinimumSize(160, 120)

        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setScaledContents(False)
        self.image_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Estética del botón de cámara
        self.video_button.setIcon(QIcon(os.path.join(
            os.path.dirname(__file__), 'icons', 'camera.png')))
        self.video_button.setIconSize(QSize(25, 25))
        self.video_button.setStyleSheet("background-color: white;")
        self.video_button.setFixedSize(30, 30)
        self.video_button.raise_() # Asegura que el botón esté siempre por encima del video

        # Definición de rutas para imágenes de marcador de posición (Placeholder) según el tema
        self.image_path_r = os.path.join(os.path.dirname(
            __file__), "img", 'camera_r.png')
        self.image_path_b = os.path.join(os.path.dirname(
            __file__), "img", 'camera_b.png')
        self.pixmap = QPixmap(self.image_path_r)

    def __setup_connections(self):
        """ Configura las conexiones de eventos: clic del botón y cambios de tema global.
        """
        self.video_button.clicked.connect(self.toggle_video)
        self.theme_manager.theme_changed.connect(self.toggle_theme)

    def on_frame_ready(self, pixmap: QPixmap):
        """ Slot encargado de recibir el frame procesado por el hilo secundario
            y mostrarlo en el label de la interfaz.

        Args:
            pixmap (QPixmap): El frame de video listo para ser renderizado.
        """
        if self.process_running:
            self.set_pixmap(pixmap) # Método de ImageUtilsMixin

    def on_video_error(self, error_message):
        """ Maneja fallos en la conexión o lectura de la cámara.

        Args:
            error_message (str): Descripción del error técnico.
        """
        print(f"Error de video: {error_message}")
        self.stop_video()

    def start_video(self):
        """ Inicializa el worker thread para la captura de video.
            Separa la lógica de captura del hilo principal para evitar lag en la UI.
        """
        if self.video_worker is not None:
            self.stop_video()

        try:
            self.video_worker = VideoWorker()

            # Conexión de señales del worker a los slots de esta clase
            self.video_worker.frame_ready.connect(self.on_frame_ready)
            self.video_worker.error_occurred.connect(self.on_video_error)

            # Inicia el ciclo de ejecución de la cámara
            self.video_worker.start()
            self.process_running = True

        except (RuntimeError, OSError) as e:
            print(f"Error al iniciar video: {e}")
            self.on_video_error(str(e))

    def stop_video(self):
        """ Detiene la captura de video y libera los recursos del hilo de forma segura.
        """
        self.process_running = False

        if self.video_worker is not None:
            try:
                # Es vital desconectar las señales para evitar llamadas a objetos eliminados
                self.video_worker.frame_ready.disconnect()
                self.video_worker.error_occurred.disconnect()

                self.video_worker.stop()
                self.video_worker.wait(3000) # Espera máxima de 3 segundos para el cierre del hilo
                self.video_worker.deleteLater()
                self.video_worker = None
            except (RuntimeError, OSError) as e:
                print(f"Error en la ejecucion al detener el video: {e}")

        # Recarga la imagen de "Cámara Desactivada" (Placeholder)
        self.load_image()

    def pause_video(self):
        """ Pausa temporalmente el flujo de frames sin destruir el hilo.
        """
        if self.video_worker is not None:
            self.video_worker.pause()

    def resume_video(self):
        """ Reanuda el flujo de frames después de una pausa.
        """
        if self.video_worker is not None:
            self.video_worker.resume()

    def toggle_video(self):
        """ Lógica de conmutación (On/Off) del video.
            Verifica si el panel de cámara es visible antes de intentar iniciarla.
        """
        if not self.parent.cameraBox.isVisible() or not self.image_label.isEnabled():
            return

        if self.process_running:
            self.stop_video()
        else:
            self.start_video()