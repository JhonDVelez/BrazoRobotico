""" En este modulo se define la estructura de la distribución de las gráficas asi como su diseño y
    el comportamiento definido al actualizar una vez se reciben datos nuevos.
"""
import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import QThread, QTimer
from PyQt6.QtWidgets import QWidget, QGridLayout
from data import SimulationSignalManager, PhysicalSignalManager
from .kinematics_worker import KinematicsWorker
from .plot_worker import upgradableGraph


class GraphWorker(QThread):
    """ Hilo de procesamiento de los gráficos definiendo estructura, estilo, ubicación y
        conexiones con los managers de señales.
    """

    def __init__(self, display_window: int = 1000, graphs_amount: int = 6):
        super().__init__()
        self.display_window = display_window
        self.graphs_amount = graphs_amount
        self.is_paused = False

        self.__setup_ui()
        self.__setup_connections()

        # --- OPTIMIZACIÓN: Desacoplamiento visual ---
        # Timer maestro para actualizar la interfaz a ~30 FPS (33 ms)
        self.plot_timer = QTimer()
        self.plot_timer.timeout.connect(self.update_all_plots)
        self.plot_timer.start(33)

    def update_all_plots(self):
        """ Actualiza todas las gráficas de golpe de forma controlada """
        if self.is_paused:
            return
        for motor in self.motors:
            motor.update_plot()

    def __setup_ui(self):
        # Crear el contenedor de gráficos con GridLayout para máxima flexibilidad
        self.graph_widget = QWidget()
        graph_layout = QGridLayout(self.graph_widget)
        graph_layout.setContentsMargins(0, 0, 0, 0)
        graph_layout.setSpacing(0)
        self.graph_widget.setLayout(graph_layout)

        self.graph_widget.setStyleSheet("""border: none;
                                        padding: 0px 0px 0px -5px;""")

        # Optimizaciones globales de PyQtGraph
        pg.setConfigOptions(antialias=False)

        # Crear gráficos individuales
        self.motors = []

        # Etiquetas por cantidad
        labels = [f"motor {i+1}" for i in range(self.graphs_amount)]
        if self.graphs_amount == 3:
            labels = ["X", "Y", "Z"]
        y_range = []
        y_label = ''

        for i in range(self.graphs_amount):
            if self.graphs_amount == 3:
                row = i
                col = 0
                # Límites específicos para X, Y, Z
                if i == 0:  # X: -100 a 400
                    y_range = [-100, 400]
                elif i == 1:  # Y: -400 a 400
                    y_range = [-400, 400]
                else:  # Z: -50 a 550
                    y_range = [-50, 550]
                y_label = 'Posición (mm)'
            else:
                row = i // 2
                col = i % 2
                y_range = [-200, 200]  # Limitado a -200 a 200 para ángulos
                y_label = 'Ángulo (°)'

            motor = upgradableGraph(
                self.graph_widget,
                labels[i],
                [row, col],
                y_range,
                self.display_window
            )
            motor.plot_item.setLabel('left', y_label)
            if row == 2:
                motor.plot_item.setLabel('bottom', 'Tiempo (s)')

            self.motors.append(motor)

        # Managers independientes
        self.sim_signal_manager = SimulationSignalManager.get_instance()
        self.phy_signal_manager = PhysicalSignalManager.get_instance()

        self.kinematics_worker = KinematicsWorker()

    def __setup_connections(self):
        if self.graphs_amount == 6:
            self.sim_signal_manager.update_graph_signal.connect(
                self.sim_angular_buffer_update)
            self.phy_signal_manager.data_received.connect(
                self.phy_angular_buffer_update)
        elif self.graphs_amount == 3:
            self.sim_signal_manager.update_graph_signal.connect(
                self.sim_cartesian_buffer_update)
            self.phy_signal_manager.data_received.connect(
                self.phy_cartesian_buffer_update)

    def sim_angular_buffer_update(self, data):
        if self.is_paused:
            return
        data[1] *= -1
        data[2] *= -1
        for motor, value in zip(self.motors, data):
            motor.add_sim(value)
        # Bucle motor.update_plot() eliminado de aquí

    def phy_angular_buffer_update(self, pos_data, temp_data):
        if self.is_paused:
            return
        pos_data[0] -= 150
        pos_data[1] = -pos_data[1] + 150
        pos_data[2] = -pos_data[2] + 150
        pos_data[3] -= 150
        pos_data[4] -= 150
        pos_data[5] -= 150

        for motor, pos_value, temp_value in zip(self.motors, pos_data, temp_data):
            motor.add_phy(pos_value, temp_value)
        # Bucle motor.update_plot() eliminado de aquí

    def sim_cartesian_buffer_update(self, data):
        if self.is_paused:
            return
        data_rad = np.array([
            np.deg2rad(data[0]),
            np.deg2rad(-data[1]),
            np.deg2rad(-data[2]),
            np.deg2rad(data[4]),
        ]).reshape((4, 1))
        pos = self.kinematics_worker.cd(
            data_rad[0, 0], data_rad[1, 0], data_rad[2, 0], data_rad[3, 0])
        for motor, value in zip(self.motors, pos):
            motor.add_sim(value)
        # Bucle motor.update_plot() eliminado de aquí

    def phy_cartesian_buffer_update(self, pos_data, temp_data):
        if self.is_paused:
            return
        data_rad = np.array([
            np.deg2rad(pos_data[0] - 150.0),
            np.deg2rad(150.0 - pos_data[1]),
            np.deg2rad(150.0 - pos_data[2]),
            np.deg2rad(pos_data[4] - 150.0),
        ]).reshape((4, 1))
        cartesian_pos = self.kinematics_worker.cd(
            data_rad[0, 0], data_rad[1, 0], data_rad[2, 0], data_rad[3, 0])
        for motor, pos_value, temp_value in zip(self.motors, cartesian_pos, temp_data):
            motor.add_phy(pos_value, temp_value)
        # Bucle motor.update_plot() eliminado de aquí

    def start(self):
        self.is_paused = False

    def pause(self):
        """ Pausa la actualización de los valores guardados. """
        self.is_paused = not self.is_paused

    def stop(self):
        """ Detiene el proceso de actualización y limpia los valores guardados """
        self.is_paused = True
        for motor in self.motors:
            motor.stop()
