"""
Modulo que define la interfaz de control manual por articulacion.

Este modulo contiene la clase SlidersWidget, la cual organiza los 6 mandos
individuales (θ1 a θ6) para el control directo de los servos del brazo robotico,
permitiendo ajustes tanto finos (SpinBox) como rapidos (Slider).

Conexiones:
    - Emite `value_changed` con el indice del motor y el valor absoluto (0-300).
    - Mantiene una sincronizacion bidireccional entre sliders y cajas numericas.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QLabel, QSlider, QSpinBox, QSizePolicy)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from src.services.ui.flow_layout import FlowLayout


class SlidersWidget(QWidget):
    """
    Widget encargado de la interfaz visual de los controles deslizantes (θ1-θ6).

    Organiza los controles en una cuadricula de 2 filas y 3 columnas, aplicando
    limites fisicos de seguridad especificos para cada articulacion del robot.

    Attributes:
        value_changed (pyqtSignal): Emite (indice_motor, valor_absoluto) donde
            valor_absoluto esta en el rango [0, 300].
    """
    value_changed = pyqtSignal(int, int)  # index, value (0-300 range)

    def __init__(self, parent=None):
        """
        Inicializa el widget de sliders y sus controles internos.

        Args:
            parent (QWidget, optional): Widget padre.
        """
        super().__init__(parent)
        self._controls = []
        self.__setup_ui()

    def __setup_ui(self):
        """
        Configura el layout fluido de controles y aplica las restricciones de hardware.
        """
        self.setObjectName("sliders_widget")
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5)

        self.container_widget = QWidget()
        self.flow_layout = FlowLayout(self.container_widget, spacing=10)
        
        # Configuracion θ: (label, min_absoluto, max_absoluto)
        theta_config = [
            ("θ1", 50, 250), ("θ2", 60, 240), ("θ3", 20, 280),
            ("θ4", 50, 250), ("θ5", 60, 270), ("θ6", 42, 171)
        ]

        for i, (text, s_min, s_max) in enumerate(theta_config):
            group_widget = QWidget()
            group_widget.setMinimumWidth(200) # Tamaño mínimo para que no se colapse demasiado
            group_layout = QHBoxLayout(group_widget)
            group_layout.setContentsMargins(2, 2, 2, 2)
            group_layout.setSpacing(5)

            # Etiqueta de identificacion
            label = QLabel(text)
            label.setFixedSize(25, 30)
            group_layout.addWidget(label)

            # Slider para control rapido
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(s_min, s_max)
            slider.setValue(150)
            slider.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            slider.setMinimumWidth(100)
            group_layout.addWidget(slider)

            # SpinBox para control de precision
            spin = QSpinBox()
            spin.setRange(s_min - 150, s_max - 150)
            spin.setValue(0)
            spin.setFixedSize(55, 30)
            group_layout.addWidget(spin)

            # Sincronización interna
            slider.valueChanged.connect(lambda val, s=spin: self._sync_spin(s, val))
            spin.valueChanged.connect(lambda val, s=slider: self._sync_slider(s, val))
            slider.valueChanged.connect(lambda val, idx=i: self.value_changed.emit(idx, val))
            spin.valueChanged.connect(lambda val, idx=i: self.value_changed.emit(idx, val + 150))

            self.flow_layout.addWidget(group_widget)
            self._controls.append({"slider": slider, "spinbox": spin})

        self.main_layout.addWidget(self.container_widget)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        self.setMinimumSize(220, 100)

    def _sync_spin(self, spin, value):
        """
        Actualiza el spinbox basandose en el valor absoluto del slider.

        Args:
            spin (QSpinBox): Widget a actualizar.
            value (int): Valor absoluto (0-300).
        """
        spin.blockSignals(True)
        spin.setValue(value - 150)
        spin.blockSignals(False)

    def _sync_slider(self, slider, value):
        """
        Actualiza el slider basandose en el valor relativo del spinbox.

        Args:
            slider (QSlider): Widget a actualizar.
            value (int): Valor relativo (-150 a 150).
        """
        slider.blockSignals(True)
        slider.setValue(value + 150)
        slider.blockSignals(False)

    # --- API Pública (Getters / Setters) ---

    def set_values(self, values: list):
        """
        Actualiza forzosamente todos los widgets con una nueva lista de valores.

        Bloquea señales para evitar bucles de retroalimentacion con el controlador.

        Args:
            values (list): Lista de 6 valores absolutos (rango 0-300).
        """
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
        """
        Retorna los valores absolutos actuales de todos los mandos.

        Returns:
            list: Lista de 6 enteros.
        """
        return [c["slider"].value() for c in self._controls]

    def reset_ui(self):
        """
        Reinicia visualmente todos los mandos a su posicion central (150).
        """
        for ctrl in self._controls:
            ctrl["slider"].setValue(150)
