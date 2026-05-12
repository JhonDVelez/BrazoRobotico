from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLabel, QSpinBox, QPushButton, QSizePolicy
from PyQt6.QtCore import Qt, QSize, pyqtSignal

class KinematicsWidget(QWidget):
    """
    Widget encargado de la interfaz visual de control cinemático (X, Y, Z).
    Permite la entrada de coordenadas y emite la señal de envío.
    """
    send_clicked = pyqtSignal()

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
        
        axes_config = [("X", 0, 270), ("Y", 0, 200), ("Z", 0, 520)]
        self._keys = ["x", "y", "z"]

        for i, (text, s_min, s_max) in enumerate(axes_config):
            label = QLabel(text, self.holder_widget)
            label.setMaximumSize(QSize(100, 16777215))
            self._labels[self._keys[i]] = label
            
            spin = QSpinBox(self.holder_widget)
            spin.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed))
            spin.setMaximumSize(QSize(200, 16777215))
            spin.setRange(s_min, s_max)
            self._spins[self._keys[i]] = spin
            
            # Layout inicial vertical
            self.container.addWidget(label, i, 0)
            self.container.addWidget(spin, i, 1)

        self.coordinates_button = QPushButton("Enviar")
        self.coordinates_button.setMinimumHeight(40)
        self.coordinates_button.clicked.connect(self.send_clicked)

        self.main_layout.addWidget(self.holder_widget)
        self.main_layout.addWidget(self.coordinates_button)

    def set_horizontal_layout(self):
        """ Reorganiza los controles en una fila horizontal """
        self._clear_layout()
        for i, key in enumerate(self._keys):
            self.container.addWidget(self._labels[key], 0, i)
            self.container.addWidget(self._spins[key], 1, i)

    def set_vertical_layout(self):
        """ Reorganiza los controles en una columna vertical """
        self._clear_layout()
        for i, key in enumerate(self._keys):
            self.container.addWidget(self._labels[key], i, 0)
            self.container.addWidget(self._spins[key], i, 1)

    def _clear_layout(self):
        while self.container.count():
            item = self.container.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

    # --- API Pública (Getters / Setters) ---

    def get_coordinates(self):
        return {key: spin.value() for key, spin in self._spins.items()}

    def set_coordinates(self, coords: dict):
        for key, val in coords.items():
            if key in self._spins:
                self._spins[key].setValue(val)
