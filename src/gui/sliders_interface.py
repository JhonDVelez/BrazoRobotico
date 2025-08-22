import os
from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6 import uic


class SlidersWidget(QWidget):
    """ Clase de gui para los controles deslizantes

    Args:
        QWidget (QWidget): Define que la clase es de tipo widget para pyqt
    """

    def __init__(self, parent):
        super().__init__(parent)
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
