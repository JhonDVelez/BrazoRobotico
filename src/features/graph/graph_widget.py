"""
Módulo que define la interfaz visual para los gráficos de telemetría.

Este módulo contiene la clase GraphWidget, la cual organiza los selectores
de modo (Angular/Cartesiano) y gestiona el intercambio entre la imagen
estática de placeholder y el área de renderizado de gráficos activos.

Conexiones:
    - Emite `mode_changed` para notificar la selección de vista.
    - Utiliza `QStackedWidget` para optimizar el rendimiento de la interfaz.
    - Integra `ImageHandler` para la gestión de temas y placeholders.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QRadioButton,
                             QLabel, QStackedWidget, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal
from src.services.ui.image_handler import ImageHandler


class GraphWidget(QWidget):
    """
    Widget contenedor principal de las graficas del sistema.

    Proporciona los controles de radio para alternar entre el análisis de
    motores y trayectorias cartesianas, además de gestionar el estado visual
    de 'ejecución' vs 'detenido'.

    Attributes:
        mode_changed (pyqtSignal): Emite True si se selecciona el modo Angular.
        resize_requested (pyqtSignal): Emite el nuevo ancho del widget.
    """
    mode_changed = pyqtSignal(bool)  # True if angular
    resize_requested = pyqtSignal(int)  # new width

    def __init__(self, parent=None):
        """
        Inicializa el widget de gráficas y configura su interfaz base.

        Args:
            parent (QWidget, optional): Widget padre.
        """
        super().__init__(parent)
        self._image_path_d = "img:graph_d.svg"
        self._image_path_l = "img:graph_l.svg"
        self.__setup_ui()

        self._image_handler = ImageHandler(
            self.image_label, self._image_path_d, self._image_path_l)
        self._image_handler.set_static_image()

    def __setup_ui(self):
        """
        Configura los layouts, botones de radio y el stack de contenedores.
        """
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

        # 2. Imagen estatica de placeholder
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.image_label.setMinimumSize(160, 120)
        self.main_layout.addWidget(self.image_label)

        # 3. Stacked widget para intercambiar paneles de graficas
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setObjectName("graph_stack_container")
        self.main_layout.addWidget(self.stacked_widget)

        # Contenedor para graficas Angulares (6 canales)
        self.angular_container = QWidget()
        self.angular_container.setObjectName("angular_container")
        self.angular_layout = QGridLayout(self.angular_container)
        self.angular_layout.setContentsMargins(0, 0, 0, 0)
        self.angular_layout.setSpacing(0)

        # Contenedor para graficas Cartesianas (3 canales)
        self.cartesian_container = QWidget()
        self.cartesian_container.setObjectName("cartesian_container")
        self.cartesian_layout = QGridLayout(self.cartesian_container)
        self.cartesian_layout.setContentsMargins(0, 0, 0, 0)
        self.cartesian_layout.setSpacing(0)

        self.stacked_widget.addWidget(self.angular_container)
        self.stacked_widget.addWidget(self.cartesian_container)

        # Estado inicial (Oculto mientras no se presione Start)
        self._set_ui_running_state(False)

    def _on_mode_toggled(self, checked):
        """
        Cambia el índice del stacked widget según el radio seleccionado.

        Args:
            checked (bool): Estado del radio 'Angular'.
        """
        if checked:
            self.stacked_widget.setCurrentIndex(0)
            self.mode_changed.emit(True)
        else:
            self.stacked_widget.setCurrentIndex(1)
            self.mode_changed.emit(False)

    def _set_ui_running_state(self, running: bool):
        """
        Intercambia la visibilidad entre el placeholder y las gráficas reales.

        Args:
            running (bool): True si las gráficas deben estar visibles.
        """
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
        """
        Establece el estado de ejecución global del módulo.

        Args:
            running (bool): True para habilitar visualización activa.
        """
        self._image_handler.set_process_running(running)
        self._set_ui_running_state(running)
        if not running:
            self._image_handler.set_static_image()

    def get_angular_layout(self):
        """
        Retorna el layout destinado a las gráficas angulares.

        Returns:
            QGridLayout: Layout angular.
        """
        return self.angular_layout

    def get_cartesian_layout(self):
        """
        Retorna el layout destinado a las gráficas cartesianas.

        Returns:
            QGridLayout: Layout cartesiano.
        """
        return self.cartesian_layout

    def set_cartesian_pid_widget(self, widget):
        """
        Reemplaza el contenido del layout cartesiano con un widget embebido.

        Limpia el layout actual (removiendo plots PyQtGraph anteriores)
        y agrega el widget de matplotlib para el PID cartesiano.

        Args:
            widget (QWidget): Widget CartesianPIDPlot a insertar.
        """
        while self.cartesian_layout.count():
            item = self.cartesian_layout.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()
        self.cartesian_layout.addWidget(widget)

    def get_image_handler(self):
        """
        Retorna el manejador de imágenes interno.

        Returns:
            ImageHandler: Manejador de placeholder.
        """
        return self._image_handler

    def resizeEvent(self, event):
        """
        Notifica cambios de tamaño para reajustar la disposición de las gráficas.
        """
        super().resizeEvent(event)
        self.resize_requested.emit(self.width())
