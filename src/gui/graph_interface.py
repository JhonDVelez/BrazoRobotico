import os
import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import Qt, QElapsedTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QSizePolicy
from gui.main_window.image_utils_mixin import ImageUtilsMixin
from gui.main_window.main_theme_mixin import ThemeManager
from gui.graph_worker import GraphWidget


class graphInterface(ImageUtilsMixin):
    def __init__(self, domain):
        super().__init__()
        self.process_running = False
        self.theme_manager = ThemeManager.get_instance()

        self.__setup_ui(domain)
        self.__setup_connections()

        self.timer = QElapsedTimer()
        self.timer.start()

    def __setup_ui(self, domain):
        self.setContentsMargins(0, 0, 0, 0)
        self.graph_object = GraphWidget(domain, 1000)
        self.graph_widget = self.graph_object.graph_widget
        self.graph_widget.setContentsMargins(0, 0, 0, 0)

        if not self.layout():
            self.graph_layout = QVBoxLayout(self)
            self.graph_layout.setContentsMargins(0, 0, 0, 0)
            self.setLayout(self.graph_layout)

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
