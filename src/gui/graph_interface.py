""" En este modulo se establece la estructura de la sección de la interfaz donde se muestran
    las gráficas tipo osciloscopio
"""
import os
from PyQt6.QtCore import Qt, QElapsedTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QHBoxLayout, QSizePolicy, QRadioButton
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
        self.graph_object = GraphWorker(1000)
        self.sim_graph_widget = self.graph_object.graph_widget
        self.graph_object.start()

        # Configurar rutas de imágenes
        self.image_path_r = os.path.join(os.path.dirname(
            __file__), "img", 'graph_r.png')
        self.image_path_b = os.path.join(os.path.dirname(
            __file__), "img", 'graph_b.png')
        self.pixmap = QPixmap(self.image_path_r)

        self.selector_layout = QHBoxLayout()
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
        graph_layout.addWidget(self.sim_graph_widget)

        # Ocultar widgets de gráficos inicialmente
        self.sim_graph_widget.hide()

    def __setup_connections(self):
        self.theme_manager.theme_changed.connect(self.toggle_theme)

    def start(self):
        """ Inicia la visualization de las gráficas ocultando la imagen.
        """
        self.image_label.hide()
        self.sim_graph_widget.show()
        self.graph_object.start()

    def pause(self):
        """ Pausa la toma de datos
        """
        self.graph_object.pause()

    def stop(self):
        """ Oculta todos los widgets y las gráficas y muestra la imagen.
        """
        self.graph_object.stop()
        self.sim_graph_widget.hide()
        self.image_label.show()
        self.load_image()
