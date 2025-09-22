import os
from PyQt6.QtWidgets import QWidget, QSizePolicy, QPushButton, QGridLayout, QLabel, QSlider
from PyQt6.QtWidgets import QSpinBox, QVBoxLayout
from PyQt6.QtCore import Qt, QSize


class SlidersWidget(QWidget):
    """ Clase de gui para los controles deslizantes

    Args:
        QWidget (QWidget): Define que la clase es de tipo widget para pyqt
    """
    sliders_status = [150, 150, 150, 150, 150, 150]
    instance = None

    def __init__(self, parent):
        super().__init__(parent)
        SlidersWidget.instance = self
        self.parent = parent
        self.__setup_ui()
        self.__setup_connections()

    def __setup_ui(self):
        """ Configura la interfaz de usuario del widget de video
        """
        self.setObjectName("Form")
        self.resize(381, 691)
        self.setWindowTitle("Form")

        # Layout principal
        self.vertical_layout = QVBoxLayout(self)
        self.vertical_layout.setObjectName("verticalLayout")

        # Widget con sliders y spinboxes
        self.widget = QWidget(self)
        self.widget.setObjectName("widget")
        self.container = QGridLayout(self.widget)
        self.container.setObjectName("gridLayout_3")

        # θ1
        self.label = QLabel("θ1", self.widget)
        self.label.setMaximumSize(QSize(100, 16777215))
        self.container.addWidget(self.label, 0, 0)

        self.slider_1 = QSlider(Qt.Orientation.Horizontal, self.widget)
        self.slider_1.setMinimum(50)
        self.slider_1.setMaximum(250)
        self.slider_1.setValue(150)
        self.container.addWidget(self.slider_1, 0, 1)

        self.spin_box_1 = QSpinBox(self.widget)
        self.spin_box_1.setSizePolicy(QSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed))
        self.spin_box_1.setMaximumSize(QSize(100, 16777215))
        self.spin_box_1.setMinimum(50)
        self.spin_box_1.setMaximum(250)
        self.spin_box_1.setValue(150)
        self.container.addWidget(self.spin_box_1, 0, 2)

        # θ2
        self.label_3 = QLabel("θ2", self.widget)
        self.container.addWidget(self.label_3, 1, 0)

        self.slider_2 = QSlider(Qt.Orientation.Horizontal, self.widget)
        self.slider_2.setMinimum(70)
        self.slider_2.setMaximum(200)
        self.slider_2.setValue(150)
        self.container.addWidget(self.slider_2, 1, 1)

        self.spin_box_2 = QSpinBox(self.widget)
        self.spin_box_2.setSizePolicy(QSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed))
        self.spin_box_2.setMaximumSize(QSize(100, 16777215))
        self.spin_box_2.setMinimum(70)
        self.spin_box_2.setMaximum(200)
        self.spin_box_2.setValue(150)
        self.container.addWidget(self.spin_box_2, 1, 2)

        # θ3
        self.label_4 = QLabel("θ3", self.widget)
        self.container.addWidget(self.label_4, 2, 0)

        self.slider_3 = QSlider(Qt.Orientation.Horizontal, self.widget)
        self.slider_3.setMinimum(50)
        self.slider_3.setMaximum(200)
        self.slider_3.setValue(150)
        self.container.addWidget(self.slider_3, 2, 1)

        self.spin_box_3 = QSpinBox(self.widget)
        self.spin_box_3.setSizePolicy(QSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed))
        self.spin_box_3.setMaximumSize(QSize(100, 16777215))
        self.spin_box_3.setMinimum(50)
        self.spin_box_3.setMaximum(250)
        self.spin_box_3.setValue(150)
        self.container.addWidget(self.spin_box_3, 2, 2)

        # θ4
        self.label_5 = QLabel("θ4", self.widget)
        self.container.addWidget(self.label_5, 3, 0)

        self.slider_4 = QSlider(Qt.Orientation.Horizontal, self.widget)
        self.slider_4.setMinimum(50)
        self.slider_4.setMaximum(250)
        self.slider_4.setValue(150)
        self.container.addWidget(self.slider_4, 3, 1)

        self.spin_box_4 = QSpinBox(self.widget)
        self.spin_box_4.setSizePolicy(QSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed))
        self.spin_box_4.setMaximumSize(QSize(100, 16777215))
        self.spin_box_4.setMinimum(50)
        self.spin_box_4.setMaximum(250)
        self.spin_box_4.setValue(150)
        self.container.addWidget(self.spin_box_4, 3, 2)

        # θ5
        self.label_6 = QLabel("θ5", self.widget)
        self.container.addWidget(self.label_6, 4, 0)

        self.slider_5 = QSlider(Qt.Orientation.Horizontal, self.widget)
        self.slider_5.setMinimum(150)
        self.slider_5.setMaximum(250)
        self.slider_5.setValue(150)
        self.container.addWidget(self.slider_5, 4, 1)

        self.spin_box_5 = QSpinBox(self.widget)
        self.spin_box_5.setSizePolicy(QSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed))
        self.spin_box_5.setMaximumSize(QSize(100, 16777215))
        self.spin_box_5.setMinimum(150)
        self.spin_box_5.setMaximum(250)
        self.spin_box_5.setValue(150)
        self.container.addWidget(self.spin_box_5, 4, 2)

        # θ6
        self.label_7 = QLabel("θ6", self.widget)
        self.container.addWidget(self.label_7, 5, 0)

        self.slider_6 = QSlider(Qt.Orientation.Horizontal, self.widget)
        self.slider_6.setMinimum(38)
        self.slider_6.setMaximum(171)
        self.slider_6.setValue(150)
        self.container.addWidget(self.slider_6, 5, 1)

        self.spin_box_6 = QSpinBox(self.widget)
        self.spin_box_6.setSizePolicy(QSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed))
        self.spin_box_6.setMaximumSize(QSize(100, 16777215))
        self.spin_box_6.setMinimum(38)
        self.spin_box_6.setMaximum(171)
        self.spin_box_6.setValue(150)
        self.container.addWidget(self.spin_box_6, 5, 2)

        # Añadir el primer widget al layout principal
        self.vertical_layout.addWidget(self.widget)

        # Widget con botones
        self.buttons_widget = QWidget(self)
        self.buttons_widget.setObjectName("buttonsWidget")
        self.buttons_widget.setMaximumSize(QSize(16777215, 100))
        self.button_container = QGridLayout(self.buttons_widget)
        self.button_container.setObjectName("gridLayout")

        self.pose_1_button = QPushButton("Pose 1", self.buttons_widget)
        self.button_container.addWidget(self.pose_1_button, 0, 0)

        self.pose_2_button = QPushButton("Pose 2", self.buttons_widget)
        self.button_container.addWidget(self.pose_2_button, 0, 1)

        self.pose_3_button = QPushButton("Pose 3", self.buttons_widget)
        self.button_container.addWidget(self.pose_3_button, 1, 0)

        self.pose_4_button = QPushButton("Pose 4", self.buttons_widget)
        self.button_container.addWidget(self.pose_4_button, 1, 1)

        # Añadir el widget de botones al layout principal
        self.vertical_layout.addWidget(self.buttons_widget)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)
        self.setMinimumSize(120, 160)

    def __setup_connections(self):
        """Configura las conexiones de eventos
        """
        self.slider_1.valueChanged.connect(self.spin_box_1.setValue)
        self.spin_box_1.valueChanged.connect(self.slider_1.setValue)

        self.slider_2.valueChanged.connect(self.spin_box_2.setValue)
        self.spin_box_2.valueChanged.connect(self.slider_2.setValue)

        self.slider_3.valueChanged.connect(self.spin_box_3.setValue)
        self.spin_box_3.valueChanged.connect(self.slider_3.setValue)

        self.slider_4.valueChanged.connect(self.spin_box_4.setValue)
        self.spin_box_4.valueChanged.connect(self.slider_4.setValue)

        self.slider_5.valueChanged.connect(self.spin_box_5.setValue)
        self.spin_box_5.valueChanged.connect(self.slider_5.setValue)

        self.slider_6.valueChanged.connect(self.spin_box_6.setValue)
        self.spin_box_6.valueChanged.connect(self.slider_6.setValue)

        self.slider_1.valueChanged.connect(self.update_class_status)
        self.spin_box_1.valueChanged.connect(self.update_class_status)

        self.slider_2.valueChanged.connect(self.update_class_status)
        self.spin_box_2.valueChanged.connect(self.update_class_status)

        self.slider_3.valueChanged.connect(self.update_class_status)
        self.spin_box_3.valueChanged.connect(self.update_class_status)

        self.slider_4.valueChanged.connect(self.update_class_status)
        self.spin_box_4.valueChanged.connect(self.update_class_status)

        self.slider_5.valueChanged.connect(self.update_class_status)
        self.spin_box_5.valueChanged.connect(self.update_class_status)

        self.slider_6.valueChanged.connect(self.update_class_status)
        self.spin_box_6.valueChanged.connect(self.update_class_status)

        self.pose_1_button.clicked.connect(self.set_pose_1)
        self.pose_2_button.clicked.connect(self.set_pose_2)
        self.pose_3_button.clicked.connect(self.set_pose_3)
        self.pose_4_button.clicked.connect(self.set_pose_4)

    def update_class_status(self):
        """ Actualiza los valores almacenados de los slider/spinBox (estan conectados)
        """
        SlidersWidget.sliders_status = [
            self.slider_1.value(),
            self.slider_2.value(),
            self.slider_3.value(),
            self.slider_4.value(),
            self.slider_5.value(),
            self.slider_6.value(),
        ]

    def reset_values(self):
        """ Regresa a su estado original los valores de los slider/spinBox (estan conectados)
        """
        self.spin_box_1.setValue(150)
        self.spin_box_2.setValue(150)
        self.spin_box_3.setValue(150)
        self.spin_box_4.setValue(150)
        self.spin_box_5.setValue(150)
        self.spin_box_6.setValue(150)

    @classmethod
    def restart_sliders(cls):
        """ Metodo de clase que no requiere instancia de la clase para su ejecucion, 
            encargada de reiniciar los sliders a su posicion inicial
        """
        if cls.instance is not None:
            cls.instance.reset_values()

    @classmethod
    def get_sliders_state(cls) -> list[int]:
        """ Metodo de clase que no requiere instancia de la clase para su ejecucion, 
            encargada de obtener los valores almacenados de los sliders
        """
        return cls.sliders_status

    def set_pose_1(self):
        self.spin_box_1.setValue(60)
        self.spin_box_2.setValue(80)
        self.spin_box_3.setValue(40)
        self.spin_box_4.setValue(120)
        self.spin_box_5.setValue(170)
        self.spin_box_6.setValue(50)

    def set_pose_2(self):
        self.spin_box_1.setValue(100)
        self.spin_box_2.setValue(90)
        self.spin_box_3.setValue(160)
        self.spin_box_4.setValue(150)
        self.spin_box_5.setValue(160)
        self.spin_box_6.setValue(38)

    def set_pose_3(self):
        self.spin_box_1.setValue(60)
        self.spin_box_2.setValue(80)
        self.spin_box_3.setValue(40)
        self.spin_box_4.setValue(120)
        self.spin_box_5.setValue(170)
        self.spin_box_6.setValue(50)

    def set_pose_4(self):
        self.spin_box_1.setValue(60)
        self.spin_box_2.setValue(80)
        self.spin_box_3.setValue(40)
        self.spin_box_4.setValue(120)
        self.spin_box_5.setValue(170)
        self.spin_box_6.setValue(50)
