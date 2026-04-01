import numpy as np
from PyQt6.QtWidgets import QWidget, QSizePolicy, QPushButton, QGridLayout, QLabel, QSlider
from PyQt6.QtWidgets import QSpinBox, QVBoxLayout
from PyQt6.QtCore import Qt, QSize
from gui.kinematics_worker import KinematicsWorker
from data import SimulationSignalManager, PhysicalSignalManager, Modes
from data import deg_to_rad, rad_to_deg


class KinematicsWidget(QWidget):

    kinematics_status = [150, 150, 150, 150, 150, 150]

    def __init__(self):
        super().__init__()
        self.__setup_ui()
        self.setup_connections()

    def __setup_ui(self):
        # Layout principal
        self.vertical_layout = QVBoxLayout(self)
        self.vertical_layout.setObjectName("verticalLayout")

        # Widget con labels y spinboxes
        self.widget = QWidget(self)
        self.widget.setObjectName("widget")
        self.container = QGridLayout(self.widget)
        self.container.setObjectName("gridLayout")

        # Configuración de cada θ: (label, axis_min, cart_max)
        axes_config = [
            ("X", 0,  270),
            ("Y", 0,  200),
            ("Z", 0,  520)
        ]

        label_names = ["label_x", "label_y", "label_z"]
        spinbox_names = ["spin_box_1", "spin_box_2",
                         "spin_box_3"]

        for row, (text, s_min, s_max) in enumerate(axes_config):
            # Label
            label = QLabel(text, self.widget)
            label.setMaximumSize(QSize(100, 16777215))
            setattr(self, label_names[row], label)
            self.container.addWidget(label, row, 0)

            # SpinBox
            spin = QSpinBox(self.widget)
            spin.setSizePolicy(QSizePolicy(
                QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed))
            spin.setMaximumSize(QSize(200, 16777215))
            spin.resize(QSize(150, 100))
            spin.setMinimum(s_min)
            spin.setMaximum(s_max)
            spin.setValue(0)
            setattr(self, spinbox_names[row], spin)
            self.container.addWidget(spin, row, 1)

        self.coordinates_button = QPushButton("Enviar")

        self.vertical_layout.addWidget(self.widget)
        self.vertical_layout.addWidget(self.coordinates_button)

        self.kinematics_worker = KinematicsWorker()
        # conectar salida de comandos calculados al estado estático usado por DataFlow
        self.kinematics_worker.commands_ready.connect(self._update_status)
        self.kinematics_worker.start()

    def set_horizontal_layout(self):
        # Guardar referencias (ya las tienes como atributos)
        labels = [self.label_x, self.label_y, self.label_z]
        spins = [self.spin_box_1, self.spin_box_2, self.spin_box_3]

        # Limpiar layout actual
        while self.container.count():
            item = self.container.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

        # Reorganizar: labels en fila 0, spinboxes en fila 1
        for col in range(3):
            self.container.addWidget(labels[col], 0, col)
            self.container.addWidget(spins[col], 1, col)

    def set_vertical_layout(self):
        labels = [self.label_x, self.label_y, self.label_z]
        spins = [self.spin_box_1, self.spin_box_2, self.spin_box_3]

        while self.container.count():
            item = self.container.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

        for row in range(3):
            self.container.addWidget(labels[row], row, 0)
            self.container.addWidget(spins[row], row, 1)

    def setup_connections(self):
        self.coordinates_button.clicked.connect(self.execute_kinematics)

    def _update_status(self, status: list):
        """Slot que recibe una lista de seis valores y actualiza el estado
           estático que consulta DataFlow.__get_kinematics_data().
        """
        KinematicsWidget.kinematics_status = status

    def execute_kinematics(self):
        """Inicia la secuencia de control cinemático realimentado.

        El worker recibirá el objetivo cartesiando y, a partir de la telemetría
        que llega por `PhysicalSignalManager.data_received`, irá calculando paso
        a paso nuevos comandos hasta alcanzar la posición deseada.  Esta función
        únicamente se encarga de fijar el modo y comunicar el objetivo al worker.
        """
        PhysicalSignalManager.get_instance().change_mode_signal.emit(Modes.KINEMATIC)
        SimulationSignalManager.get_instance().change_mode_signal.emit(Modes.KINEMATIC)

        # fijar objetivo en el worker; este comenzará a generar comandos en
        # cuanto reciba la primera actualización de posición
        self.kinematics_worker.set_target(
            self.spin_box_1.value(),
            self.spin_box_2.value(),
            self.spin_box_3.value()
        )

        # También podemos proporcionar una primera estimación rápida
        # para que los sliders muestren una posición razonable antes de recibir
        # telemetría.
        best_q, error = self.kinematics_worker.ci(
            self.spin_box_1.value(), self.spin_box_2.value(), self.spin_box_3.value(), 0)
        q_deg = rad_to_deg(best_q.flatten())
        KinematicsWidget.kinematics_status = [
            np.abs(q_deg[0] + 150.0),
            np.abs(q_deg[1] - 150.0),
            np.abs(q_deg[2] - 150.0),
            150.0,
            np.abs(q_deg[3] + 150.0),
            171]

    @classmethod
    def get_kinematics_state(cls) -> list[int]:
        """Metodo de clase que no requiere instancia para su ejecución.

        Devuelve la lista de seis ángulos (en grados) que actualmente se
        consideran como comandos para el robot.  En modo SLIDERS son los valores
        de los deslizadores; en modo KINEMATIC el trabajador de cinemática realimentada
        actualiza periódicamente este vector en función de la telemetría recibida.
        """
        return cls.kinematics_status
