"""
Módulo que define la interfaz de control manual por articulación.

Este módulo contiene la clase SlidersWidget, la cual organiza los 6 mandos
individuales (θ1 a θ6) para el control directo de los servos del brazo robótico,
permitiendo ajustes tanto finos (SpinBox) como rápidos (Slider).

Los valores representan directamente los ángulos articulares del robot
(espacio angular), no las posiciones absolutas del servo (0-300).

Conexiones:
    - Emite `value_changed` con el índice del motor y el valor angular.
    - Mantiene una sincronización bidireccional entre sliders y cajas numéricas.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QSlider, QSpinBox, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal
from src.services.ui.flow_layout import FlowLayout


class SlidersWidget(QWidget):
    """
    Widget encargado de la interfaz visual de los controles deslizantes (θ1-θ6).

    Organiza los controles en una cuadrícula fluida, aplicando
    límites físicos de seguridad específicos para cada articulación del robot.

    Los valores emitidos y recibidos están en espacio angular (ángulos del usuario).

    Attributes:
        value_changed (pyqtSignal): Emite (indice_motor, valor_angular).
    """
    value_changed = pyqtSignal(int, int)

    # Rangos angulares por articulación: (label, min, max)
    THETA_CONFIG = [
        ("θ1", -100, 100),
        ("θ2", -90, 90),
        ("θ3", -130, 130),
        ("θ4", -100, 100),
        ("θ5", -90, 120),
        ("θ6", -100, 20),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._controls = []
        self.__setup_ui()

    def __setup_ui(self):
        self.setObjectName("sliders_widget")
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5)

        self.container_widget = QWidget()
        self.flow_layout = FlowLayout(self.container_widget, spacing=10)

        for i, (text, s_min, s_max) in enumerate(self.THETA_CONFIG):
            group_widget = QWidget()
            group_widget.setMinimumWidth(200)
            group_layout = QHBoxLayout(group_widget)
            group_layout.setContentsMargins(2, 2, 2, 2)
            group_layout.setSpacing(5)

            label = QLabel(text)
            label.setFixedSize(25, 30)
            group_layout.addWidget(label)

            # Slider en espacio angular
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(s_min, s_max)
            slider.setValue(0)
            slider.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            slider.setMinimumWidth(100)
            group_layout.addWidget(slider)

            # SpinBox en espacio angular (mismo rango que el slider)
            spin = QSpinBox()
            spin.setRange(s_min, s_max)
            spin.setValue(0)
            spin.setFixedSize(55, 30)
            group_layout.addWidget(spin)

            # Sincronización interna (sin offset)
            slider.valueChanged.connect(lambda val, s=spin: self._sync_spin(s, val))
            spin.valueChanged.connect(lambda val, s=slider: self._sync_slider(s, val))
            slider.valueChanged.connect(lambda val, idx=i: self.value_changed.emit(idx, val))
            spin.valueChanged.connect(lambda val, idx=i: self.value_changed.emit(idx, val))

            self.flow_layout.addWidget(group_widget)
            self._controls.append({"slider": slider, "spinbox": spin})

        self.main_layout.addWidget(self.container_widget)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        self.setMinimumSize(625, 90)

    def _sync_spin(self, spin, value):
        spin.blockSignals(True)
        spin.setValue(value)
        spin.blockSignals(False)

    def _sync_slider(self, slider, value):
        slider.blockSignals(True)
        slider.setValue(value)
        slider.blockSignals(False)

    # --- API Pública ---

    def set_values(self, values: list):
        """Establece valores angulares en todos los mandos.

        Args:
            values (list): Lista de 6 valores angulares.
        """
        if len(values) != 6:
            return
        self.blockSignals(True)
        for i, val in enumerate(values):
            self._controls[i]["slider"].blockSignals(True)
            self._controls[i]["slider"].setValue(int(val))
            self._controls[i]["slider"].blockSignals(False)

            self._controls[i]["spinbox"].blockSignals(True)
            self._controls[i]["spinbox"].setValue(int(val))
            self._controls[i]["spinbox"].blockSignals(False)
        self.blockSignals(False)

    def get_values(self) -> list:
        """Retorna los valores angulares actuales de todos los mandos.

        Returns:
            list: Lista de 6 enteros angulares.
        """
        return [c["slider"].value() for c in self._controls]

    def reset_ui(self):
        """Reinicia visualmente todos los mandos a la posición central (0)."""
        for ctrl in self._controls:
            ctrl["slider"].setValue(0)
