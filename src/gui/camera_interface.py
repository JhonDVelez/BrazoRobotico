""" Modulo donde se gestiona la estructura y comportamiento de la cámara cuyas imágenes se muestran
    en la interfaz
"""
import os
import numpy as np
import cv2
from PyQt6.QtWidgets import QSizePolicy, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QWidget
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QIcon
from gui.camera_worker import CameraWorker
from gui.main_window.main_theme_mixin import ThemeManager
from gui.main_window.image_utils_mixin import ImageUtilsMixin


class CameraInterface(ImageUtilsMixin):
    """ Manejo del widget de video que muestra las imágenes de la cámara en un label de la interfaz
    """

    def __init__(self, parent, is_calibration: bool = False):
        super().__init__(parent=None)
        self.parent = parent
        self.video_worker = None
        self.camera_chess_board = None
        self.process_running = False
        self.app_running = None
        self.grid_enabled = False
        self.geometry_enabled = False
        self.fps = 0
        self._frame_count = 0
        self._last_fps_update = 0
        self.theme_manager = ThemeManager.get_instance()
        self.is_calibration = is_calibration
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

        self.setSizeIncrement(QSize(160, 120))
        self.setWindowTitle("Form")

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # Label de fondo
        self.image_label = QLabel()
        self.image_label.setScaledContents(False)
        self.image_label.setSizePolicy(size_policy)
        self.image_label.setMinimumSize(QSize(160, 120))
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.main_layout.addWidget(self.image_label)

        # Widget overlay para botones
        self.buttons_widget = QWidget(self)
        self.buttons_widget.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground)
        self.buttons_widget.setSizePolicy(size_policy)
        self.buttons_widget.setMinimumSize(QSize(110, 40))

        buttons_layout = QHBoxLayout(self.buttons_widget)
        buttons_layout.setContentsMargins(10, 10, 0, 0)
        buttons_layout.setSpacing(5)

        # Botón cámara
        self.video_button = QPushButton()

        self.video_button.setIconSize(QSize(25, 25))
        self.video_button.setFixedSize(30, 30)
        self.video_button.setStyleSheet("background-color: white;")

        self.camera_on_icon = QIcon(os.path.join(
            os.path.dirname(__file__), 'icons', 'cameraOn.png'))
        self.camera_off_icon = QIcon(os.path.join(
            os.path.dirname(__file__), 'icons', 'cameraOff.png'))
        self.video_button.setIcon(self.camera_on_icon)

        # Botón grid
        self.grid_button = QPushButton()
        self.grid_button.setIconSize(QSize(25, 25))
        self.grid_button.setFixedSize(30, 30)
        self.grid_button.setStyleSheet("background-color: white;")
        # Iconos para el botón de encendido o apagado de la referencia visual de la malla
        self.show_grid_icon = QIcon(os.path.join(
            os.path.dirname(__file__), 'icons', 'gridOn.png'))
        self.hide_grid_icon = QIcon(os.path.join(
            os.path.dirname(__file__), 'icons', 'gridOff.png'))

        # Botón grid
        self.geometry_button = QPushButton()
        self.geometry_button.setIconSize(QSize(25, 25))
        self.geometry_button.setFixedSize(30, 30)
        self.geometry_button.setStyleSheet("background-color: white;")
        # Iconos para el botón de encendido o apagado de la referencia visual de las esferas
        self.show_geometry_icon = QIcon(os.path.join(
            os.path.dirname(__file__), 'icons', 'geometryOn.png'))
        self.hide_geometry_icon = QIcon(os.path.join(
            os.path.dirname(__file__), 'icons', 'geometryOff.png'))

        self.grid_button.setIcon(self.show_grid_icon)
        self.geometry_button.setIcon(self.show_geometry_icon)

        buttons_layout.addWidget(self.video_button)
        buttons_layout.addWidget(self.grid_button)
        buttons_layout.addWidget(self.geometry_button)

        # Posición del overlay
        self.buttons_widget.move(0, 0)
        self.buttons_widget.raise_()

        self.image_path_r = os.path.join(os.path.dirname(
            __file__), "img", 'camera_r.png')
        self.image_path_b = os.path.join(os.path.dirname(
            __file__), "img", 'camera_b.png')
        self.pixmap = QPixmap(self.image_path_r)

    def __setup_connections(self):
        """Configura las conexiones de eventos
        """
        self.video_button.clicked.connect(self.toggle_video)
        self.grid_button.clicked.connect(self.toggle_grid)
        self.geometry_button.clicked.connect(self.toggle_geometry)
        self.theme_manager.theme_changed.connect(self.toggle_theme)

    def toggle_grid(self):
        """Alterna el dibujo de rejilla en el procesamiento de frames"""
        self.grid_enabled = not self.grid_enabled
        if self.video_worker is not None and self.video_worker.camera_chess_board is not None:
            self.video_worker.camera_chess_board.show_grid = self.grid_enabled

        self.grid_button.setIcon(
            self.hide_grid_icon if self.grid_enabled else self.show_grid_icon)

    def toggle_geometry(self):
        """Alterna el dibujo de rejilla en el procesamiento de frames"""
        self.geometry_enabled = not self.geometry_enabled

        self.geometry_button.setIcon(
            self.hide_geometry_icon if self.geometry_enabled else self.show_geometry_icon)

    def on_frame_ready(self, frame: np.ndarray):
        """ Slot para manejar el frame listo del worker thread.

        Args:
            frame (np.ndarray): Frame BGR listo para mostrar
        """
        if self.process_running and frame is not None:
            pixmap = None
            # Convertir el frame numpy a pixmap solo para dibujar overlays
            if isinstance(frame, np.ndarray):
                pixmap = self.numpy_to_qpixmap(frame)
            elif isinstance(frame, cv2.UMat):
                pixmap = self.umat_to_pixmap(frame)
            if not pixmap.isNull():
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
            self.video_worker = CameraWorker(
                is_calibration=self.is_calibration)
            self.camera_chess_board = self.video_worker.camera_chess_board
            self.camera_chess_board.show_grid = self.grid_enabled

            # Conectar señales
            self.video_worker.frame_ready.connect(self.on_frame_ready)
            self.video_worker.error_occurred.connect(self.on_video_error)

            # Iniciar el hilo
            self.video_worker.start()
            self.process_running = True

            self.video_button.setIcon(self.camera_off_icon)
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
                try:
                    self.video_worker.frame_ready.disconnect(
                        self.on_frame_ready)
                except Exception:
                    pass
                try:
                    self.video_worker.error_occurred.disconnect(
                        self.on_video_error)
                except Exception:
                    pass

                self.video_worker.stop()
                if self.video_worker.isRunning():
                    self.video_worker.wait(3000)

                self.video_button.setIcon(self.camera_on_icon)
                self.video_worker.deleteLater()
                self.video_worker = None
            except Exception as e:
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
