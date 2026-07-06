"""
Módulo que controla la visualización de datos en tiempo real mediante gráficos.

Este módulo define la clase GraphController, la cual coordina múltiples workers
de datos y procesamiento asíncrono para mostrar el comportamiento angular
(servos) y cartesiano (trayectoria) del brazo robótico.

Conexiones:
    - Escucha `update_graph_signal` para datos de simulación.
    - Escucha `data_received` para telemetría física.
    - Distribuye actualizaciones a una colección de `PlotController`.
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
    Controlador principal de la sección de gráficas.

    Orquesta la recolección de datos crudos, su transformación mediante
    un procesador cinemático asíncrono y su renderizado final en la interfaz
    de usuario.
    """

    def __init__(self, parent=None, kinematics_worker=None):
        """
        Inicializa el controlador de gráficas y configura sus componentes.

        Args:
            parent (QWidget, optional): Widget padre para la UI.
            kinematics_worker (KinematicsWorker, optional): Servicio para cálculos de CD.
        """
        super().__init__()

        # 1. Componentes Visuales
        self._widget = GraphWidget(parent)

<<<<<<< HEAD
        # 2. Workers de Datos (Angular: 6 ejes)
        self._angular_worker = GraphWorker(display_window=1000, graphs_amount=6)

        # 3. Controladores de Plot individuales (Angulares)
        self._current_cols = 0
        self._angular_plots = []
=======
        # 2. Workers de Datos (Angular: 6 ejes, Cartesiano: 3 ejes)
        self._angular_worker = GraphWorker(
            display_window=1000, graphs_amount=6)
        self._cartesian_worker = GraphWorker(
            display_window=1000, graphs_amount=3)

        # 3. Controladores de Plot individuales
        self._current_cols = 0  # Para evitar re-layouts innecesarios
        self._angular_plots: list[PlotController] = []
        self._cartesian_plots: list[PlotController] = []
>>>>>>> 1825586cf103f63ef7f9c90d4540b2f568c648da
        self._setup_plots()

        # 4. Grafico Cartesiano PID (matplotlib)
        self._kinematics_service = kinematics_worker
<<<<<<< HEAD
        self._cartesian_pid_plot = CartesianPIDPlot()
        self._widget.set_cartesian_pid_widget(self._cartesian_pid_plot)
=======
        self._processing_worker = GraphProcessingWorker(
            self._kinematics_service)
>>>>>>> 1825586cf103f63ef7f9c90d4540b2f568c648da

        # 5. Establecer conexiones reactivas
        self.__setup_connections()

    def _setup_plots(self):
        """
        Inicializa los controladores para cada gráfica individual.

        No los agrega al layout inmediatamente; delega esta tarea a _rearrange_plots
        para permitir una disposición responsiva.
        """
        config_manager = ConfigSignalManager.get_instance()
        config = config_manager.get_param("graphics.json", "grid", default={})

        # Angular (6 motores)
        labels_ang = [f"motor {i+1}" for i in range(6)]
        for i in range(6):
            plot_cfg = [i, "angle", config.get(
                "angle")[i][0:2], config.get("angle")[i][2]]
            pc = PlotController(
                labels_ang[i], [-200, 200], 1000, plot_cfg, self._widget)
            pc.get_widget().plot_item.setLabel("left", "Ángulo (°)")
            self._angular_plots.append(pc)

<<<<<<< HEAD
        # Disposición inicial angular
=======
        # Cartesiano (X, Y, Z)
        labels_cart = ["X", "Y", "Z"]
        y_ranges = [[-400, 400], [-400, 400], [-50, 550]]
        for i in range(3):
            plot_cfg = [i, "position", config.get(
                "position")[i][0:2], config.get("position")[i][2]]
            pc = PlotController(
                labels_cart[i], y_ranges[i], 1000, plot_cfg, self._widget)
            pc.get_widget().plot_item.setLabel("left", "Posición (mm)")
            self._cartesian_plots.append(pc)

        # Disposición inicial
>>>>>>> 1825586cf103f63ef7f9c90d4540b2f568c648da
        self._rearrange_plots(self._widget.width())

    def _rearrange_plots(self, width):
        """
        Calcula y ajusta la cantidad de columnas en los layouts según el ancho.

        Args:
            width (int): Ancho actual del widget de gráficas.
        """
        new_cols = max(1, width // 350)
<<<<<<< HEAD
        if new_cols > 3: new_cols = 3
        
=======
        if new_cols > 3:
            new_cols = 3  # Límite máximo de columnas

>>>>>>> 1825586cf103f63ef7f9c90d4540b2f568c648da
        if new_cols == self._current_cols:
            return

        self._current_cols = new_cols
<<<<<<< HEAD
        
=======

        # Limpiar layouts sin destruir los widgets
>>>>>>> 1825586cf103f63ef7f9c90d4540b2f568c648da
        ang_layout = self._widget.get_angular_layout()
        while ang_layout.count():
            item = ang_layout.takeAt(0)
            if item.widget():
<<<<<<< HEAD
=======
                item.widget().hide()  # Ocultar temporalmente

        cart_layout = self._widget.get_cartesian_layout()
        while cart_layout.count():
            item = cart_layout.takeAt(0)
            if item.widget():
>>>>>>> 1825586cf103f63ef7f9c90d4540b2f568c648da
                item.widget().hide()

        for i, pc in enumerate(self._angular_plots):
            row, col = i // new_cols, i % new_cols
            widget = pc.get_widget()
            self._widget.get_angular_layout().addWidget(widget, row, col)
            widget.show()
            show_time = (i >= len(self._angular_plots) - new_cols)
            widget.plot_item.setLabel(
                "bottom", "Tiempo (s)" if show_time else "")

    def __setup_connections(self):
        """
        Configura el flujo de señales entre managers globales, workers y UI.
        """
        # Señales Globales -> Workers
        sim_mgr = SimulationSignalManager.get_instance()
        phy_mgr = PhysicalSignalManager.get_instance()

        sim_mgr.update_graph_signal.connect(self._on_sim_data_received)
        phy_mgr.data_received.connect(self._on_phy_data_received)

<<<<<<< HEAD
        # Kinematics Worker -> Cartesian PID Plot
        self._kinematics_service.pid_iteration.connect(self._on_pid_iteration)
=======
        # Procesador Cinematico -> Cartesian Worker
        self._processing_worker.sim_result_ready.connect(
            self._cartesian_worker.add_sim_data)
        self._processing_worker.phy_result_ready.connect(
            self._cartesian_worker.add_phy_data)
>>>>>>> 1825586cf103f63ef7f9c90d4540b2f568c648da

        # Workers -> Plot Controllers (Angular)
        self._angular_worker.channel_updated.connect(self._update_angular_plot)

<<<<<<< HEAD
=======
        # Workers -> Plot Controllers (Cartesiano)
        self._cartesian_worker.channel_updated.connect(
            self._update_cartesian_plot)

>>>>>>> 1825586cf103f63ef7f9c90d4540b2f568c648da
        # UI -> Visibilidad de paneles
        self._widget.mode_changed.connect(self._on_mode_changed)
        self._widget.resize_requested.connect(self._rearrange_plots)

        # Cambio de Tema visual
        ThemeSignalManager.get_instance().theme_changed.connect(
            self._widget.get_image_handler().update_theme)

    @pyqtSlot(list)
    def _on_sim_data_received(self, data):
        """
        Maneja la recepción de datos de la simulación.

        Args:
            data (list): Lista de ángulos en grados.
        """
<<<<<<< HEAD
=======
        # 1. Procesamiento Angular Sim (Invertir ejes si es necesario por convencion visual)
>>>>>>> 1825586cf103f63ef7f9c90d4540b2f568c648da
        ang_data = list(data)
        ang_data[1] *= -1
        ang_data[2] *= -1
        self._angular_worker.add_sim_data(ang_data)

<<<<<<< HEAD
=======
        # 2. Preparación para Cartesiano Sim (vía worker de procesamiento asíncrono)
        angles_rad = np.array([
            np.deg2rad(data[0]),
            np.deg2rad(-data[1]),
            np.deg2rad(-data[2]),
            np.deg2rad(data[4]),
        ])
        self._processing_worker.push_sim_angles(angles_rad)

>>>>>>> 1825586cf103f63ef7f9c90d4540b2f568c648da
    @pyqtSlot(list, list)
    def _on_phy_data_received(self, pos_data, temp_data):
        """
        Maneja la recepción de datos reales del robot físico.

        Args:
            pos_data (list): Posiciones actuales de los servos.
            temp_data (list): Temperaturas de los motores.
        """
<<<<<<< HEAD
        print(f"Datos de robot recibidos: Posiciones={pos_data}, Temperaturas={temp_data}")
=======
        # 1. Procesamiento Angular Phy (Ajuste de offset respecto al centro 150)
        print(
            f"Datos de robot recibidos: Posiciones={pos_data}, Temperaturas={temp_data}")
>>>>>>> 1825586cf103f63ef7f9c90d4540b2f568c648da
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
        Actualiza el buffer de un plot angular específico.
        """
        if idx < len(self._angular_plots):
            self._angular_plots[idx].update_buffers(
                y_sim, y_phy, temp, w_idx, full, x)

<<<<<<< HEAD
    @pyqtSlot(int, list, list)
    def _on_pid_iteration(self, iteration, actual_xyz, target_xyz):
        if iteration == 0:
            self._cartesian_pid_plot.reset_plot(target_xyz)
        self._cartesian_pid_plot.append_data(iteration, actual_xyz, target_xyz)
=======
    def _update_cartesian_plot(self, idx, y_sim, y_phy, temp, w_idx, full, x):
        """
        Actualiza el buffer de un plot cartesiano específico.
        """
        if idx < len(self._cartesian_plots):
            self._cartesian_plots[idx].update_buffers(
                y_sim, y_phy, temp, w_idx, full, x)
>>>>>>> 1825586cf103f63ef7f9c90d4540b2f568c648da

    def _on_mode_changed(self, is_angular):
        """
        Alterna la visibilidad de los paneles de gráficas según el modo.

        Args:
            is_angular (bool): True si se debe mostrar la vista angular.
        """
<<<<<<< HEAD
        for p in self._angular_plots: p.set_visible(is_angular)
        self._cartesian_pid_plot.setVisible(not is_angular)
=======
        for p in self._angular_plots:
            p.set_visible(is_angular)
        for p in self._cartesian_plots:
            p.set_visible(not is_angular)
>>>>>>> 1825586cf103f63ef7f9c90d4540b2f568c648da

    # --- API de Control ---

    def start(self):
        """
        Inicia la captura y visualización de datos en las gráficas.
        """
        self._widget.set_running(True)
        self._angular_worker.set_paused(False)

<<<<<<< HEAD
        for p in self._angular_plots: p.set_paused(False)
=======
        if not self._processing_worker.isRunning():
            self._processing_worker.start()

        # IMPORTANTE: Quitar pausa a todos los plots al iniciar/continuar
        for p in self._angular_plots:
            p.set_paused(False)
        for p in self._cartesian_plots:
            p.set_paused(False)
>>>>>>> 1825586cf103f63ef7f9c90d4540b2f568c648da

        self._on_mode_changed(self._widget.angular_radio.isChecked())

    def pause(self):
        """
        Alterna el estado de pausa de los workers y los plots.
        """
        current_paused = self._angular_worker.get_is_paused()
        new_paused = not current_paused

        self._angular_worker.set_paused(new_paused)

<<<<<<< HEAD
        for p in self._angular_plots: p.set_paused(new_paused)
=======
        for p in self._angular_plots:
            p.set_paused(new_paused)
        for p in self._cartesian_plots:
            p.set_paused(new_paused)
>>>>>>> 1825586cf103f63ef7f9c90d4540b2f568c648da

    def stop(self):
        """
        Detiene los hilos de procesamiento y limpia los buffers de datos.
        """
        self._widget.set_running(False)
        self._angular_worker.set_paused(True)

        self._angular_worker.reset_buffers()

<<<<<<< HEAD
        for p in self._angular_plots: p.set_paused(True)
=======
        # Asegurar que los plots se detengan visualmente
        for p in self._angular_plots:
            p.set_paused(True)
        for p in self._cartesian_plots:
            p.set_paused(True)
>>>>>>> 1825586cf103f63ef7f9c90d4540b2f568c648da

    def get_widget(self):
        """
        Retorna el widget principal de gráficas.

        Returns:
            GraphWidget: Instancia del widget.
        """
        return self._widget

    def cleanup(self):
        """
        Realiza la limpieza de recursos y guarda la configuración pendiente.
        """
        flushed_types = set()
        for pc in self._angular_plots + self._cartesian_plots:
            if pc._graph_type not in flushed_types and pc._pending_config is not None:
                pc.flush_pending_config()
                flushed_types.add(pc._graph_type)
        self.stop()
