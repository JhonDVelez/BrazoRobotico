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

from PyQt6.QtCore import QObject, pyqtSlot
from src.features.graph.graph_widget import GraphWidget
from src.features.graph.graph_worker import GraphWorker
from src.features.graph.plots.plot_controller import PlotController
from src.features.graph.cartesian_pid_plot import CartesianPIDPlot
from src.services.data.signals import SimulationSignalManager, PhysicalSignalManager, ConfigSignalManager, ThemeSignalManager


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

        # 2. Workers de Datos (Angular: 6 ejes)
        self._angular_worker = GraphWorker(display_window=1000, graphs_amount=6)

        # 3. Controladores de Plot individuales (Angulares)
        self._current_cols = 0
        self._angular_plots = []
        self._setup_plots()

        # 4. Grafico Cartesiano PID (matplotlib)
        self._kinematics_service = kinematics_worker
        self._cartesian_pid_plot = CartesianPIDPlot()
        self._widget.set_cartesian_pid_widget(self._cartesian_pid_plot)

        # 5. Establecer conexiones reactivas
        self.__setup_connections()

    def _setup_plots(self):
        """
        Inicializa los controladores para cada grafica individual.
        
        No los agrega al layout inmediatamente; delega esta tarea a _rearrange_plots
        para permitir una disposicion responsiva.
        """
        config_manager = ConfigSignalManager.get_instance()
        config = config_manager.get_param("graphics.json", "grid", default={})

        # Angular (6 motores)
        labels_ang = [f"motor {i+1}" for i in range(6)]
        for i in range(6):
            plot_cfg = [i, "angle", config.get("angle")[i][0:2], config.get("angle")[i][2]]
            pc = PlotController(labels_ang[i], [-200, 200], 1000, plot_cfg, self._widget)
            pc.get_widget().plot_item.setLabel("left", "Ángulo (°)")
            self._angular_plots.append(pc)

        # Disposición inicial angular
        self._rearrange_plots(self._widget.width())

    def _rearrange_plots(self, width):
        """
        Calcula y ajusta la cantidad de columnas en los layouts segun el ancho.
        
        Args:
            width (int): Ancho actual del widget de graficas.
        """
        new_cols = max(1, width // 350)
        if new_cols > 3: new_cols = 3
        
        if new_cols == self._current_cols:
            return
            
        self._current_cols = new_cols
        
        ang_layout = self._widget.get_angular_layout()
        while ang_layout.count():
            item = ang_layout.takeAt(0)
            if item.widget():
                item.widget().hide()

        for i, pc in enumerate(self._angular_plots):
            row, col = i // new_cols, i % new_cols
            widget = pc.get_widget()
            self._widget.get_angular_layout().addWidget(widget, row, col)
            widget.show()
            show_time = (i >= len(self._angular_plots) - new_cols)
            widget.plot_item.setLabel("bottom", "Tiempo (s)" if show_time else "")

    def __setup_connections(self):
        """
        Configura el flujo de señales entre managers globales, workers y UI.
        """
        # Señales Globales -> Workers
        sim_mgr = SimulationSignalManager.get_instance()
        phy_mgr = PhysicalSignalManager.get_instance()

        sim_mgr.update_graph_signal.connect(self._on_sim_data_received)
        phy_mgr.data_received.connect(self._on_phy_data_received)

        # Kinematics Worker -> Cartesian PID Plot
        self._kinematics_service.pid_iteration.connect(self._on_pid_iteration)

        # Workers -> Plot Controllers (Angular)
        self._angular_worker.channel_updated.connect(self._update_angular_plot)

        # UI -> Visibilidad de paneles
        self._widget.mode_changed.connect(self._on_mode_changed)
        self._widget.resize_requested.connect(self._rearrange_plots)

        # Cambio de Tema visual
        ThemeSignalManager.get_instance().theme_changed.connect(self._widget.get_image_handler().update_theme)

    @pyqtSlot(list)
    def _on_sim_data_received(self, data):
        """
        Maneja la recepcion de datos de la simulacion.

        Args:
            data (list): Lista de angulos en grados.
        """
        ang_data = list(data)
        ang_data[1] *= -1
        ang_data[2] *= -1
        self._angular_worker.add_sim_data(ang_data)

    @pyqtSlot(list, list)
    def _on_phy_data_received(self, pos_data, temp_data):
        """
        Maneja la recepcion de datos reales del robot fisico.

        Args:
            pos_data (list): Posiciones actuales de los servos.
            temp_data (list): Temperaturas de los motores.
        """
        print(f"Datos de robot recibidos: Posiciones={pos_data}, Temperaturas={temp_data}")
        pos_ang = list(pos_data)
        pos_ang[0] -= 150
        pos_ang[1] = -pos_ang[1] + 150
        pos_ang[2] = -pos_ang[2] + 150
        pos_ang[3] -= 150
        pos_ang[4] -= 150
        pos_ang[5] -= 150
        self._angular_worker.add_phy_data(pos_ang, temp_data)

    def _update_angular_plot(self, idx, y_sim, y_phy, temp, w_idx, full, x):
        """
        Actualiza el buffer de un plot angular especifico.
        """
        if idx < len(self._angular_plots):
            self._angular_plots[idx].update_buffers(y_sim, y_phy, temp, w_idx, full, x)

    @pyqtSlot(int, list, list)
    def _on_pid_iteration(self, iteration, actual_xyz, target_xyz):
        if iteration == 0:
            self._cartesian_pid_plot.reset_plot(target_xyz)
        self._cartesian_pid_plot.append_data(iteration, actual_xyz, target_xyz)

    def _on_mode_changed(self, is_angular):
        """
        Alterna la visibilidad de los paneles de graficas segun el modo.

        Args:
            is_angular (bool): True si se debe mostrar la vista angular.
        """
        for p in self._angular_plots: p.set_visible(is_angular)
        self._cartesian_pid_plot.setVisible(not is_angular)

    # --- API de Control ---

    def start(self):
        """
        Inicia la captura y visualizacion de datos en las graficas.
        """
        self._widget.set_running(True)
        self._angular_worker.set_paused(False)

        for p in self._angular_plots: p.set_paused(False)

        self._on_mode_changed(self._widget.angular_radio.isChecked())

    def pause(self):
        """
        Alterna el estado de pausa de los workers y los plots.
        """
        current_paused = self._angular_worker.get_is_paused()
        new_paused = not current_paused

        self._angular_worker.set_paused(new_paused)

        for p in self._angular_plots: p.set_paused(new_paused)

    def stop(self):
        """
        Detiene los hilos de procesamiento y limpia los buffers de datos.
        """
        self._widget.set_running(False)
        self._angular_worker.set_paused(True)

        self._angular_worker.reset_buffers()

        for p in self._angular_plots: p.set_paused(True)

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
