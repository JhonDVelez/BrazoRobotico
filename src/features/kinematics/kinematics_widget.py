"""
Modulo que define la interfaz visual para el control cartesiano.

Este modulo contiene la clase KinematicsWidget, la cual permite al usuario
ingresar las coordenadas X, Y, Z deseadas para el efector final del robot.

Conexiones:
    - Emite `send_clicked` para notificar al controlador que se desea mover el robot.
    - Soporta layouts dinamicos (horizontal/vertical) para adaptarse a la UI principal.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QSpinBox, QPushButton, QSizePolicy
from PyQt6.QtCore import QSize, pyqtSignal


class KinematicsWidget(QWidget):
    """
    Widget para la entrada de coordenadas cinematicas (X, Y, Z).

    Organiza campos de entrada numerica (QSpinBox) y permite la alternancia
    entre una disposicion vertical (por defecto) y una horizontal segun el
    espacio disponible en la ventana principal.

    Attributes:
        send_clicked (pyqtSignal): Emite al presionar el boton 'Enviar'.
    """
    send_clicked = pyqtSignal()

    def __init__(self, parent=None):
        """
        Inicializa el widget cinematico y su interfaz.

        Args:
            parent (QWidget, optional): Widget padre.
        """
        super().__init__(parent)
        self.__setup_ui()

    def __setup_ui(self):
        """
        Configura los componentes de entrada y el boton de envio.
        """
        self.setObjectName("kinematics_widget")
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setObjectName("verticalLayout")
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.holder_widget = QWidget(self)
        self.container = QGridLayout(self.holder_widget)
        self.container.setObjectName("gridLayout")

        self._labels = {}
        self._spins = {}

        # Configuración de ejes: (Etiqueta, Minimo, Maximo)
        axes_config = [("X", 0, 200), ("Y", -200, 200), ("Z", 0, 520)]
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

            # Layout inicial vertical (etiqueta a la izquierda, spin a la derecha)
            self.container.addWidget(label, i, 0)
            self.container.addWidget(spin, i, 1)

        self.coordinates_button = QPushButton("Enviar")
        self.coordinates_button.setObjectName("send_kinematics")
        self.coordinates_button.setMinimumHeight(40)
        self.coordinates_button.clicked.connect(self.send_clicked)
        self.coordinates_button.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.main_layout.addWidget(self.holder_widget)
        h = QHBoxLayout()
        h.addStretch()
        h.addWidget(self.coordinates_button)
        h.addStretch()
        self.main_layout.addLayout(h)

    def set_horizontal_layout(self):
        """
        Reorganiza los controles en una fila horizontal (ideal para paneles anchos).
        """
        self._clear_layout()
        for i, key in enumerate(self._keys):
            self.container.addWidget(self._labels[key], 0, i)
            self.container.addWidget(self._spins[key], 1, i)

    def set_vertical_layout(self):
        """
        Reorganiza los controles en una columna vertical (ideal para paneles laterales).
        """
        self._clear_layout()
        for i, key in enumerate(self._keys):
            self.container.addWidget(self._labels[key], i, 0)
            self.container.addWidget(self._spins[key], i, 1)

    def _clear_layout(self):
        """
        Elimina todas las asociaciones de widgets del layout grid sin destruirlos.
        """
        while self.container.count():
            item = self.container.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

    # --- API Pública (Getters / Setters) ---

    def get_coordinates(self):
        """
        Obtiene los valores actuales ingresados en los spinboxes.

        Returns:
            dict: Diccionario con claves 'x', 'y', 'z' y sus valores.
        """
        return {key: spin.value() for key, spin in self._spins.items()}

    def set_coordinates(self, coords: dict):
        """
        Establece nuevos valores en los campos de entrada.

        Args:
            coords (dict): Diccionario con las coordenadas a cargar.
        """
        for key, val in coords.items():
            if key in self._spins:
                self._spins[key].setValue(val)

    def resizeEvent(self, event):
        super().resizeEvent(event)

        self.coordinates_button.setFixedWidth(self.width() // 2)
