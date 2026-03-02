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
        self.kinematics_worker.start()

    def setup_connections(self):
        self.coordinates_button.clicked.connect(self.execute_kinematics)

    def execute_kinematics(self):
        PhysicalSignalManager.get_instance().change_mode_signal.emit(Modes.KINEMATIC)
        SimulationSignalManager.get_instance().change_mode_signal.emit(Modes.KINEMATIC)
        best_q, error = self.kinematics_worker.ci(
            self.spin_box_1.value(), self.spin_box_2.value(), self.spin_box_3.value(), 0)
        q_deg = rad_to_deg(best_q.flatten())
        KinematicsWidget.kinematics_status = [
            q_deg[0] + 150.0,
            -q_deg[1] + 150.0,
            -q_deg[2] + 150.0,
            150.0,
            q_deg[3] + 150.0,
            171]
        print(KinematicsWidget.kinematics_status)

    @classmethod
    def get_kinematics_state(cls) -> list[int]:
        """ Metodo de clase que no requiere instancia de la clase para su ejecucion, 
            encargada de obtener los valores almacenados de los sliders
        """
        return cls.kinematics_status
