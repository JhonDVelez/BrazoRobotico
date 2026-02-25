from PyQt6.QtWidgets import QWidget, QSizePolicy, QPushButton, QGridLayout, QLabel, QSlider
from PyQt6.QtWidgets import QSpinBox, QVBoxLayout
from PyQt6.QtCore import Qt, QSize


class SlidersWidget(QWidget):
    """ Clase de gui para los controles deslizantes (Sliders) y cajas numéricas (SpinBoxes)
        que permiten el control articular manual del robot.

    Args:
        QWidget (QWidget): Define que la clase es de tipo widget para pyqt.
    """
    # Variable de clase para almacenar la posición de los 6 motores (estado global)
    sliders_status = [150, 150, 150, 150, 150, 150]
    # Referencia a la instancia activa para permitir acceso desde métodos de clase
    instance = None

    def __init__(self, parent):
        super().__init__(parent)
        SlidersWidget.instance = self
        self.parent = parent
        self.__setup_ui()
        self.__setup_connections()

    def __setup_ui(self):
        """ Configura la interfaz de usuario, organizando los controles en una cuadrícula.
        """
        self.setObjectName("Form")
        self.resize(381, 691)
        self.setWindowTitle("Form")

        # Layout principal vertical que contiene el bloque de sliders y el bloque de botones
        self.vertical_layout = QVBoxLayout(self)
        self.vertical_layout.setObjectName("verticalLayout")

        # --- SECCIÓN DE CONTROLES ARTICULARES ---
        self.widget = QWidget(self)
        self.widget.setObjectName("widget")
        self.container = QGridLayout(self.widget) # Rejilla para alinear Etiqueta | Slider | SpinBox
        self.container.setObjectName("gridLayout_3")

        # Configuración de los 6 motores (θ1 a θ6)
        # Cada motor tiene un Slider (para movimiento rápido) y un SpinBox (para precisión)
        
        # θ1: Base del robot
        self.label = QLabel("θ1", self.widget)
        self.label.setMaximumSize(QSize(100, 16777215))
        self.container.addWidget(self.label, 0, 0)

        self.slider_1 = QSlider(Qt.Orientation.Horizontal, self.widget)
        self.slider_1.setMinimum(50)
        self.slider_1.setMaximum(250)
        self.slider_1.setValue(150) # Punto central/Home
        self.container.addWidget(self.slider_1, 0, 1)

        self.spin_box_1 = QSpinBox(self.widget)
        self.spin_box_1.setSizePolicy(QSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed))
        self.spin_box_1.setMaximumSize(QSize(100, 16777215))
        self.spin_box_1.setMinimum(-100)
        self.spin_box_1.setMaximum(100)
        self.spin_box_1.setValue(0)
        self.container.addWidget(self.spin_box_1, 0, 2)

        # θ2: Hombro
        self.label_3 = QLabel("θ2", self.widget)
        self.container.addWidget(self.label_3, 1, 0)

        self.slider_2 = QSlider(Qt.Orientation.Horizontal, self.widget)
        self.slider_2.setMinimum(70)
        self.slider_2.setMaximum(200)
        self.slider_2.setValue(150)
        self.container.addWidget(self.slider_2, 1, 1)

        self.spin_box_2 = QSpinBox(self.widget)
        self.spin_box_2.setMinimum(-80)
        self.spin_box_2.setMaximum(50)
        self.spin_box_2.setValue(0)
        self.container.addWidget(self.spin_box_2, 1, 2)

        # θ3: Codo
        self.label_4 = QLabel("θ3", self.widget)
        self.container.addWidget(self.label_4, 2, 0)

        self.slider_3 = QSlider(Qt.Orientation.Horizontal, self.widget)
        self.slider_3.setMinimum(50)
        self.slider_3.setMaximum(200)
        self.slider_3.setValue(150)
        self.container.addWidget(self.slider_3, 2, 1)

        self.spin_box_3 = QSpinBox(self.widget)
        self.spin_box_3.setMinimum(-100)
        self.spin_box_3.setMaximum(100)
        self.spin_box_3.setValue(0)
        self.container.addWidget(self.spin_box_3, 2, 2)

        # θ4: Muñeca (Giro)
        self.label_5 = QLabel("θ4", self.widget)
        self.container.addWidget(self.label_5, 3, 0)

        self.slider_4 = QSlider(Qt.Orientation.Horizontal, self.widget)
        self.slider_4.setMinimum(50)
        self.slider_4.setMaximum(250)
        self.slider_4.setValue(150)
        self.container.addWidget(self.slider_4, 3, 1)

        self.spin_box_4 = QSpinBox(self.widget)
        self.spin_box_4.setMinimum(-100)
        self.spin_box_4.setMaximum(100)
        self.spin_box_4.setValue(0)
        self.container.addWidget(self.spin_box_4, 3, 2)

        # θ5: Muñeca (Elevación)
        self.label_6 = QLabel("θ5", self.widget)
        self.container.addWidget(self.label_6, 4, 0)

        self.slider_5 = QSlider(Qt.Orientation.Horizontal, self.widget)
        self.slider_5.setMinimum(150)
        self.slider_5.setMaximum(250)
        self.slider_5.setValue(150)
        self.container.addWidget(self.slider_5, 4, 1)

        self.spin_box_5 = QSpinBox(self.widget)
        self.spin_box_5.setMinimum(0)
        self.spin_box_5.setMaximum(50)
        self.spin_box_5.setValue(0)
        self.container.addWidget(self.spin_box_5, 4, 2)

        # θ6: Gripper / Pinza
        self.label_7 = QLabel("θ6", self.widget)
        self.container.addWidget(self.label_7, 5, 0)

        self.slider_6 = QSlider(Qt.Orientation.Horizontal, self.widget)
        self.slider_6.setMinimum(38)
        self.slider_6.setMaximum(171)
        self.slider_6.setValue(150)
        self.container.addWidget(self.slider_6, 5, 1)

        self.spin_box_6 = QSpinBox(self.widget)
        self.spin_box_6.setMinimum(-112)
        self.spin_box_6.setMaximum(21)
        self.spin_box_6.setValue(0)
        self.container.addWidget(self.spin_box_6, 5, 2)

        self.vertical_layout.addWidget(self.widget)

        # --- SECCIÓN DE BOTONES DE POSES PREDEFINIDAS ---
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

        self.vertical_layout.addWidget(self.buttons_widget)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)
        self.setMinimumSize(120, 160)

    def __setup_connections(self):
        """ Configura la lógica bidireccional entre Sliders y SpinBoxes.
            Asegura que al mover uno, el otro se actualice proporcionalmente.
        """

        # Lógica de mapeo: 
        # El Slider opera en un rango absoluto (ej. 0 a 300) para el control del robot.
        # El SpinBox muestra un valor relativo (offset de -150) para la lectura humana.
        
        # Conexiones para Motor 1
        self.slider_1.valueChanged.connect(
            lambda value: self.spin_box_1.setValue(value - 150))
        self.spin_box_1.valueChanged.connect(
            lambda value: self.slider_1.setValue(value + 150))

        # Conexiones para Motor 2
        self.slider_2.valueChanged.connect(
            lambda value: self.spin_box_2.setValue(value - 150))
        self.spin_box_2.valueChanged.connect(
            lambda value: self.slider_2.setValue(value + 150))

        # Conexiones para Motor 3
        self.slider_3.valueChanged.connect(
            lambda value: self.spin_box_3.setValue(value - 150))
        self.spin_box_3.valueChanged.connect(
            lambda value: self.slider_3.setValue(value + 150))

        # Conexiones para Motor 4
        self.slider_4.valueChanged.connect(
            lambda value: self.spin_box_4.setValue(value - 150))
        self.spin_box_4.valueChanged.connect(
            lambda value: self.slider_4.setValue(value + 150))

        # Conexiones para Motor 5
        self.slider_5.valueChanged.connect(
            lambda value: self.spin_box_5.setValue(value - 150))
        self.spin_box_5.valueChanged.connect(
            lambda value: self.slider_5.setValue(value + 150))

        # Conexiones para Motor 6
        self.slider_6.valueChanged.connect(
            lambda value: self.spin_box_6.setValue(value - 150))
        self.spin_box_6.valueChanged.connect(
            lambda value: self.slider_6.setValue(value + 150))

        # Registro de cualquier cambio en la variable de clase 'sliders_status'
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

        # Conexión de botones de poses predefinidas
        self.pose_1_button.clicked.connect(self.set_pose_1)
        self.pose_2_button.clicked.connect(self.set_pose_2)
        self.pose_3_button.clicked.connect(self.set_pose_3)
        self.pose_4_button.clicked.connect(self.set_pose_4)

    def update_class_status(self):
        """ Sincroniza los valores actuales de la UI con la variable de estado global.
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
        """ Restablece todos los controles a la posición central (150).
        """
        self.slider_1.setValue(150)
        self.slider_2.setValue(150)
        self.slider_3.setValue(150)
        self.slider_4.setValue(150)
        self.slider_5.setValue(150)
        self.slider_6.setValue(150)

    @classmethod
    def restart_sliders(cls):
        """ Método estático para reiniciar los sliders desde cualquier parte del programa
            sin necesitar una referencia directa a la instancia.
        """
        if cls.instance is not None:
            cls.instance.reset_values()

    @classmethod
    def get_sliders_state(cls) -> list[int]:
        """ Recupera el estado actual de los 6 motores. Usado por el flujo de datos.
        """
        return cls.sliders_status

    # --- DEFINICIÓN DE POSES PRECONFIGURADAS ---
    # Nota: Se asignan valores al SpinBox, lo que automáticamente actualiza el Slider
    # debido a las conexiones bidireccionales definidas en __setup_connections.

    def set_pose_1(self):
        """ Configura el robot en la Pose 1 (Posición de descanso/orientación inicial).
        """
        self.spin_box_1.setValue(-90)
        self.spin_box_2.setValue(-30)
        self.spin_box_3.setValue(-70)
        self.spin_box_4.setValue(0)
        self.spin_box_5.setValue(30)
        self.spin_box_6.setValue(-60)

    def set_pose_2(self):
        """ Configura el robot en la Pose 2 (Extensión frontal).
        """
        self.spin_box_1.setValue(-90)
        self.spin_box_2.setValue(-40)
        self.spin_box_3.setValue(-80)
        self.spin_box_4.setValue(55)
        self.spin_box_5.setValue(30)
        self.spin_box_6.setValue(21)

    def set_pose_3(self):
        """ Configura el robot en la Pose 3 (Recogida lateral).
        """
        self.spin_box_1.setValue(-40)
        self.spin_box_2.setValue(-10)
        self.spin_box_3.setValue(-44)
        self.spin_box_4.setValue(-100)
        self.spin_box_5.setValue(0)
        self.spin_box_6.setValue(21)

    def set_pose_4(self):
        """ Configura el robot en la Pose 4 (Posición de trabajo elevada).
        """
        self.spin_box_1.setValue(10)
        self.spin_box_2.setValue(-60)
        self.spin_box_3.setValue(-60)
        self.spin_box_4.setValue(-70)
        self.spin_box_5.setValue(33)
        self.spin_box_6.setValue(70)