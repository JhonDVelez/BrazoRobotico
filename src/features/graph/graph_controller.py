"""
Modulo que controla la visualizacion de datos en tiempo real mediante graficos.

Este modulo define la clase GraphController, la cual coordina multiples workers
de datos y procesamiento asincrono para mostrar el comportamiento angular
(servos) y cartesiano (trayectoria) del brazo robotico.

Conexiones:
    - Escucha `update_graph_signal` para datos de simulacion.
    - Escucha `data_received` para telemetria fisica.
    - Distribuye actualizaciones a una coleccion de `PlotController`.
    - Gestiona el cambio entre vista Angular y Cartesiana en la UI.
"""

import numpy as np
from PyQt6.QtCore import QObject, pyqtSlot
from src.features.graph.graph_widget import GraphWidget
from src.features.graph.graph_worker import GraphWorker
from src.features.graph.graph_processing_worker import GraphProcessingWorker
from src.features.graph.plots.plot_controller import PlotController
from src.services.data.signals import SimulationSignalManager, PhysicalSignalManager
from src.services.styling.theme_manger import ThemeSignalManager
from src.services.data import config_manager as cfg


class GraphController(QObject):
    """
    Controlador principal de la seccion de graficas.

    Orquesta la recoleccion de datos crudos, su transformacion mediante
    un procesador cinematico asincrono y su renderizado final en la interfaz
    de usuario.
    """

    def __init__(self, parent=None, kinematics_worker=None):
        """
        Inicializa el controlador de graficas y configura sus componentes.

        Args:
            parent (QWidget, optional): Widget padre para la UI.
            kinematics_worker (KinematicsWorker, optional): Servicio para calculos de CD.
        """
        super().__init__()

        # 1. Componentes Visuales
        self._widget = GraphWidget(parent)

        # 2. Workers de Datos (Angular: 6 ejes, Cartesiano: 3 ejes)
        self._angular_worker = GraphWorker(display_window=1000, graphs_amount=6)
        self._cartesian_worker = GraphWorker(display_window=1000, graphs_amount=3)

        # 3. Controladores de Plot individuales
        self._angular_plots = []
        self._cartesian_plots = []
        self._setup_plots()

        # 4. Procesador de Cinemática (Asíncrono)
        self._kinematics_service = kinematics_worker
        self._processing_worker = GraphProcessingWorker(self._kinematics_service)

        # 5. Establecer conexiones reactivas
        self.__setup_connections()

    def _setup_plots(self):
        """
        Inicializa y configura los controladores para cada grafica individual.

        Lee la configuracion de rejilla desde `graphics.json` para posicionar
        adecuadamente los plots en los layouts angulares y cartesianos.
        """
        config = cfg.get("graphics.json", "grid")

        # Angular (6 motores)
        labels_ang = [f"motor {i+1}" for i in range(6)]
        for i in range(6):
            row, col = i // 2, i % 2
            plot_cfg = [i, "angle", config.get("angle")[i][0:2], config.get("angle")[i][2]]
            pc = PlotController(labels_ang[i], [-200, 200], 1000, plot_cfg, self._widget)
            pc.get_widget().plot_item.setLabel("left", "Ángulo (°)")
            if row == 2: pc.get_widget().plot_item.setLabel("bottom", "Tiempo (s)")

            self._widget.get_angular_layout().addWidget(pc.get_widget(), row, col)
            self._angular_plots.append(pc)

        # Cartesiano (X, Y, Z)
        labels_cart = ["X", "Y", "Z"]
        y_ranges = [[-400, 400], [-400, 400], [-50, 550]]
        for i in range(3):
            plot_cfg = [i, "position", config.get("position")[i][0:2], config.get("position")[i][2]]
            pc = PlotController(labels_cart[i], y_ranges[i], 1000, plot_cfg, self._widget)
            pc.get_widget().plot_item.setLabel("left", "Posición (mm)")
            pc.get_widget().plot_item.setLabel("bottom", "Tiempo (s)")

            self._widget.get_cartesian_layout().addWidget(pc.get_widget(), i, 0)
            self._cartesian_plots.append(pc)

    def __setup_connections(self):
        """
        Configura el flujo de señales entre managers globales, workers y UI.
        """
        # Señales Globales -> Workers
        sim_mgr = SimulationSignalManager.get_instance()
        phy_mgr = PhysicalSignalManager.get_instance()

        sim_mgr.update_graph_signal.connect(self._on_sim_data_received)
        phy_mgr.data_received.connect(self._on_phy_data_received)

        # Procesador Cinematico -> Cartesian Worker
        self._processing_worker.sim_result_ready.connect(self._cartesian_worker.add_sim_data)
        self._processing_worker.phy_result_ready.connect(self._cartesian_worker.add_phy_data)

        # Workers -> Plot Controllers (Angular)
        self._angular_worker.channel_updated.connect(self._update_angular_plot)

        # Workers -> Plot Controllers (Cartesiano)
        self._cartesian_worker.channel_updated.connect(self._update_cartesian_plot)

        # UI -> Visibilidad de paneles
        self._widget.mode_changed.connect(self._on_mode_changed)

        # Cambio de Tema visual
        ThemeSignalManager.get_instance().theme_changed.connect(self._widget.get_image_handler().update_theme)

    @pyqtSlot(list)
    def _on_sim_data_received(self, data):
        """
        Maneja la recepcion de datos de la simulacion.

        Args:
            data (list): Lista de angulos en grados.
        """
        # 1. Procesamiento Angular Sim (Invertir ejes si es necesario por convencion visual)
        ang_data = list(data)
        ang_data[1] *= -1
        ang_data[2] *= -1
        self._angular_worker.add_sim_data(ang_data)

        # 2. Preparación para Cartesiano Sim (vía worker de procesamiento asincrono)
        angles_rad = np.array([
            np.deg2rad(data[0]),
            np.deg2rad(-data[1]),
            np.deg2rad(-data[2]),
            np.deg2rad(data[4]),
        ])
        self._processing_worker.push_sim_angles(angles_rad)

    @pyqtSlot(list, list)
    def _on_phy_data_received(self, pos_data, temp_data):
        """
        Maneja la recepcion de datos reales del robot fisico.

        Args:
            pos_data (list): Posiciones actuales de los servos.
            temp_data (list): Temperaturas de los motores.
        """
        # 1. Procesamiento Angular Phy (Ajuste de offset respecto al centro 150)
        pos_ang = list(pos_data)
        pos_ang[0] -= 150
        pos_ang[1] = -pos_ang[1] + 150
        pos_ang[2] = -pos_ang[2] + 150
        pos_ang[3] -= 150
        pos_ang[4] -= 150
        pos_ang[5] -= 150
        self._angular_worker.add_phy_data(pos_ang, temp_data)

        # 2. Procesamiento Cartesiano Phy (Asíncrono mediante hilos)
        angles_rad = np.array([
            np.deg2rad(pos_data[0] - 150.0),
            np.deg2rad(150.0 - pos_data[1]),
            np.deg2rad(150.0 - pos_data[2]),
            np.deg2rad(pos_data[4] - 150.0),
        ])
        self._processing_worker.push_phy_angles(angles_rad, temp_data)

    def _update_angular_plot(self, idx, y_sim, y_phy, temp, w_idx, full, x):
        """
        Actualiza el buffer de un plot angular especifico.
        """
        if idx < len(self._angular_plots):
            self._angular_plots[idx].update_buffers(y_sim, y_phy, temp, w_idx, full, x)

    def _update_cartesian_plot(self, idx, y_sim, y_phy, temp, w_idx, full, x):
        """
        Actualiza el buffer de un plot cartesiano especifico.
        """
        if idx < len(self._cartesian_plots):
            self._cartesian_plots[idx].update_buffers(y_sim, y_phy, temp, w_idx, full, x)

    def _on_mode_changed(self, is_angular):
        """
        Alterna la visibilidad de los paneles de graficas segun el modo.

        Args:
            is_angular (bool): True si se debe mostrar la vista angular.
        """
        for p in self._angular_plots: p.set_visible(is_angular)
        for p in self._cartesian_plots: p.set_visible(not is_angular)

    # --- API de Control ---

    def start(self):
        """
        Inicia la captura y visualizacion de datos en las graficas.
        """
        self._widget.set_running(True)
        self._angular_worker.set_paused(False)
        self._cartesian_worker.set_paused(False)

        if not self._processing_worker.isRunning():
            self._processing_worker.start()

        # IMPORTANTE: Quitar pausa a todos los plots al iniciar/continuar
        for p in self._angular_plots: p.set_paused(False)
        for p in self._cartesian_plots: p.set_paused(False)

        self._on_mode_changed(self._widget.angular_radio.isChecked())

    def pause(self):
        """
        Alterna el estado de pausa de los workers y los plots.
        """
        # Invertir estado de pausa
        current_paused = self._angular_worker.get_is_paused()
        new_paused = not current_paused

        self._angular_worker.set_paused(new_paused)
        self._cartesian_worker.set_paused(new_paused)

        for p in self._angular_plots: p.set_paused(new_paused)
        for p in self._cartesian_plots: p.set_paused(new_paused)

    def stop(self):
        """
        Detiene los hilos de procesamiento y limpia los buffers de datos.
        """
        self._widget.set_running(False)
        self._angular_worker.set_paused(True)
        self._cartesian_worker.set_paused(True)

        if self._processing_worker.isRunning():
            self._processing_worker.stop()

        self._angular_worker.reset_buffers()
        self._cartesian_worker.reset_buffers()

        # Asegurar que los plots se detengan visualmente
        for p in self._angular_plots: p.set_paused(True)
        for p in self._cartesian_plots: p.set_paused(True)

    def get_widget(self):
        """
        Retorna el widget principal de graficas.

        Returns:
            GraphWidget: Instancia del widget.
        """
        return self._widget

    def cleanup(self):
        """
        Realiza la limpieza de recursos.
        """
        self.stop()
