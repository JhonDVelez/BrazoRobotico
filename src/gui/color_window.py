"""Ventana de calibración de colores HSV para detección de elipses."""
from PyQt6.QtWidgets import (
    QVBoxLayout, QGridLayout, QPushButton, QApplication, QWidget,
    QHBoxLayout, QSizePolicy, QLabel, QSlider, QSpinBox
)
from PyQt6.QtCore import QSize, QCoreApplication, Qt
from PyQt6.QtGui import QFont
from qframelesswindow import FramelessMainWindow
from gui.main_window import MainTitleBarMixin, CalibrationMenuMixin, MainThemeMixin, ThemeManager
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

        # ColorInterface (ocupa la izquierda, 2 filas)
        self.color_interface = ColorInterface(self)
        main_grid.addWidget(self.color_interface, 0, 0, 2, 1)

        # Panel de controles superior derecho (QLabel)
        self.info_label = QLabel("Controles de Color")
        self.info_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_grid.addWidget(self.info_label, 0, 1)

        # Panel de barras HSV (inferior derecho, QWidget)
        self.controls_widget = QWidget()
        controls_layout = QVBoxLayout(self.controls_widget)
        controls_layout.setContentsMargins(5, 5, 5, 5)
        controls_layout.setSpacing(5)

        # Cargar valores desde config
        hsv_config = cfg.get("camera.json", "hsv_colors", default={})
        default_color = list(hsv_config.values())[0] if hsv_config else [
            0, 0, 0, 180, 255, 255]

        # Crear barras deslizantes para cada parámetro HSV
        self.hsv_sliders = {}
        labels_text = [
            ("H Min", 0, 180),
            ("S Min", 0, 255),
            ("V Min", 0, 255),
            ("H Max", 0, 180),
            ("S Max", 0, 255),
            ("V Max", 0, 255),
        ]

        for idx, (label_text, min_val, max_val) in enumerate(labels_text):
            row_layout = QHBoxLayout()

            label = QLabel(label_text)
            label.setFixedWidth(60)
            row_layout.addWidget(label)

            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setMinimum(min_val)
            slider.setMaximum(max_val)
            slider.setValue(default_color[idx])
            slider.setFixedHeight(25)
            row_layout.addWidget(slider)

            spinbox = QSpinBox()
            spinbox.setMinimum(min_val)
            spinbox.setMaximum(max_val)
            spinbox.setValue(default_color[idx])
            spinbox.setFixedWidth(60)
            row_layout.addWidget(spinbox)

            key = ["h_min", "s_min", "v_min", "h_max", "s_max", "v_max"][idx]
            self.hsv_sliders[key] = {
                "slider": slider,
                "spinbox": spinbox,
                "label": label_text
            }

            # Conectar slider y spinbox
            slider.valueChanged.connect(
                lambda val, key=key: self._on_slider_changed(key, val))
            spinbox.valueChanged.connect(
                lambda val, key=key: self._on_spinbox_changed(key, val))

            controls_layout.addLayout(row_layout)

        # Botón Guardar
        self.save_button = QPushButton("Guardar Configuración")
        self.save_button.setMinimumHeight(35)
        controls_layout.addWidget(self.save_button)

        controls_layout.addStretch()

        main_grid.addWidget(self.controls_widget, 1, 1)

    def _on_slider_changed(self, key: str, value: int):
        """Actualiza el spinbox cuando se mueve el slider."""
        self.hsv_sliders[key]["spinbox"].blockSignals(True)
        self.hsv_sliders[key]["spinbox"].setValue(value)
        self.hsv_sliders[key]["spinbox"].blockSignals(False)
        self._update_color_interface()

    def _on_spinbox_changed(self, key: str, value: int):
        """Actualiza el slider cuando se cambia el spinbox."""
        self.hsv_sliders[key]["slider"].blockSignals(True)
        self.hsv_sliders[key]["slider"].setValue(value)
        self.hsv_sliders[key]["slider"].blockSignals(False)
        self._update_color_interface()

    def _update_color_interface(self):
        """Actualiza la interfaz de color con los valores actuales."""
        values = {key: data["spinbox"].value()
                  for key, data in self.hsv_sliders.items()}
        self.color_interface.update_hsv_values(
            values["h_min"],
            values["s_min"],
            values["v_min"],
            values["h_max"],
            values["s_max"],
            values["v_max"]
        )

    def setup_connections(self):
        """Configura las conexiones de eventos."""
        if hasattr(self, 'save_button'):
            self.save_button.clicked.connect(self.save_color_config)
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
        """Maneja el cambio de tema."""
        if is_dark:
            self.load_dark_theme()
        else:
            self.load_light_theme()

    def save_color_config(self):
        """Guarda la configuración de colores en el JSON."""
        values = [
            self.hsv_sliders["h_min"]["spinbox"].value(),
            self.hsv_sliders["s_min"]["spinbox"].value(),
            self.hsv_sliders["v_min"]["spinbox"].value(),
            self.hsv_sliders["h_max"]["spinbox"].value(),
            self.hsv_sliders["s_max"]["spinbox"].value(),
            self.hsv_sliders["v_max"]["spinbox"].value(),
        ]

        # Obtenemos el color seleccionado (por ahora lo guardamos como "custom")
        cfg.set_value("camera.json", "hsv_colors", "custom", value=values)
        print(f"Configuración de color guardada: {values}")

    def closeEvent(self, event):
        """Maneja el cierre de la ventana."""
        if hasattr(self, "color_interface"):
            self.color_interface.stop_video()
        self.clear_camera_selection()
        if hasattr(self, "_device_monitor"):
            self._device_monitor.uninstall_filter()
        event.accept()
