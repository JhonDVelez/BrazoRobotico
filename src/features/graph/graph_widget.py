import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QRadioButton,
                             QLabel, QStackedWidget, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal
from src.services.ui.image_handler import ImageHandler


class GraphWidget(QWidget):
    """
    Widget contenedor de las gráficas.
    Gestiona los selectores de modo (Angular/Cartesiano) y la imagen estática.
    """
    mode_changed = pyqtSignal(bool)  # True if angular

    def __init__(self, parent=None):
        super().__init__(parent)
        self._image_path_d = "img:graph_d.svg"
        self._image_path_l = "img:graph_l.svg"
        self.__setup_ui()

        self._image_handler = ImageHandler(
            self.image_label, self._image_path_d, self._image_path_l)
        self._image_handler.set_static_image()

    def __setup_ui(self):
        self.setObjectName("radio_button_container")
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.setObjectName("graph_widget")

        # 1. Selector de modo (Radios)
        radio_style = "QRadioButton::indicator {margin-left: 0px; background-color: transparent}"
        self.angular_radio = QRadioButton("Angular")
        self.angular_radio.setStyleSheet(radio_style)
        self.angular_radio.setChecked(True)
        self.angular_radio.toggled.connect(self._on_mode_toggled)

        self.cartesian_radio = QRadioButton("Cartesiano")
        self.cartesian_radio.setStyleSheet(radio_style)

        self.selector_layout = QHBoxLayout()
        self.selector_layout.addWidget(self.angular_radio)
        self.selector_layout.addWidget(self.cartesian_radio)
        self.selector_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.selector_layout.setSpacing(10)
        self.main_layout.addLayout(self.selector_layout)

        # 2. Imagen estática
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.image_label.setMinimumSize(160, 120)
        self.main_layout.addWidget(self.image_label)

        # 3. Stacked widget para las gráficas
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setObjectName("graph_stack_container")
        self.main_layout.addWidget(self.stacked_widget)

        # Contenedores para las gráficas
        self.angular_container = QWidget()
        self.angular_container.setObjectName("angular_container")
        self.angular_layout = QGridLayout(self.angular_container)
        self.angular_layout.setContentsMargins(0, 0, 0, 0)
        self.angular_layout.setSpacing(0)

        self.cartesian_container = QWidget()
        self.cartesian_container.setObjectName("cartesian_container")
        self.cartesian_layout = QGridLayout(self.cartesian_container)
        self.cartesian_layout.setContentsMargins(0, 0, 0, 0)
        self.cartesian_layout.setSpacing(0)

        self.stacked_widget.addWidget(self.angular_container)
        self.stacked_widget.addWidget(self.cartesian_container)

        # Estado inicial (Oculto)
        self._set_ui_running_state(False)

    def _on_mode_toggled(self, checked):
        if checked:
            self.stacked_widget.setCurrentIndex(0)
            self.mode_changed.emit(True)
        else:
            self.stacked_widget.setCurrentIndex(1)
            self.mode_changed.emit(False)

    def _set_ui_running_state(self, running: bool):
        if running:
            self.image_label.hide()
            self.stacked_widget.show()
            self.angular_radio.show()
            self.cartesian_radio.show()
        else:
            self.stacked_widget.hide()
            self.angular_radio.hide()
            self.cartesian_radio.hide()
            self.image_label.show()

    # --- API Pública ---

    def set_running(self, running: bool):
        self._image_handler.set_process_running(running)
        self._set_ui_running_state(running)
        if not running:
            self._image_handler.set_static_image()

    def get_angular_layout(self):
        return self.angular_layout

    def get_cartesian_layout(self):
        return self.cartesian_layout

    def get_image_handler(self):
        return self._image_handler
