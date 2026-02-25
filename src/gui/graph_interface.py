""" En este modulo se establece la estructura de la sección de la interfaz donde se muestran
    las gráficas tipo osciloscopio.
    Permite visualizar datos en tiempo real tanto del entorno simulado como del robot real.
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
        del usuario como iniciar o detener, asi como actualizar el gráfico con nuevos datos.
        Hace uso de el mixin ImageUtils para el pixmap(imagen) mostrada cuando no se esta en
        ejecución.
    """

    def __init__(self):
        super().__init__()
        # Estado de ejecución del procesamiento de datos
        self.process_running = False
        # Acceso al Singleton del gestor de temas para coherencia visual
        self.theme_manager = ThemeManager.get_instance()

        self.__setup_ui()
        self.__setup_connections()

        # Temporizador de precisión para el seguimiento del tiempo transcurrido en las gráficas
        self.timer = QElapsedTimer()
        self.timer.start()

    def __setup_ui(self):
        """ Inicializa y organiza los componentes visuales de la sección de gráficas.
        """
        # Crear layout principal con márgenes en cero para maximizar el área de dibujo
        graph_layout = QVBoxLayout(self)
        graph_layout.setContentsMargins(0, 0, 0, 0)
        graph_layout.setSpacing(0)

        # --- INSTANCIACIÓN DE GRÁFICOS ---
        # Gráfico para el dominio de SIMULACIÓN (datos internos del modelo matemático)
        self.sim_graph_object = GraphWorker(Domains.SIMULATION, 1000)
        self.sim_graph_widget = self.sim_graph_object.graph_widget
        self.sim_graph_object.start() # Inicia el hilo de actualización de datos

        # Gráfico para el dominio FÍSICO (datos reales provenientes del hardware/robot)
        self.phy_graph_object = GraphWorker(Domains.PHYSICAL, 1000)
        self.phy_graph_widget = self.phy_graph_object.graph_widget
        self.phy_graph_object.start() # Inicia el hilo de actualización de datos

        # --- RECURSOS VISUALES ---
        # Rutas de imágenes placeholder para cuando el osciloscopio está inactivo (modo oscuro/claro)
        self.image_path_r = os.path.join(os.path.dirname(
            __file__), "img", 'graph_r.png')
        self.image_path_b = os.path.join(os.path.dirname(
            __file__), "img", 'graph_b.png')
        self.pixmap = QPixmap(self.image_path_r)

        # --- SELECTORES DE VISTA ---
        # Estilo mínimo para los radio buttons de selección de gráfico
        radio_style = """QRadioButton::indicator {margin-left: 0px;}"""
        
        self.sim_radio_button = QRadioButton("Simulación")
        self.sim_radio_button.setStyleSheet(radio_style)
        self.sim_radio_button.setChecked(True) # Simulación activa por defecto
        
        self.phy_radio_button = QRadioButton("Robot")
        self.phy_radio_button.setStyleSheet(radio_style)

        # Organización horizontal de los selectores (centrados)
        self.selector_layout = QHBoxLayout()
        self.selector_layout.addWidget(self.sim_radio_button)
        self.selector_layout.addWidget(self.phy_radio_button)
        self.selector_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.selector_layout.setSpacing(10)
        graph_layout.addLayout(self.selector_layout)

        # --- LABEL DE IMAGEN (PLACEHOLDER) ---
        # Se muestra cuando las gráficas están detenidas
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.image_label.setMinimumSize(160, 120)
        self.image_label.setContentsMargins(0, 0, 0, 0)

        # Agregar todos los widgets al contenedor principal
        graph_layout.addWidget(self.image_label)
        graph_layout.addWidget(self.sim_graph_widget)
        graph_layout.addWidget(self.phy_graph_widget)

        # --- ESTADO INICIAL ---
        # Por defecto, solo se muestra la imagen placeholder. Las gráficas y radios se ocultan.
        self.phy_graph_widget.hide()
        self.sim_graph_widget.hide()
        self.sim_radio_button.hide()
        self.phy_radio_button.hide()

    def __setup_connections(self):
        """ Establece la lógica de respuesta ante eventos de usuario y sistema.
        """
        # Reaccionar a cambios en el tema (Claro/Oscuro)
        self.theme_manager.theme_changed.connect(self.toggle_theme)
        # Cambiar el gráfico visible cuando el usuario alterna entre Simulación y Robot
        self.sim_radio_button.toggled.connect(self.update_visible_graph)
        self.phy_radio_button.toggled.connect(self.update_visible_graph)

    def start(self):
        """ Método público para iniciar la visualización de datos.
            Oculta la imagen estática y muestra los controles de selección de gráfico.
        """
        self.image_label.hide()
        self.sim_radio_button.show()
        self.phy_radio_button.show()
        self.update_visible_graph()

    def stop(self):
        """ Método público para detener la visualización.
            Limpia la pantalla de gráficas y vuelve a mostrar la imagen de marcador de posición.
        """
        self.phy_graph_widget.hide()
        self.sim_graph_widget.hide()
        self.sim_radio_button.hide()
        self.phy_radio_button.hide()
        self.image_label.show()

    def update_visible_graph(self):
        """ Lógica de conmutación de visibilidad. 
            Asegura que solo se renderice un gráfico a la vez para optimizar recursos.
        """
        if self.sim_radio_button.isChecked():
            self.phy_graph_widget.hide()
            self.sim_graph_widget.show()
        elif self.phy_radio_button.isChecked():
            self.sim_graph_widget.hide()
            self.phy_graph_widget.show()