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

        # Configuración de cada θ: (label, slider_min, slider_max, slider_val, spin_min, spin_max)
        theta_config = [
            ("θ1", 50,  250),
            ("θ2", 70,  200),
            ("θ3", 50,  200),
            ("θ4", 50,  250),
            ("θ5", 150, 250),
            ("θ6", 38,  171)
        ]

        label_names = ["label", "label_3", "label_4",
                       "label_5", "label_6", "label_7"]
        slider_names = ["slider_1", "slider_2",
                        "slider_3", "slider_4", "slider_5", "slider_6"]
        spinbox_names = ["spin_box_1", "spin_box_2",
                         "spin_box_3", "spin_box_4", "spin_box_5", "spin_box_6"]

        for row, (text, s_min, s_max) in enumerate(theta_config):
            s_val = 150  # Valor inicial o central
            sb_min = s_min - s_val
            sb_max = s_max - s_val
            # Label
            label = QLabel(text, self.widget)
            label.setMaximumSize(QSize(100, 16777215))
            setattr(self, label_names[row], label)
            self.container.addWidget(label, row, 0)

            # Slider
            slider = QSlider(Qt.Orientation.Horizontal, self.widget)
            slider.setMinimum(s_min)
            slider.setMaximum(s_max)
            slider.setValue(s_val)
            setattr(self, slider_names[row], slider)
            self.container.addWidget(slider, row, 1)

            # SpinBox
            spin = QSpinBox(self.widget)
            spin.setSizePolicy(QSizePolicy(
                QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed))
            spin.setMaximumSize(QSize(100, 16777215))
            spin.setMinimum(sb_min)
            spin.setMaximum(sb_max)
            spin.setValue(0)
            setattr(self, spinbox_names[row], spin)
            self.container.addWidget(spin, row, 2)

        self.vertical_layout.addWidget(self.widget)

        # Widget con botones
        self.buttons_widget = QWidget(self)
        self.buttons_widget.setObjectName("buttonsWidget")
        self.buttons_widget.setMaximumSize(QSize(16777215, 100))
        self.button_container = QGridLayout(self.buttons_widget)
        self.button_container.setObjectName("gridLayout")

        button_config = [
            ("pose_1_button", "Pose 1", 0, 0),
            ("pose_2_button", "Pose 2", 0, 1),
            ("pose_3_button", "Pose 3", 1, 0),
            ("pose_4_button", "Pose 4", 1, 1),
        ]

        for attr, text, row, col in button_config:
            btn = QPushButton(text, self.buttons_widget)
            setattr(self, attr, btn)
            self.button_container.addWidget(btn, row, col)

        self.vertical_layout.addWidget(self.buttons_widget)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)
        self.setMinimumSize(120, 160)

    def __setup_connections(self):
        """Configura las conexiones de eventos
        """

        # Se establece una relacion donde el valor del slider es el del spinbox - 150
        # Es decir, el rango del slider es de 0 a 300, mientras el del spinbox es de -150 a 150.
        # Esto hace que se vean en la interfaz valores de -150 a 150 pero al robot se le envian
        # de 0 a 300
        self.slider_1.valueChanged.connect(
            lambda value: self.spin_box_1.setValue(value - 150))
        self.spin_box_1.valueChanged.connect(
            lambda value: self.slider_1.setValue(value + 150))

        self.slider_2.valueChanged.connect(
            lambda value: self.spin_box_2.setValue(value - 150))
        self.spin_box_2.valueChanged.connect(
            lambda value: self.slider_2.setValue(value + 150))

        self.slider_3.valueChanged.connect(
            lambda value: self.spin_box_3.setValue(value - 150))
        self.spin_box_3.valueChanged.connect(
            lambda value: self.slider_3.setValue(value + 150))

        self.slider_4.valueChanged.connect(
            lambda value: self.spin_box_4.setValue(value - 150))
        self.spin_box_4.valueChanged.connect(
            lambda value: self.slider_4.setValue(value + 150))

        self.slider_5.valueChanged.connect(
            lambda value: self.spin_box_5.setValue(value - 150))
        self.spin_box_5.valueChanged.connect(
            lambda value: self.slider_5.setValue(value + 150))

        self.slider_6.valueChanged.connect(
            lambda value: self.spin_box_6.setValue(value - 150))
        self.spin_box_6.valueChanged.connect(
            lambda value: self.slider_6.setValue(value + 150))

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
        self.slider_1.setValue(150)
        self.slider_2.setValue(150)
        self.slider_3.setValue(150)
        self.slider_4.setValue(150)
        self.slider_5.setValue(150)
        self.slider_6.setValue(150)

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
        """ Pose por defecto, se proporcionan los ángulos de los 6 motores, tener en cuenta que para
            el spinbox el rango es de -150 a 150 mientras que para el slider es de 0 a 300
        """
        self.spin_box_1.setValue(-90)
        self.spin_box_2.setValue(-30)
        self.spin_box_3.setValue(-70)
        self.spin_box_4.setValue(0)
        self.spin_box_5.setValue(30)
        self.spin_box_6.setValue(-60)

    def set_pose_2(self):
        """ Pose por defecto, se proporcionan los ángulos de los 6 motores, tener en cuenta que para
            el spinbox el rango es de -150 a 150 mientras que para el slider es de 0 a 300
        """
        self.spin_box_1.setValue(-90)
        self.spin_box_2.setValue(-40)
        self.spin_box_3.setValue(-80)
        self.spin_box_4.setValue(55)
        self.spin_box_5.setValue(30)
        self.spin_box_6.setValue(21)

    def set_pose_3(self):
        """ Pose por defecto, se proporcionan los ángulos de los 6 motores, tener en cuenta que para
            el spinbox el rango es de -150 a 150 mientras que para el slider es de 0 a 300
        """
        self.spin_box_1.setValue(-40)
        self.spin_box_2.setValue(-10)
        self.spin_box_3.setValue(-44)
        self.spin_box_4.setValue(-100)
        self.spin_box_5.setValue(0)
        self.spin_box_6.setValue(21)

    def set_pose_4(self):
        """ Pose por defecto, se proporcionan los ángulos de los 6 motores, tener en cuenta que para
            el spinbox el rango es de -150 a 150 mientras que para el slider es de 0 a 300
        """
        self.spin_box_1.setValue(10)
        self.spin_box_2.setValue(-60)
        self.spin_box_3.setValue(-60)
        self.spin_box_4.setValue(-70)
        self.spin_box_5.setValue(33)
        self.spin_box_6.setValue(70)
