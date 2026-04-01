""" En este modulo se establece la estructura de la sección de la interfaz donde se muestran
    las gráficas tipo osciloscopio
"""
import os
from PyQt6.QtCore import Qt, QElapsedTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QHBoxLayout, QStackedWidget, QSizePolicy, QRadioButton
from gui.main_window.image_utils_mixin import ImageUtilsMixin
from gui.main_window.main_theme_mixin import ThemeManager
from gui.graph_worker import GraphWorker
from data.control_utils import Domains


class GraphInterface(ImageUtilsMixin):
    """ Clase donde se define las estructura de las gráficas, su comportamiento a las acciones
        del usuario como iniciar o detener, asi como actualizar el gráfico con nuevos datos,
        hace uso de el mixin ImageUtils para el pixmap(imagen) mostrada cuando no se esta en
        ejecución.
    """

    def __init__(self):
        super().__init__()
        self.process_running = False
        self.theme_manager = ThemeManager.get_instance()

        self.__setup_ui()
        self.__setup_connections()

        self.timer = QElapsedTimer()
        self.timer.start()

    def __setup_ui(self):
        # Crear layout principal con márgenes en cero
        graph_layout = QVBoxLayout(self)
        graph_layout.setContentsMargins(0, 0, 0, 0)
        graph_layout.setSpacing(0)

        # Crear objetos de gráficos
        self.angular_graph_object = GraphWorker(1000, 6)
        self.angular_graph_widget = self.angular_graph_object.graph_widget
        self.angular_graph_object.start()

        self.cartesian_graph_object = GraphWorker(1000, 3)
        self.cartesian_graph_widget = self.cartesian_graph_object.graph_widget
        self.cartesian_graph_object.start()

        self.stacked_widget = QStackedWidget()

        # Configurar rutas de imágenes
        self.image_path_r = os.path.join(os.path.dirname(
            __file__), "img", 'graph_r.png')
        self.image_path_b = os.path.join(os.path.dirname(
            __file__), "img", 'graph_b.png')
        self.pixmap = QPixmap(self.image_path_r)

        radio_style = """QRadioButton::indicator {margin-left: 0px;}"""
        self.sim_radio_button = QRadioButton("Angular")
        self.sim_radio_button.setStyleSheet(radio_style)
        self.sim_radio_button.setChecked(True)
        self.phy_radio_button = QRadioButton("Cartesiano")
        self.phy_radio_button.setStyleSheet(radio_style)

        self.selector_layout = QHBoxLayout()
        self.selector_layout.addWidget(self.sim_radio_button)
        self.selector_layout.addWidget(self.phy_radio_button)
        self.selector_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.selector_layout.setSpacing(10)
        graph_layout.addLayout(self.selector_layout)

        # Configurar label de imagen
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.image_label.setMinimumSize(160, 120)
        self.image_label.setContentsMargins(0, 0, 0, 0)

        # Agregar widgets al layout
        graph_layout.addWidget(self.image_label)
        self.stacked_widget.addWidget(self.angular_graph_widget)
        self.stacked_widget.addWidget(self.cartesian_graph_widget)
        graph_layout.addWidget(self.stacked_widget)

        # Ocultar widgets de gráficos inicialmente
        self.angular_graph_widget.hide()
        self.cartesian_graph_widget.hide()
        self.sim_radio_button.hide()
        self.phy_radio_button.hide()
        self.stacked_widget.hide()

    def __setup_connections(self):
        self.theme_manager.theme_changed.connect(self.toggle_theme)
        self.sim_radio_button.toggled.connect(self.update_visible_graph)
        self.phy_radio_button.toggled.connect(self.update_visible_graph)

    def start(self):
        """ Inicia la visualization de las gráficas ocultando la imagen.
        """
        self.image_label.hide()
        self.stacked_widget.show()
        self.angular_graph_widget.show()
        self.sim_radio_button.show()
        self.phy_radio_button.show()
        self.angular_graph_object.start()

    def pause(self):
        """ Pausa la toma de datos
        """
        self.cartesian_graph_object.pause()
        self.angular_graph_object.pause()

    def stop(self):
        """ Oculta todos los widgets y las gráficas y muestra la imagen.
        """
        self.stacked_widget.hide()
        self.angular_graph_widget.hide()
        self.sim_radio_button.hide()
        self.phy_radio_button.hide()
        self.image_label.show()
        self.load_image()

    def update_visible_graph(self):
        """ Actualiza visibilidad según el radio activo
        """
        if self.sim_radio_button.isChecked():
            self.stacked_widget.setCurrentIndex(0)
        elif self.phy_radio_button.isChecked():
            self.stacked_widget.setCurrentIndex(1)
