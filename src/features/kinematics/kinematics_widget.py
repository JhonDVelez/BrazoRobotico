"""
Módulo que define la interfaz visual para el control cartesiano.

Este módulo contiene la clase KinematicsWidget, la cual permite al usuario
ingresar las coordenadas X, Y, Z deseadas para el efector final del robot
y ajustar las ganancias PID del controlador.

Conexiones:
    - Emite `send_clicked` para notificar al controlador que se desea mover el robot.
    - Soporta layouts dinámicos (horizontal/vertical) para adaptarse a la UI principal.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QSpinBox, QDoubleSpinBox, QPushButton, QSizePolicy
)
from PyQt6.QtCore import QSize, pyqtSignal, Qt


class KinematicsWidget(QWidget):
    """
    Widget para la entrada de coordenadas cinemáticas y ganancias PID.

    Organiza campos de entrada numérica (QSpinBox / QDoubleSpinBox) y permite
    la alternancia entre disposiciones verticales y horizontales.

    Attributes:
        send_clicked (pyqtSignal): Emite al presionar el boton 'Enviar'.
    """
    send_clicked = pyqtSignal()

    # Valores por defecto de las ganancias PID
    DEFAULT_KP = [1.5, 1.0, 1.38]
    DEFAULT_KI = [0.9375, 0.0, 0.69]
    DEFAULT_KD = [0.06, 0.0, 0.069]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.__setup_ui()

    def __setup_ui(self):
        self.setObjectName("kinematics_widget")
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setObjectName("verticalLayout")
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.holder_widget = QWidget(self)
        self.container = QGridLayout(self.holder_widget)
        self.container.setObjectName("gridLayout")

        self._labels = {}
        self._spins = {}

        axes_config = [("X", 0, 150), ("Y", -180, 180), ("Z", 0, 250)]
        self._keys = ["x", "y", "z"]

        for i, (text, s_min, s_max) in enumerate(axes_config):
            label = QLabel(text, self.holder_widget)
            label.setMaximumSize(QSize(100, 16777215))
            self._labels[self._keys[i]] = label

            spin = QSpinBox(self.holder_widget)
            spin.setSizePolicy(QSizePolicy(
                QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed))
            spin.setMaximumSize(QSize(200, 16777215))
            spin.setRange(s_min, s_max)
            self._spins[self._keys[i]] = spin

            self.container.addWidget(label, i, 0)
            self.container.addWidget(spin, i, 1)

        self.coordinates_button = QPushButton("Enviar")
        self.coordinates_button.setObjectName("send_kinematics")
        self.coordinates_button.setMinimumHeight(40)
        self.coordinates_button.clicked.connect(self.send_clicked)
        self.coordinates_button.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.main_layout.addWidget(self.holder_widget)

        # --- Sección de Ganancias PID ---
        self._pid_container = QWidget(self)
        pid_grid = QGridLayout(self._pid_container)
        pid_grid.setObjectName("pidGridLayout")
        pid_grid.setContentsMargins(0, 0, 0, 0)

        pid_title = QLabel("Ganancias PID")
        pid_title.setStyleSheet("font-weight: bold;")
        pid_grid.addWidget(pid_title, 0, 0, 1, 4)

        pid_headers = ["", "X", "Y", "Z"]
        for col, text in enumerate(pid_headers):
            lbl = QLabel(text, self._pid_container)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pid_grid.addWidget(lbl, 1, col)

        self._pid_spins = {}
        pid_defaults = {"kp": self.DEFAULT_KP, "ki": self.DEFAULT_KI, "kd": self.DEFAULT_KD}
        pid_labels_map = {"kp": "Kp", "ki": "Ki", "kd": "Kd"}

        for row, (gain_key, defaults) in enumerate(pid_defaults.items(), start=2):
            lbl = QLabel(pid_labels_map[gain_key], self._pid_container)
            pid_grid.addWidget(lbl, row, 0)

            self._pid_spins[gain_key] = {}
            for col, axis_key in enumerate(self._keys):
                dsb = QDoubleSpinBox(self._pid_container)
                dsb.setDecimals(4)
                dsb.setRange(0.0, 100.0)
                dsb.setSingleStep(0.01)
                dsb.setValue(defaults[col])
                dsb.setSizePolicy(QSizePolicy(
                    QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed))
                dsb.setMaximumSize(QSize(200, 16777215))
                self._pid_spins[gain_key][axis_key] = dsb
                pid_grid.addWidget(dsb, row, col + 1)

        self.main_layout.addWidget(self._pid_container)

        h = QHBoxLayout()
        h.addStretch()
        h.addWidget(self.coordinates_button)
        h.addStretch()
        self.main_layout.addLayout(h)

    def set_horizontal_layout(self):
        self._clear_layout()
        for i, key in enumerate(self._keys):
            self.container.addWidget(self._labels[key], 0, i)
            self.container.addWidget(self._spins[key], 1, i)

    def set_vertical_layout(self):
        self._clear_layout()
        for i, key in enumerate(self._keys):
            self.container.addWidget(self._labels[key], i, 0)
            self.container.addWidget(self._spins[key], i, 1)

    def _clear_layout(self):
        while self.container.count():
            item = self.container.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

    # --- API Pública ---

    def get_coordinates(self):
        return {key: spin.value() for key, spin in self._spins.items()}

    def set_coordinates(self, coords: dict):
        for key, val in coords.items():
            if key in self._spins:
                self._spins[key].setValue(val)

    def get_pid_gains(self):
        """Obtiene las ganancias PID actuales de los spinboxes.

        Returns:
            dict: {"kp": [x,y,z], "ki": [x,y,z], "kd": [x,y,z]}
        """
        return {
            gain: [self._pid_spins[gain][axis].value() for axis in self._keys]
            for gain in self._pid_spins
        }

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.coordinates_button.setFixedWidth(self.width() // 2)
