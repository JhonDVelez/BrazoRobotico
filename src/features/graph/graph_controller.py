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
    Controlador principal de la sección de gráficas.
    Coordina la recolección de datos, el procesamiento cinemático asíncrono 
    y la distribución hacia los controladores de plots individuales.
    """
    def __init__(self, parent=None, kinematics_worker=None):
        super().__init__()
        
        # 1. Componentes
        self._widget = GraphWidget(parent)
        
        # 2. Workers de Datos (Angular: 6 ejes, Cartesiano: 3 ejes)
        self._angular_worker = GraphWorker(display_window=1000, graphs_amount=6)
        self._cartesian_worker = GraphWorker(display_window=1000, graphs_amount=3)
        
        # 3. Controladores de Plot
        self._angular_plots = []
        self._cartesian_plots = []
        self._setup_plots()
        
        # 4. Procesador de Cinemática (Asíncrono)
        # Recibimos el worker de cinemática inyectado desde el controlador superior
        self._kinematics_service = kinematics_worker
        self._processing_worker = GraphProcessingWorker(self._kinematics_service)
        
        # 5. Conexiones
        self.__setup_connections()

    def _setup_plots(self):
        """ Inicializa los controladores de cada gráfica individual """
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
        # Señales Globales -> Workers
        sim_mgr = SimulationSignalManager.get_instance()
        phy_mgr = PhysicalSignalManager.get_instance()
        
        sim_mgr.update_graph_signal.connect(self._on_sim_data_received)
        phy_mgr.data_received.connect(self._on_phy_data_received)
        
        # Procesador -> Cartesian Worker
        self._processing_worker.sim_result_ready.connect(self._cartesian_worker.add_sim_data)
        self._processing_worker.phy_result_ready.connect(self._cartesian_worker.add_phy_data)
        
        # Workers -> Plot Controllers (Angular)
        self._angular_worker.channel_updated.connect(self._update_angular_plot)
        
        # Workers -> Plot Controllers (Cartesiano)
        self._cartesian_worker.channel_updated.connect(self._update_cartesian_plot)
        
        # UI -> Visibilidad
        self._widget.mode_changed.connect(self._on_mode_changed)
        
        # Tema
        ThemeSignalManager.get_instance().theme_changed.connect(self._widget.get_image_handler().update_theme)

    @pyqtSlot(list)
    def _on_sim_data_received(self, data):
        # 1. Procesamiento Angular Sim
        ang_data = list(data)
        ang_data[1] *= -1
        ang_data[2] *= -1
        self._angular_worker.add_sim_data(ang_data)
        
        # 2. Preparación para Cartesiano Sim (vía worker de procesamiento)
        angles_rad = np.array([
            np.deg2rad(data[0]),
            np.deg2rad(-data[1]),
            np.deg2rad(-data[2]),
            np.deg2rad(data[4]),
        ])
        self._processing_worker.push_sim_angles(angles_rad)

    @pyqtSlot(list, list)
    def _on_phy_data_received(self, pos_data, temp_data):
        # 1. Procesamiento Angular Phy
        pos_ang = list(pos_data)
        pos_ang[0] -= 150
        pos_ang[1] = -pos_ang[1] + 150
        pos_ang[2] = -pos_ang[2] + 150
        pos_ang[3] -= 150
        pos_ang[4] -= 150
        pos_ang[5] -= 150
        self._angular_worker.add_phy_data(pos_ang, temp_data)
        
        # 2. Procesamiento Cartesiano Phy (Asíncrono)
        angles_rad = np.array([
            np.deg2rad(pos_data[0] - 150.0),
            np.deg2rad(150.0 - pos_data[1]),
            np.deg2rad(150.0 - pos_data[2]),
            np.deg2rad(pos_data[4] - 150.0),
        ])
        self._processing_worker.push_phy_angles(angles_rad, temp_data)

    def _update_angular_plot(self, idx, y_sim, y_phy, temp, w_idx, full, x):
        if idx < len(self._angular_plots):
            self._angular_plots[idx].update_buffers(y_sim, y_phy, temp, w_idx, full, x)

    def _update_cartesian_plot(self, idx, y_sim, y_phy, temp, w_idx, full, x):
        if idx < len(self._cartesian_plots):
            self._cartesian_plots[idx].update_buffers(y_sim, y_phy, temp, w_idx, full, x)

    def _on_mode_changed(self, is_angular):
        for p in self._angular_plots: p.set_visible(is_angular)
        for p in self._cartesian_plots: p.set_visible(not is_angular)

    # --- API de Control ---

    def start(self):
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
        # Invertir estado de pausa
        current_paused = self._angular_worker.get_is_paused()
        new_paused = not current_paused
        
        self._angular_worker.set_paused(new_paused)
        self._cartesian_worker.set_paused(new_paused)
        
        for p in self._angular_plots: p.set_paused(new_paused)
        for p in self._cartesian_plots: p.set_paused(new_paused)

    def stop(self):
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
        return self._widget

    def cleanup(self):
        self.stop()
