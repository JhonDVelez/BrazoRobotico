import os
import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QSizePolicy
from data.control_utils import SimulationSignalManager, PhysicalSignalManager, domains
from gui.main_window.theme_stylesheet import dark, light
from gui.main_window.image_utils_mixin import ImageUtilsMixin
from gui.main_window.main_theme_mixin import ThemeManager


class graphInterface(ImageUtilsMixin):
    def __init__(self, domain):
        super().__init__()
        self.process_running = False
        self.theme_manager = ThemeManager.get_instance()

        self.__setup_ui(domain)
        self.__setup_connections()

    def __setup_ui(self, domain):
        self.graph_widget = pg.GraphicsLayoutWidget(show=False, title="Graph")
        self.motor_1 = upgradableGraph(self.graph_widget, "motor 1", [0, 0])
        self.motor_2 = upgradableGraph(self.graph_widget, "motor 2", [0, 1])
        self.motor_3 = upgradableGraph(self.graph_widget, "motor 3", [1, 0])
        self.motor_4 = upgradableGraph(self.graph_widget, "motor 4", [1, 1])
        self.motor_5 = upgradableGraph(self.graph_widget, "motor 5", [2, 0])
        self.motor_6 = upgradableGraph(self.graph_widget, "motor 6", [2, 1])

        if not self.layout():
            self.graph_layout = QVBoxLayout(self)
            self.graph_layout.setContentsMargins(0, 0, 0, 0)
            self.setLayout(self.graph_layout)

        if domain is domains.SIMULATION:
            self.signal_manager = SimulationSignalManager()

        self.image_path_r = os.path.join(os.path.dirname(
            __file__), "img", 'graph_r.png')
        self.image_path_b = os.path.join(os.path.dirname(
            __file__), "img", 'graph_b.png')
        self.pixmap = QPixmap(self.image_path_r)
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.image_label.setMinimumSize(160, 120)
        self.layout().addWidget(self.image_label)
        self.layout().addWidget(self.graph_widget)
        self.graph_widget.hide()

    def __setup_connections(self):
        self.theme_manager.theme_changed.connect(self.toggle_theme)

    def update_motors(self, data):
        self.motor_1.update_data(data[0])
        self.motor_2.update_data(data[1])
        self.motor_3.update_data(data[2])
        self.motor_4.update_data(data[3])
        self.motor_5.update_data(data[4])
        self.motor_6.update_data(data[5])


class upgradableGraph:
    def __init__(self, graph_widget, title, pos):
        self.graph_widget = graph_widget
        # Se define una cantidad de 24M de puntos
        self.x = np.zeros(24000000, dtype=np.float32)
        self.y = np.zeros(24000000, dtype=np.float32)

        self.graph_widget.setBackground('k')

        pen = pg.mkPen(color=(255, 0, 0))
        self.motor = self.graph_widget.addPlot(
            title=title, row=pos[0], col=pos[1], pen=pen)

    def update_data(self, data):
        self.y = self.y[1:]
        self.y = np.append(self.y, data)
        self.motor.setData(self.y)
