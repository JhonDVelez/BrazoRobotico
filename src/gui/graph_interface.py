"""
GraphInterface simplificado: ya no gestiona ningún timer.
Cada GraphWorker agenda sus propios renders en cuanto llegan datos.
"""
import os
from PyQt6.QtCore import Qt, QElapsedTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QLabel, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QSizePolicy, QRadioButton,
)
from gui.main_window.image_utils_mixin import ImageUtilsMixin
from gui.main_window.main_theme_mixin import ThemeManager
from gui.graph_worker import GraphWorker
from data.control_utils import Domains


class GraphInterface(ImageUtilsMixin):
    """Estructura de la sección de gráficas.

    Con el renderizado event-driven en GraphWorker, esta clase solo
    gestiona visibilidad, tema y ciclo de vida (start/pause/stop).
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
        self.setObjectName("radio_button_container")
        graph_layout = QVBoxLayout(self)
        graph_layout.setContentsMargins(0, 0, 0, 0)
        graph_layout.setSpacing(0)

        self.angular_graph_object = GraphWorker(1000, 6)
        self.angular_graph_widget = self.angular_graph_object.graph_widget
        self.angular_graph_object.is_visible = True

        self.cartesian_graph_object = GraphWorker(1000, 3)
        self.cartesian_graph_widget = self.cartesian_graph_object.graph_widget
        self.cartesian_graph_object.is_visible = False

        self.stacked_widget = QStackedWidget()

        self.image_path_d = os.path.join("img:graph_d.svg")
        self.image_path_l = os.path.join("img:graph_l.svg")
        self.pixmap = QPixmap(self.image_path_d)

        radio_style = "QRadioButton::indicator {margin-left: 0px; background-color: transparent}"
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

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.image_label.setMinimumSize(160, 120)
        self.image_label.setContentsMargins(0, 0, 0, 0)

        graph_layout.addWidget(self.image_label)
        self.stacked_widget.addWidget(self.angular_graph_widget)
        self.stacked_widget.addWidget(self.cartesian_graph_widget)
        graph_layout.addWidget(self.stacked_widget)

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
        self.image_label.hide()
        self.stacked_widget.show()
        self.angular_graph_widget.show()
        self.sim_radio_button.show()
        self.phy_radio_button.show()
        self.angular_graph_object.start()
        self.cartesian_graph_object.start()

    def pause(self):
        self.angular_graph_object.pause()
        self.cartesian_graph_object.pause()

    def stop(self):
        self.angular_graph_object.stop()
        self.cartesian_graph_object.stop()
        self.stacked_widget.hide()
        self.angular_graph_widget.hide()
        self.sim_radio_button.hide()
        self.phy_radio_button.hide()
        self.image_label.show()
        self.set_static_image()

    def update_visible_graph(self):
        angular_active = self.sim_radio_button.isChecked()
        self.stacked_widget.setCurrentIndex(0 if angular_active else 1)
        self.angular_graph_object.is_visible = angular_active
        self.cartesian_graph_object.is_visible = not angular_active
