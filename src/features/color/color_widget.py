"""
Módulo que gestiona la interfaz visual para la calibración de colores.

Este módulo define la clase ColorWidget, la cual integra los controles deslizantes
para el ajuste de rangos HSV y las visualizaciones de cámara, máscara y resultado
en una disposición organizada.

Conexiones:
    - Emite `hsv_changed` cuando se ajusta cualquier control deslizante.
    - Emite `camera_toggled` para encender o apagar la captura de video.
    - Utiliza `ImageHandler` para cada una de sus tres sub-vistas de imagen.
"""

import numpy as np
from PyQt6.QtWidgets import (
    QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QSlider, QSpinBox, QComboBox, QGroupBox
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QFont
from src.services.ui import ImageHandler


class ColorWidget(QWidget):
    """
    Widget de interfaz para la calibración de color HSV.

    Mantiene una paridad visual entre los controles de entrada (sliders/spinboxes)
    y la retroalimentacion visual de procesamiento en tiempo real.

    Attributes:
        save_clicked (pyqtSignal): Emite al presionar el boton de guardar.
        camera_toggled (pyqtSignal): Emite el estado deseado de la camara (bool).
        hsv_changed (pyqtSignal): Emite un diccionario con los valores HSV actuales.
    """
    save_clicked = pyqtSignal()
    camera_toggled = pyqtSignal(bool)
    hsv_changed = pyqtSignal(dict)

    COLORS = ["amarillo", "verde", "azul", "naranja", "morado"]

    def __init__(self, parent=None):
        """
        Inicializa el widget de color y sus controles.

        Args:
            parent (QWidget, optional): Widget padre.
        """
        super().__init__(parent)
        self._hsv_controls = {}
        self.__setup_ui()

    def __setup_ui(self):
        """
        Configura la disposición de los paneles de control y visualización.
        """
        self.setObjectName("ColorWidget")

        self.setMinimumSize(QSize(600, 600))

        main_grid = QGridLayout(self)
        main_grid.setContentsMargins(5, 5, 5, 5)
        main_grid.setSpacing(10)

        # (0, 0) - Contenedor para el widget de cámara (inyectado por controller)
        self.camera_container = QGroupBox("Vista Original")
        self.camera_layout = QVBoxLayout(self.camera_container)
        self.camera_layout.setContentsMargins(0, 0, 0, 0)
        main_grid.addWidget(self.camera_container, 0, 0)

        # (0, 1) - Panel de Controles HSV
        self.controls_widget = QWidget()
        controls_layout = QVBoxLayout(self.controls_widget)
        controls_layout.setContentsMargins(5, 5, 5, 5)
        controls_layout.setSpacing(8)

        # Top controls: Botón Cámara y Título
        top_layout = QHBoxLayout()
        self.camera_button = QPushButton("Camara")
        self.camera_button.setFixedSize(90, 30)
        self.camera_button.setCheckable(True)
        self.camera_button.setStyleSheet("border: none; padding: 4px;")
        self.camera_button.toggled.connect(self._on_camera_toggled)

        title_label = QLabel("Controles de Color")
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        top_layout.addWidget(self.camera_button)
        top_layout.addWidget(title_label)
        controls_layout.addLayout(top_layout)

        # Selector de color
        sel_layout = QHBoxLayout()
        sel_layout.addWidget(QLabel("Color:"))
        self.color_selector = QComboBox()
        self.color_selector.addItems(self.COLORS)
        sel_layout.addWidget(self.color_selector)
        controls_layout.addLayout(sel_layout)

        # Sliders y Spinboxes
        slider_specs = [
            ("H Min", "h_min", 0, 180), ("H Max", "h_max", 0, 180),
            ("S Min", "s_min", 0, 255), ("S Max", "s_max", 0, 255),
            ("V Min", "v_min", 0, 255), ("V Max", "v_max", 0, 255),
        ]

        for label_text, key, min_v, max_v in slider_specs:
            row = QHBoxLayout()
            row.addWidget(QLabel(label_text), 0)

            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(min_v, max_v)
            slider.setFixedHeight(25)

            spin = QSpinBox()
            spin.setRange(min_v, max_v)
            spin.setFixedWidth(60)

            # Sincronización interna
            slider.valueChanged.connect(
                lambda val, s=spin: self._sync_control(s, val))
            spin.valueChanged.connect(
                lambda val, s=slider: self._sync_control(s, val))

            # Notificar cambios
            slider.valueChanged.connect(self._emit_hsv_changed)

            row.addWidget(slider, 1)
            row.addWidget(spin, 0)
            controls_layout.addLayout(row)
            self._hsv_controls[key] = {"slider": slider, "spinbox": spin}

        # Botón Guardar
        self.save_button = QPushButton("Guardar Configuración")
        self.save_button.setMinimumHeight(35)
        self.save_button.clicked.connect(self.save_clicked)
        controls_layout.addWidget(self.save_button)
        controls_layout.addStretch()

        main_grid.addWidget(self.controls_widget, 0, 1)

        # (1, 0) - Máscara HSV
        self.mask_view: QGroupBox = self._create_image_view("Máscara HSV")
        main_grid.addWidget(self.mask_view, 1, 0)

        # (1, 1) - Resultado HSV
        self.result_view: QGroupBox = self._create_image_view("Resultado HSV")
        main_grid.addWidget(self.result_view, 1, 1)

    def _create_image_view(self, title: str) -> QGroupBox:
        """
        Crea una vista de imagen agrupada con su propio ImageHandler.

        Args:
            title (str): Titulo del grupo visual.

        Returns:
            QGroupBox: Grupo contenedor con un atributo ``handler`` adjunto.
        """
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setMinimumSize(QSize(240, 180))
        layout.addWidget(label)

        # Usar ImageHandler para cada vista
        handler = ImageHandler(label, "img:camera_d.svg", "img:camera_l.svg")
        handler.set_static_image()
        setattr(group, "handler", handler)
        return group

    def _sync_control(self, widget, value) -> None:
        """
        Sincroniza dos widgets sin realimentación de señales.

        Args:
            widget (QWidget): Widget cuyo valor se actualiza.
            value (int): Nuevo valor a establecer.
        """
        widget.blockSignals(True)
        widget.setValue(value)
        widget.blockSignals(False)

    def _emit_hsv_changed(self) -> None:
        """
        Emite la señal de cambio de valores HSV con el estado actual.
        """
        self.hsv_changed.emit(self.get_hsv_values())

    def _on_camera_toggled(self, checked):
        """
        Maneja el toggle del botón de cámara.

        Args:
            checked (bool): Estado del boton (ON/OFF).
        """
        self.camera_button.setText("Cámara ON" if checked else "Cámara OFF")
        self.camera_toggled.emit(checked)

    def get_hsv_values(self) -> dict:
        """
        Retorna los valores actuales de todos los controles HSV.

        Returns:
            dict: Diccionario {nombre_control: valor}.
        """
        return {key: ctrl["spinbox"].value() for key, ctrl in self._hsv_controls.items()}

    def set_hsv_values(self, values: dict) -> None:
        """
        Establece los valores de los controles HSV desde un diccionario.

        Args:
            values (dict): Diccionario {nombre_control: valor}.
        """
        for key, val in values.items():
            if key in self._hsv_controls:
                self._hsv_controls[key]["spinbox"].setValue(val)

    def get_selected_color(self) -> str:
        """
        Retorna el nombre del color seleccionado en el combo.

        Returns:
            str: Nombre del color (e.g. 'azul').
        """
        return self.color_selector.currentText()

    def get_camera_layout(self) -> QVBoxLayout:
        """
        Retorna el layout destinado al widget de feed de cámara.

        Returns:
            QVBoxLayout: Layout del contenedor de cámara.
        """
        return self.camera_layout

    def update_views(self, mask_frame: np.ndarray, result_frame: np.ndarray) -> None:
        """
        Actualiza las imágenes de máscara y resultado del procesamiento.

        Args:
            mask_frame (np.ndarray): Imagen de la máscara binaria HSV.
            result_frame (np.ndarray): Imagen filtrada final.
        """
        self.mask_view.handler.set_video_image(
            ImageHandler.numpy_to_qpixmap(mask_frame))
        self.result_view.handler.set_video_image(
            ImageHandler.numpy_to_qpixmap(result_frame))

    def set_process_running(self, running: bool) -> None:
        """
        Actualiza el estado de procesamiento de los ImageHandler internos.

        Args:
            running (bool): True si el procesamiento está activo.
        """
        self.mask_view.handler.set_process_running(running)
        self.result_view.handler.set_process_running(running)

    def clear_views(self) -> None:
        """
        Detiene el procesamiento y restaura las imágenes placeholder.
        """
        self.set_process_running(False)
        self.mask_view.handler.set_static_image()
        self.result_view.handler.set_static_image()
