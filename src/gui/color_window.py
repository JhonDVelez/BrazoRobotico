"""Ventana de calibración de colores HSV para detección de elipses."""
from PyQt6.QtWidgets import (
    QVBoxLayout, QGridLayout, QPushButton, QApplication, QWidget,
    QHBoxLayout, QSizePolicy, QLabel, QSlider, QSpinBox, QComboBox
)
from PyQt6.QtCore import QSize, QCoreApplication, Qt
from PyQt6.QtGui import QFont, QIcon
import os
from qframelesswindow import FramelessMainWindow
from gui.main_window import MainTitleBarMixin, CalibrationMenuMixin, MainThemeMixin, ThemeManager
from gui.camera_interface import CameraInterface
from gui.color_interface import ColorInterface
from gui.device_monitor import get_device_monitor
from data import config_manager as cfg


class ColorWindow(FramelessMainWindow, CalibrationMenuMixin, MainThemeMixin):
    """Ventana para calibración de colores HSV."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Calibración De Colores")

        # Inicializar tema manager
        self.theme_manager = ThemeManager.get_instance()
        self.actual_theme = None

        # Crear atributos para iconos de tema (necesarios para MainThemeMixin)
        self.sun_icon = QIcon(os.path.join("icons:sun.png"))
        self.moon_icon = QIcon(os.path.join("icons:moon.png"))

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Barra de título
        self.create_calibration_menu()
        self.create_status_bar()
        self.title_bar = MainTitleBarMixin(self, "Calibración De Colores")
        self.setTitleBar(self.title_bar)
        layout.addWidget(self.title_bar)

        self.central_widget = QWidget()
        self.setup_ui(self.central_widget)
        self.color_interface = ColorInterface(self)

        layout.addWidget(self.central_widget)
        self.setCentralWidget(container)

        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        self.resize(int(screen_geometry.width() * 0.75),
                    int(screen_geometry.height() * 0.75))
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)

        self.setup_connections()
        self.clear_camera_selection()

        # Cargar el tema actual
        self._load_current_theme()

        # Instalar monitor de dispositivos multiplataforma (solo para cámaras)
        self._device_monitor = get_device_monitor(
            camera_callback=self.get_cameras, camera_only=True)
        self._device_monitor.install_filter(QCoreApplication.instance())
        self.get_cameras()

    def setup_ui(self, main_widget):
        """Configura la interfaz con malla 2x2."""
        self.main_widget = main_widget
        self.main_widget.setObjectName("MainWidget")
        self.main_widget.setMinimumSize(QSize(600, 600))

        sizePolicy = QSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Preferred
        )
        self.main_widget.setSizePolicy(sizePolicy)

        # Layout principal: Malla
        main_grid = QGridLayout(self.main_widget)
        main_grid.setContentsMargins(5, 5, 5, 5)
        main_grid.setSpacing(5)
        main_grid.setRowStretch(0, 1)
        main_grid.setRowStretch(1, 1)
        main_grid.setColumnStretch(0, 1)
        main_grid.setColumnStretch(1, 1)

        # Imagen original de la cámara.
        self.camera_interface = CameraInterface(self, is_calibration=True)
        main_grid.addWidget(self.camera_interface, 0, 0)

        # Máscara HSV calculada con los sliders.
        self.mask_label = self._create_image_label("Máscara HSV")
        main_grid.addWidget(self.mask_label, 1, 0)

        # Panel superior derecho con botón de cámara, título y sliders HSV.
        self.controls_widget = QWidget()
        controls_layout = QVBoxLayout(self.controls_widget)
        controls_layout.setContentsMargins(5, 5, 5, 5)
        controls_layout.setSpacing(8)

        self.top_controls_widget = QWidget()
        top_controls_layout = QHBoxLayout(self.top_controls_widget)
        top_controls_layout.setContentsMargins(0, 0, 0, 0)
        top_controls_layout.setSpacing(10)

        self.camera_toggle_button = QPushButton("Camara")
        self.camera_toggle_button.setFixedSize(90, 30)
        self.camera_toggle_button.setCheckable(True)
        self.camera_toggle_button.setStyleSheet("border: none; padding: 4px;")
        top_controls_layout.addWidget(self.camera_toggle_button)

        self.info_label = QLabel("Controles de Color")
        self.info_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        top_controls_layout.addWidget(self.info_label)

        controls_layout.addWidget(self.top_controls_widget)

        color_selector_layout = QHBoxLayout()
        color_selector_label = QLabel("Color")
        color_selector_label.setFixedWidth(60)
        color_selector_layout.addWidget(color_selector_label)

        self.color_selector = QComboBox()
        self.color_selector.addItems(ColorInterface.COLORS)
        color_selector_layout.addWidget(self.color_selector)
        controls_layout.addLayout(color_selector_layout)

        default_values = ColorInterface.load_default_values()

        # Crear barras deslizantes para cada parámetro HSV
        self.hsv_sliders = {}
        slider_specs = [
            ("H Min", "h_min", 0, 180),
            ("H Max", "h_max", 0, 180),
            ("S Min", "s_min", 0, 255),
            ("S Max", "s_max", 0, 255),
            ("V Min", "v_min", 0, 255),
            ("V Max", "v_max", 0, 255),
        ]

        for label_text, key, min_val, max_val in slider_specs:
            row_layout = QHBoxLayout()

            label = QLabel(label_text)
            label.setFixedWidth(60)
            row_layout.addWidget(label)

            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setMinimum(min_val)
            slider.setMaximum(max_val)
            slider.setValue(default_values[key])
            slider.setFixedHeight(25)
            row_layout.addWidget(slider)

            spinbox = QSpinBox()
            spinbox.setMinimum(min_val)
            spinbox.setMaximum(max_val)
            spinbox.setValue(default_values[key])
            spinbox.setFixedWidth(60)
            row_layout.addWidget(spinbox)

            self.hsv_sliders[key] = {
                "slider": slider,
                "spinbox": spinbox,
                "label": label_text
            }

            controls_layout.addLayout(row_layout)

        # Botón Guardar
        self.save_button = QPushButton("Guardar Configuración")
        self.save_button.setMinimumHeight(35)
        controls_layout.addWidget(self.save_button)

        controls_layout.addStretch()

        main_grid.addWidget(self.controls_widget, 0, 1)

        # Resultado de aplicar la máscara al frame original.
        self.result_label = self._create_image_label("Resultado HSV")
        main_grid.addWidget(self.result_label, 1, 1)

    def _create_image_label(self, text: str):
        """Crea un QLabel preparado para mostrar imágenes escaladas."""
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setMinimumSize(QSize(240, 180))
        label.setScaledContents(False)
        label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        return label

    def setup_connections(self):
        """Configura las conexiones de eventos."""
        self.color_interface.setup_connections()
        # Conectar acción de tema al toggle
        if hasattr(self, 'theme_action'):
            self.theme_action.triggered.connect(self.toggle_theme_event)
        # Conectar cambios de tema
        self.theme_manager.theme_changed.connect(self._on_theme_changed)

    def _load_current_theme(self):
        """Carga el tema actual desde la configuración."""
        theme = cfg.get("settings.json", "theme", default="dark").lower()
        is_dark = theme == "dark"
        if is_dark:
            self.load_dark_theme()
        else:
            self.load_light_theme()
        self.actual_theme = Qt.ColorScheme.Dark if is_dark else Qt.ColorScheme.Light

    def _on_theme_changed(self, is_dark: bool):
        """Maneja el cambio de tema desde el ThemeManager."""
        self._apply_theme_from_signal(is_dark)

    def closeEvent(self, event):
        """Maneja el cierre de la ventana."""
        if hasattr(self, "color_interface"):
            self.color_interface.close()
        self.clear_camera_selection()
        if hasattr(self, "_device_monitor"):
            self._device_monitor.uninstall_filter()
        event.accept()
