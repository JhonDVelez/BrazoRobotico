from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QLabel, QSlider, QSpinBox, QSizePolicy)
from PyQt6.QtCore import Qt, QSize, pyqtSignal


class SlidersWidget(QWidget):
    """
    Widget encargado de la interfaz visual de los controles deslizantes (θ1-θ6).
    Mantiene la paridad visual exacta con el diseño original (3 columnas x 2 filas).
    """
    value_changed = pyqtSignal(int, int)  # index, value (0-300 range)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._controls = []
        self.__setup_ui()

    def __setup_ui(self):
        self.setObjectName("sliders_widget")
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.container_widget = QWidget()
        self.grid_layout = QGridLayout(self.container_widget)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(10)

        # Configuración θ: (label, min, max)
        theta_config = [
            ("θ1", 50, 250), ("θ2", 60, 240), ("θ3", 30, 270),
            ("θ4", 50, 250), ("θ5", 39, 270), ("θ6", 38, 171)
        ]

        for i, (text, s_min, s_max) in enumerate(theta_config):
            row, col = i // 3, i % 3

            group_widget = QWidget()
            group_layout = QHBoxLayout(group_widget)
            group_layout.setContentsMargins(0, 0, 0, 0)

            # Label
            label = QLabel(text)
            label.setFixedSize(30, 30)
            group_layout.addWidget(label)

            # Slider (Internamente manejamos 0-300, pero visualmente se limita por config)
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(s_min, s_max)
            slider.setValue(150)
            slider.setMaximumSize(QSize(400, 30))
            group_layout.addWidget(slider)

            # SpinBox (Muestra valor - 150)
            spin = QSpinBox()
            spin.setRange(s_min - 150, s_max - 150)
            spin.setValue(0)
            spin.setFixedSize(60, 30)
            group_layout.addWidget(spin)

            # Sincronización interna Widget
            slider.valueChanged.connect(
                lambda val, s=spin: self._sync_spin(s, val))
            spin.valueChanged.connect(
                lambda val, s=slider: self._sync_slider(s, val))

            # Notificación al controlador (desde ambos widgets)
            slider.valueChanged.connect(
                lambda val, idx=i: self.value_changed.emit(idx, val))
            spin.valueChanged.connect(
                lambda val, idx=i: self.value_changed.emit(idx, val + 150))

            self.grid_layout.addWidget(group_widget, row, col)
            self._controls.append({"slider": slider, "spinbox": spin})

        self.main_layout.addWidget(self.container_widget)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)
        self.setMinimumSize(120, 160)

    def _sync_spin(self, spin, value):
        spin.blockSignals(True)
        spin.setValue(value - 150)
        spin.blockSignals(False)

    def _sync_slider(self, slider, value):
        slider.blockSignals(True)
        slider.setValue(value + 150)
        slider.blockSignals(False)

    # --- API Pública (Getters / Setters) ---

    def set_values(self, values: list):
        """ Actualiza los widgets con una lista de 6 valores (rango 0-300) """
        if len(values) != 6:
            return
        self.blockSignals(True)
        for i, val in enumerate(values):
            # Actualizar Slider
            self._controls[i]["slider"].blockSignals(True)
            self._controls[i]["slider"].setValue(int(val))
            self._controls[i]["slider"].blockSignals(False)

            # Actualizar SpinBox
            self._controls[i]["spinbox"].blockSignals(True)
            self._controls[i]["spinbox"].setValue(int(val) - 150)
            self._controls[i]["spinbox"].blockSignals(False)
        self.blockSignals(False)

    def get_values(self) -> list:
        """ Retorna los valores actuales de los widgets """
        return [c["slider"].value() for c in self._controls]

    def reset_ui(self):
        """ Reinicia los widgets a la posición central """
        for ctrl in self._controls:
            ctrl["slider"].setValue(150)
