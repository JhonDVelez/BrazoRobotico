from PyQt6.QtWidgets import QWidget, QSizePolicy, QPushButton, QGridLayout, QLabel, QSlider
from PyQt6.QtWidgets import QSpinBox, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from data import Modes, PhysicalSignalManager, SimulationSignalManager


class SlidersWidget(QWidget):
    """ Clase de gui para los controles deslizantes

    Args:
        QWidget (QWidget): Define que la clase es de tipo widget para pyqt
    """
    mode_changed = pyqtSignal(object)
    sliders_status = [150, 150, 150, 150, 150, 150]
    instance = None

    def __init__(self, parent, kinematics_widget=None):
        super().__init__(parent)
        SlidersWidget.instance = self
        self.parent = parent
        self.kinematics_widget = kinematics_widget
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

        # Holder que contendrá alternativamente los sliders o el panel cartesiano
        self.controls_holder = QWidget(self)
        self.controls_holder_layout = QVBoxLayout(self.controls_holder)
        self.controls_holder_layout.setContentsMargins(0, 0, 0, 0)

        # Widget con sliders y spinboxes (hijo del holder)
        self.widget = QWidget(self.controls_holder)
        self.widget.setObjectName("controls_holder")
        self.container = QGridLayout(self.widget)
        self.container.setObjectName("gridLayout_3")

        # Configuración de cada θ: (label, slider_min, slider_max)
        # Los valores de slider están desplazados por 150 respecto al spinbox
        # slider = spin + 150
        theta_config = [
            ("θ1", 50, 250),   # spin: -100 .. 100
            ("θ2", 60, 240),   # spin: -90  .. 90
            ("θ3", 30, 270),   # spin: -120 .. 120
            ("θ4", 50, 250),   # spin: -100 .. 100
            ("θ5", 39, 270),   # spin: -111 .. 120
            ("θ6", 38, 171)    # mantener igual
        ]

        label_names = ["label", "label_3", "label_4",
                       "label_5", "label_6", "label_7"]
        slider_names = ["slider_1", "slider_2",
                        "slider_3", "slider_4", "slider_5", "slider_6"]
        spinbox_names = ["spin_box_1", "spin_box_2",
                         "spin_box_3", "spin_box_4", "spin_box_5", "spin_box_6"]

        for i, (text, s_min, s_max) in enumerate(theta_config):
            s_val = 150
            sb_min = s_min - s_val
            sb_max = s_max - s_val

            # Posición en cuadrícula 3 columnas x 2 filas
            grid_row = i // 3
            grid_col = i % 3

            # Sub-widget horizontal para cada grupo
            group_widget = QWidget(self.widget)
            group_layout = QHBoxLayout(group_widget)
            group_layout.setContentsMargins(0, 0, 0, 0)

            # Label
            label = QLabel(text, group_widget)
            label.setMaximumSize(QSize(30, 30))
            setattr(self, label_names[i], label)
            group_layout.addWidget(label)

            # Slider
            slider = QSlider(Qt.Orientation.Horizontal, group_widget)
            slider.setMinimum(s_min)
            slider.setMaximum(s_max)
            slider.setValue(s_val)
            slider.setMaximumSize(QSize(400, 30))
            setattr(self, slider_names[i], slider)
            group_layout.addWidget(slider)

            # SpinBox
            spin = QSpinBox(group_widget)
            spin.setSizePolicy(QSizePolicy(
                QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed))
            spin.setMaximumSize(QSize(60, 30))
            spin.setMinimum(sb_min)
            spin.setMaximum(sb_max)
            spin.setValue(0)
            setattr(self, spinbox_names[i], spin)
            group_layout.addWidget(spin)

            self.container.addWidget(group_widget, grid_row, grid_col)

        # Añadir ambos al holder (se mostrará solo uno a la vez)
        self.controls_holder_layout.addWidget(self.widget)
        if self.kinematics_widget is not None:
            self.controls_holder_layout.addWidget(self.kinematics_widget)
            self.kinematics_widget.hide()

        self.vertical_layout.addWidget(self.controls_holder)

        # Widget con botones
        self.buttons_widget = QWidget()
        self.buttons_widget.setObjectName("buttonsWidget")
        self.buttons_widget.setMaximumSize(QSize(16777215, 100))
        self.button_container = QGridLayout(self.buttons_widget)
        self.button_container.setObjectName("gridLayout")

        # self.vertical_layout.addWidget(self.buttons_widget) # Agrega o quita los botones de pose
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

        # Conectar recepción de cambio de modo desde los SignalManagers para ajustar la UI
        try:
            PhysicalSignalManager.get_instance().change_mode_signal.connect(self._on_mode_changed)
        except Exception:
            pass
        try:
            SimulationSignalManager.get_instance(
            ).change_mode_signal.connect(self._on_mode_changed)
        except Exception:
            pass

    def update_class_status(self):
        """ Actualiza los valores almacenados de los slider/spinBox (estan conectados)
        """
        self.mode_changed.emit(Modes.SLIDERS)
        SlidersWidget.sliders_status = [
            self.slider_1.value(),
            -self.spin_box_2.value()+150,
            -self.spin_box_3.value()+150,
            self.slider_4.value(),
            self.slider_5.value(),
            self.slider_6.value(),
        ]

    def _on_mode_changed(self, mode):
        """Slot para cambios de modo. No oculta widgets ya que están en MainInitMixin."""
        pass

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

    def set_values(self, values: list[int]):
        """Actualizar los sliders/spinboxes desde una lista de 6 valores.

        Se espera que `values` contenga los valores en el mismo formato que usan los
        `spin_box` (ej. -150..150). Este método actualiza los `spin_box` para que
        las conexiones existentes sincronicen los `slider` automáticamente.
        """
        if values is None:
            return
        try:
            # Asegurar longitud mínima
            vals = list(values)
            if len(vals) < 6:
                return
            self.slider_1.setValue(int(vals[0]))
            self.spin_box_2.setValue(int(-vals[1]+150))
            self.spin_box_3.setValue(int(-vals[2]+150))
            self.slider_4.setValue(int(vals[3]))
            self.slider_5.setValue(int(vals[4]))
            self.slider_6.setValue(int(vals[5]))
        except Exception:
            pass
