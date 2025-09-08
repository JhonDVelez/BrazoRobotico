import os
from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6 import uic


class SlidersWidget(QWidget):
    """ Clase de gui para los controles deslizantes

    Args:
        QWidget (QWidget): Define que la clase es de tipo widget para pyqt
    """
    sliders_status = [0, 0, 0, 0, 0, 0]
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
        self.ui = uic.loadUi(os.path.join(
            os.path.dirname(__file__), 'sliders_interface.ui'), self)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)
        self.setMinimumSize(120, 160)

    def __setup_connections(self):
        """Configura las conexiones de eventos
        """
        self.slider1.valueChanged.connect(self.spinBox1.setValue)
        self.spinBox1.valueChanged.connect(self.slider1.setValue)

        self.slider2.valueChanged.connect(self.spinBox2.setValue)
        self.spinBox2.valueChanged.connect(self.slider2.setValue)

        self.slider3.valueChanged.connect(self.spinBox3.setValue)
        self.spinBox3.valueChanged.connect(self.slider3.setValue)

        self.slider4.valueChanged.connect(self.spinBox4.setValue)
        self.spinBox4.valueChanged.connect(self.slider4.setValue)

        self.slider5.valueChanged.connect(self.spinBox5.setValue)
        self.spinBox5.valueChanged.connect(self.slider5.setValue)

        self.slider6.valueChanged.connect(self.spinBox6.setValue)
        self.spinBox6.valueChanged.connect(self.slider6.setValue)

        self.slider1.valueChanged.connect(self.update_class_status)
        self.spinBox1.valueChanged.connect(self.update_class_status)

        self.slider2.valueChanged.connect(self.update_class_status)
        self.spinBox2.valueChanged.connect(self.update_class_status)

        self.slider3.valueChanged.connect(self.update_class_status)
        self.spinBox3.valueChanged.connect(self.update_class_status)

        self.slider4.valueChanged.connect(self.update_class_status)
        self.spinBox4.valueChanged.connect(self.update_class_status)

        self.slider5.valueChanged.connect(self.update_class_status)
        self.spinBox5.valueChanged.connect(self.update_class_status)

        self.slider6.valueChanged.connect(self.update_class_status)
        self.spinBox6.valueChanged.connect(self.update_class_status)

        self.pose1Button.clicked.connect(self.set_pose_1)
        self.pose2Button.clicked.connect(self.set_pose_2)
        self.pose3Button.clicked.connect(self.set_pose_3)
        self.pose4Button.clicked.connect(self.set_pose_4)

    def update_class_status(self):
        """ Actualiza los valores almacenados de los slider/spinBox (estan conectados)
        """
        SlidersWidget.sliders_status = [
            self.slider1.value(),
            self.slider2.value(),
            self.slider3.value(),
            self.slider4.value(),
            self.slider5.value(),
            self.slider6.value(),
        ]

    def reset_values(self):
        """ Regresa a su estado original los valores de los slider/spinBox (estan conectados)
        """
        self.spinBox1.setValue(0)
        self.spinBox2.setValue(0)
        self.spinBox3.setValue(0)
        self.spinBox4.setValue(0)
        self.spinBox5.setValue(0)
        self.spinBox6.setValue(0)

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
        self.spinBox1.setValue(-70)
        self.spinBox2.setValue(80)
        self.spinBox3.setValue(40)
        self.spinBox4.setValue(-120)
        self.spinBox5.setValue(-60)
        self.spinBox6.setValue(50)

    def set_pose_2(self):
        self.spinBox1.setValue(-70)
        self.spinBox2.setValue(60)
        self.spinBox3.setValue(-10)
        self.spinBox4.setValue(0)
        self.spinBox5.setValue(-20)
        self.spinBox6.setValue(20)

    def set_pose_3(self):
        self.spinBox1.setValue(20)
        self.spinBox2.setValue(60)
        self.spinBox3.setValue(10)
        self.spinBox4.setValue(0)
        self.spinBox5.setValue(50)
        self.spinBox6.setValue(20)

    def set_pose_4(self):
        self.spinBox1.setValue(20)
        self.spinBox2.setValue(50)
        self.spinBox3.setValue(40)
        self.spinBox4.setValue(0)
        self.spinBox5.setValue(80)
        self.spinBox6.setValue(60)
