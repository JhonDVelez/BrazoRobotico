import os
import pyqtgraph as pg
from PyQt6.QtCore import Qt, QElapsedTimer, QThread, QTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QHBoxLayout, QSizePolicy, QRadioButton
from gui.main_window.image_utils_mixin import ImageUtilsMixin
from gui.main_window.main_theme_mixin import ThemeManager
from gui.graph_worker import upgradableGraph
from data.control_utils import SimulationSignalManager, PhysicalSignalManager, domains


class graphInterface(ImageUtilsMixin):
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
        self.sim_graph_object = GraphWidget(domains.SIMULATION, 1000)
        self.sim_graph_widget = self.sim_graph_object.graph_widget
        self.sim_graph_object.start()

        self.phy_graph_object = GraphWidget(domains.PHYSICAL, 1000)
        self.phy_graph_widget = self.phy_graph_object.graph_widget
        self.phy_graph_object.start()

        # Configurar rutas de imágenes
        self.image_path_r = os.path.join(os.path.dirname(
            __file__), "img", 'graph_r.png')
        self.image_path_b = os.path.join(os.path.dirname(
            __file__), "img", 'graph_b.png')
        self.pixmap = QPixmap(self.image_path_r)

        # Configura el radio button para el cambio de graficos visible
        radio_style = """QRadioButton::indicator {margin-left: 0px;}"""
        self.sim_radio_button = QRadioButton("Simulación")
        self.sim_radio_button.setStyleSheet(radio_style)
        self.sim_radio_button.setChecked(True)
        self.phy_radio_button = QRadioButton("Robot")
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
        graph_layout.addWidget(self.sim_graph_widget)
        graph_layout.addWidget(self.phy_graph_widget)

        # Ocultar widgets de gráficos inicialmente
        self.phy_graph_widget.hide()
        self.sim_graph_widget.hide()
        self.sim_radio_button.hide()
        self.phy_radio_button.hide()

    def __setup_connections(self):
        self.theme_manager.theme_changed.connect(self.toggle_theme)
        self.sim_radio_button.toggled.connect(self.update_visible_graph)
        self.phy_radio_button.toggled.connect(self.update_visible_graph)

    def start(self):
        self.image_label.hide()
        self.sim_radio_button.show()
        self.phy_radio_button.show()
        self.update_visible_graph()

    def stop(self):
        self.phy_graph_widget.hide()
        self.sim_graph_widget.hide()
        self.sim_radio_button.hide()
        self.phy_radio_button.hide()
        self.image_label.show()

    def update_visible_graph(self):
        """ Actualiza visibilidad según el radio activo
        """
        if self.sim_radio_button.isChecked():
            self.phy_graph_widget.hide()
            self.sim_graph_widget.show()
        elif self.phy_radio_button.isChecked():
            self.sim_graph_widget.hide()
            self.phy_graph_widget.show()


class GraphWidget(QThread):
    def __init__(self, domain, display_window=1000):
        super().__init__()
        self.display_window = display_window
        self.__setup_ui(domain)
        self.__setup_connections()

    def __setup_ui(self, domain):
        # Crear widget de gráficos con márgenes en cero
        self.graph_widget = pg.GraphicsLayoutWidget(show=False, title="Graph")
        self.graph_widget.setContentsMargins(0, 0, 0, 0)

        # Remover bordes y márgenes del GraphicsLayoutWidget
        self.graph_widget.setStyleSheet("""border: none;
                                        padding: 0px 0px 0px -5px;""")

        # Optimizaciones globales de PyQtGraph
        pg.setConfigOptions(antialias=False)
        # pg.setConfigOption('useOpenGL', True)

        # Crear gráficos individuales
        self.motor_1 = upgradableGraph(self.graph_widget, "motor 1", [
                                       0, 0], self.display_window)
        self.motor_2 = upgradableGraph(self.graph_widget, "motor 2", [
                                       0, 1], self.display_window)
        self.motor_3 = upgradableGraph(self.graph_widget, "motor 3", [
                                       1, 0], self.display_window)
        self.motor_4 = upgradableGraph(self.graph_widget, "motor 4", [
                                       1, 1], self.display_window)
        self.motor_5 = upgradableGraph(self.graph_widget, "motor 5", [
                                       2, 0], self.display_window)
        self.motor_6 = upgradableGraph(self.graph_widget, "motor 6", [
                                       2, 1], self.display_window)

        self.motor_1.start()
        self.motor_2.start()
        self.motor_3.start()
        self.motor_4.start()
        self.motor_5.start()
        self.motor_6.start()

        # Configurar signal manager según dominio
        if domain is domains.SIMULATION:
            self.signal_manager = SimulationSignalManager.get_instance()
        elif domain is domains.PHYSICAL:
            self.signal_manager = PhysicalSignalManager.get_instance()

        # Buffer para acumular actualizaciones
        self.update_buffer = []
        self.batch_size = 10

        # Timer para actualizaciones periódicas
        self.update_timer = QTimer()
        self.update_timer.setInterval(100)
        self.update_timer.timeout.connect(self._process_buffer)
        self.update_timer.start()

    def __setup_connections(self):
        self.signal_manager.update_graph_signal.connect(self.buffer_update)

    def buffer_update(self, data):
        """Acumula datos en buffer en lugar de actualizar inmediatamente"""
        self.update_buffer.append(data)

    def _process_buffer(self):
        """Procesa el buffer acumulado"""
        if not self.update_buffer:
            return

        for data in self.update_buffer:
            self.motor_1.add_data(data[0])
            self.motor_2.add_data(data[1])
            self.motor_3.add_data(data[2])
            self.motor_4.add_data(data[3])
            self.motor_5.add_data(data[4])
            self.motor_6.add_data(data[5])

        self.update_buffer.clear()

        self.motor_1.update_plot()
        self.motor_2.update_plot()
        self.motor_3.update_plot()
        self.motor_4.update_plot()
        self.motor_5.update_plot()
        self.motor_6.update_plot()
