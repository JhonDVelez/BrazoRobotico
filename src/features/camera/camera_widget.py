"""
Modulo que gestiona la interfaz visual del modulo de camara.

Este modulo define la clase CameraWidget, la cual organiza los elementos graficos
para la visualizacion del flujo de video, la seleccion de dispositivos y el control
de overlays (cuadricula y geometria) sobre la imagen.

Conexiones:
    - Utiliza `ImageHandler` para gestionar la transicion entre imagenes estaticas y dinmicas.
    - Integra `CameraSelectorWidget` para la eleccion de hardware.
    - Muestra notificaciones temporales mediante `ToastLabel`.
"""

import numpy as np
from PyQt6.QtWidgets import QSizePolicy, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QWidget
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QIcon
from src.features.camera.devices_submenu import CameraSelectorWidget
from src.services.ui.image_handler import ImageHandler
from src.services.ui.toast_label import ToastLabel


class CameraWidget(QWidget):
    """
    Widget para la visualizacion y control de la camara en la interfaz.

    Administra un layout que superpone botones de control sobre la visualizacion
    del video y gestiona la seleccion de camaras disponibles.

    Attributes:
        video_toggled (pyqtSignal): Señal emitida al presionar el boton de video.
        grid_toggled (pyqtSignal): Señal emitida al alternar la cuadricula.
        geometry_toggled (pyqtSignal): Señal emitida al alternar la geometria.
        camera_changed (pyqtSignal): Señal que envia el indice de la camara seleccionada.
    """
    video_toggled = pyqtSignal()
    grid_toggled = pyqtSignal()
    geometry_toggled = pyqtSignal()
    camera_changed = pyqtSignal(int)

    def __init__(self, parent=None, camera_config: dict = {"charuco": False, "circle": False}):
        """
        Inicializa el widget de camara con la configuracion de vista inicial.

        Args:
            parent (QWidget, optional): Widget padre.
            camera_config (dict): Configuracion inicial de visibilidad de overlays.
        """
        super().__init__(parent)
        self.charuco_view = camera_config.get("charuco", False)
        self.sphere_view = camera_config.get("circle", False)
        self.__setup_ui()
        self.image_handler = ImageHandler(
            self.image_label, "img:camera_d.svg", "img:camera_l.svg"
        )
        self.image_handler.set_static_image()

    def __setup_ui(self):
        """
        Configura la interfaz de usuario, layouts y componentes de control.
        """
        self.setObjectName("OverlayButtonWidget")
        size_policy = QSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setSizePolicy(size_policy)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # Label de fondo para mostrar el video
        self.image_label = QLabel()
        self.image_label.setScaledContents(False)
        self.image_label.setSizePolicy(size_policy)
        self.image_label.setMinimumSize(QSize(160, 120))
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.image_label)

        # Widget overlay para botones (transparente)
        self.buttons_widget = QWidget(self)
        self.buttons_widget.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground)
        self.buttons_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.buttons_widget.setFixedHeight(50)

        buttons_layout = QHBoxLayout(self.buttons_widget)
        buttons_layout.setContentsMargins(10, 10, 10, 0)
        buttons_layout.setSpacing(0)

        # Panel de botones izquierdo (Video, Grid, Geometria)
        self.camera_buttons_panel = QWidget(self.buttons_widget)
        self.camera_buttons_panel.setObjectName("camera_buttons_panel")
        camera_buttons_layout = QHBoxLayout(self.camera_buttons_panel)
        camera_buttons_layout.setContentsMargins(0, 0, 0, 0)
        camera_buttons_layout.setSpacing(5)

        self.video_button = QPushButton()
        self.video_button.setFixedSize(30, 30)
        self.video_button.setStyleSheet(
            "background-color: white; border: none;")
        self.video_button.setIconSize(QSize(25, 25))
        self.camera_on_icon = QIcon('icons:cameraOn.png')
        self.camera_off_icon = QIcon('icons:cameraOff.png')
        self.video_button.setIcon(self.camera_on_icon)

        self.grid_button = QPushButton()
        self.grid_button.setFixedSize(30, 30)
        self.grid_button.setStyleSheet(
            "background-color: white; border: none;")
        self.grid_button.setIconSize(QSize(25, 25))
        self.show_grid_icon = QIcon('icons:gridOn.png')
        self.hide_grid_icon = QIcon('icons:gridOff.png')
        self.grid_button.setIcon(
            self.show_grid_icon if self.sphere_view else self.hide_grid_icon)

        self.geometry_button = QPushButton()
        self.geometry_button.setFixedSize(30, 30)
        self.geometry_button.setStyleSheet(
            "background-color: white; border: none;")
        self.geometry_button.setIconSize(QSize(25, 25))
        self.show_circle_icon = QIcon('icons:geometryOn.png')
        self.hide_circle_icon = QIcon('icons:geometryOff.png')
        self.geometry_button.setIcon(
            self.show_circle_icon if self.charuco_view else self.hide_circle_icon)

        camera_buttons_layout.addWidget(self.video_button)
        camera_buttons_layout.addWidget(self.grid_button)
        camera_buttons_layout.addWidget(self.geometry_button)

        controls_width = 30 * 3 + 5 * 2
        self.camera_buttons_panel.setFixedSize(controls_width, 30)

        # Panel del selector central (Combo box de camaras)
        self.camera_selector = CameraSelectorWidget()
        self.camera_selector_panel = QWidget(self.buttons_widget)
        self.camera_selector_panel.setFixedHeight(30)
        self.camera_selector_panel.setObjectName("camera_selector_panel")
        camera_selector_layout = QHBoxLayout(self.camera_selector_panel)
        camera_selector_layout.setContentsMargins(0, 0, 0, 0)
        camera_selector_layout.addStretch(1)
        camera_selector_layout.addWidget(
            self.camera_selector, 0, Qt.AlignmentFlag.AlignTop)
        camera_selector_layout.addStretch(1)

        # Spacer derecho para equilibrar el selector
        self.camera_buttons_spacer = QWidget(self.buttons_widget)
        self.camera_buttons_spacer.setFixedSize(controls_width, 30)
        self.camera_buttons_spacer.setObjectName("camera_buttons_spacer")

        buttons_layout.addWidget(
            self.camera_buttons_panel, 0, Qt.AlignmentFlag.AlignTop)
        buttons_layout.addWidget(
            self.camera_selector_panel, 1, Qt.AlignmentFlag.AlignTop)
        buttons_layout.addWidget(
            self.camera_buttons_spacer, 0, Qt.AlignmentFlag.AlignTop)
        buttons_layout.addStretch(0)

        self.buttons_widget.setGeometry(0, 0, self.width(), 50)
        self.__setup_connections()

        self.toast = ToastLabel(self)
        self.toast.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def __setup_connections(self):
        """
        Conecta las señales de los componentes visuales con los slots internos.
        """
        self.video_button.clicked.connect(self.video_toggled)
        self.grid_button.clicked.connect(self.grid_toggled)
        self.geometry_button.clicked.connect(self.geometry_toggled)
        self.camera_selector.currentIndexChanged.connect(self.camera_changed)

    def get_image_handler(self):
        """
        Retorna el manejador de imagenes del widget.

        Returns:
            ImageHandler: Instancia del manejador de imagenes.
        """
        return self.image_handler

    def set_ui_running_state(self, is_running):
        """
        Actualiza el estado visual de los controles segun si el video esta activo.

        Args:
            is_running (bool): True si el video esta en ejecucion.
        """
        self.video_button.setIcon(
            self.camera_off_icon if is_running else self.camera_on_icon)
        if is_running:
            self.camera_selector_panel.hide()
            self.camera_buttons_spacer.hide()
        else:
            self.camera_selector_panel.show()
            self.camera_buttons_spacer.show()

    def set_available_cameras(self, cameras, selected_name=None):
        """
        Actualiza la lista de camaras disponibles en el selector.

        Args:
            cameras (list): Lista de tuplas (indice, nombre_pantalla).
            selected_name (str, optional): Nombre de la camara a seleccionar por defecto.
        """
        self.camera_selector.blockSignals(True)
        self.camera_selector.clear()
        for camera_index, display_name in cameras:
            self.camera_selector.addItem(
                display_name, [camera_index, display_name])

        has_cameras = bool(cameras)
        self.camera_selector.setVisible(has_cameras)

        selected_index = -1
        if selected_name:
            selected_index = self.camera_selector.findText(selected_name)

        self.camera_selector.setCurrentIndex(selected_index)
        self.camera_selector.blockSignals(False)

    def update_frame(self, frame):
        """
        Actualiza el frame visualizado en la interfaz.

        Args:
            frame (np.ndarray | cv2.UMat): Nueva imagen a mostrar.
        """
        if frame is not None:
            pixmap = ImageHandler.numpy_to_qpixmap(frame) if isinstance(
                frame, np.ndarray) else ImageHandler.umat_to_pixmap(frame)
            self.image_handler.set_video_image(pixmap)

    def resizeEvent(self, event):
        """
        Ajusta la posicion del panel de botones y el toast al redimensionar.

        Args:
            event (QResizeEvent): Evento de redimensionamiento.
        """
        super().resizeEvent(event)
        self.buttons_widget.setGeometry(0, 0, self.width(), 50)
        self.buttons_widget.raise_()
        self.toast.raise_()
