"""
Renderizado dirigido por eventos (event-driven) con coalescencia:

  - Cuando llegan datos se llama _schedule_render().
  - Si no hay un render ya agendado se dispara QTimer.singleShot(0, _do_render).
    Esto coloca el render en la siguiente vuelta del event loop de Qt (~1-2 ms).
  - Si ya había un render agendado, simplemente se ignora: cuando ese render
    llegue a ejecutarse ya encontrará los datos más recientes (coalesce).
  - Un FPS cap (MIN_INTERVAL_MS) evita renderizar más rápido de lo que la
    pantalla puede mostrar, protegiendo el hilo GUI ante ráfagas de datos.

Latencia típica: 1-3 ms (antes: hasta 33 ms con el timer fijo).
"""
import queue
import time
import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import QWidget, QGridLayout
from data import SimulationSignalManager, PhysicalSignalManager
from .kinematics_worker import KinematicsWorker
from .plot_worker import upgradableGraph
from data import config_manager as cfg


# ---------------------------------------------------------------------------
# Hilo dedicado para cinemática directa
# ---------------------------------------------------------------------------
class KinematicsThread(QThread):
    """Ejecuta cd() fuera del hilo GUI.

    maxsize=1 garantiza que siempre se procesa el frame MÁS RECIENTE:
    si llega uno nuevo antes de que el anterior se procese, lo reemplaza.
    """
    result_ready = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        # maxsize=1: descarta frames viejos, nunca acumula latencia
        self._queue: queue.Queue = queue.Queue(maxsize=1)
        self._worker = KinematicsWorker()
        self._running = True

    def push_angles(self, angles: np.ndarray):
        """Reemplaza el frame pendiente (si lo hay) por el más reciente."""
        try:
            self._queue.get_nowait()
        except queue.Empty:
            pass
        try:
            self._queue.put_nowait(angles)
        except queue.Full:
            pass

    def run(self):
        while self._running:
            try:
                angles = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
            pos = self._worker.cd(angles[0], angles[1], angles[2], angles[3])
            self.result_ready.emit(list(pos))

    def stop(self):
        self._running = False
        self.wait()


# ---------------------------------------------------------------------------
# GraphWorker con renderizado event-driven
# ---------------------------------------------------------------------------
class GraphWorker:
    """Gestiona un set de gráficas con renderizado dirigido por eventos.

    Flujo cuando llegan datos:
        señal Qt -> buffer_update() -> _schedule_render()
                                           |
                                    (si no hay render pendiente)
                                           |
                                    QTimer.singleShot(0, _do_render)
                                           |
                                    (siguiente vuelta del event loop)
                                           |
                                    update_plot() solo en motores con datos nuevos
    """

    # Intervalo mínimo entre renders en ms. 16 ms aprox 60 FPS.
    MIN_INTERVAL_MS: float = 16.0

    def __init__(self, display_window: int = 1000, graphs_amount: int = 6):
        self.display_window = display_window
        self.graphs_amount = graphs_amount
        self.is_paused = False
        self.is_visible = True

        self._render_scheduled: bool = False
        self._last_render_ns: int = 0

        self.__setup_ui()
        self.__setup_connections()

    # ------------------------------------------------------------------
    # Scheduling de renders
    # ------------------------------------------------------------------
    def _schedule_render(self):
        """Agenda un render para la próxima vuelta del event loop si no hay uno ya."""
        if self._render_scheduled or not self.is_visible or self.is_paused:
            return
        self._render_scheduled = True
        QTimer.singleShot(0, self._do_render)

    def _do_render(self):
        """Ejecuta el render; si han pasado muy pocos ms lo pospone (FPS cap)."""
        self._render_scheduled = False

        if self.is_paused or not self.is_visible:
            return

        now_ns = time.monotonic_ns()
        elapsed_ms = (now_ns - self._last_render_ns) / 1_000_000
        if self._last_render_ns and elapsed_ms < self.MIN_INTERVAL_MS:
            remaining_ms = int(self.MIN_INTERVAL_MS - elapsed_ms)
            self._render_scheduled = True
            QTimer.singleShot(remaining_ms, self._do_render)
            return

        self._last_render_ns = now_ns
        for motor in self.motors:
            if motor.has_new_data:
                motor.update_plot()
                motor.has_new_data = False

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    def __setup_ui(self):
        self.graph_widget = QWidget()
        graph_layout = QGridLayout(self.graph_widget)
        graph_layout.setContentsMargins(0, 0, 0, 0)
        graph_layout.setSpacing(0)
        self.graph_widget.setLayout(graph_layout)
        self.graph_widget.setStyleSheet(
            "border: none; padding: 0px 0px 0px -5px;")

        pg.setConfigOptions(antialias=False)
        config = cfg.get("graphics.json", "grid")
        graph_type = None

        self.motors = []
        labels = [f"motor {i+1}" for i in range(self.graphs_amount)]
        if self.graphs_amount == 3:
            labels = ["X", "Y", "Z"]

        for i in range(self.graphs_amount):
            if self.graphs_amount == 3:
                row, col = i, 0
                y_ranges = [[-400, 400], [-400, 400], [-50, 550]]
                y_range = y_ranges[i]
                y_label = "Posición (mm)"
                graph_type = "position"
            else:
                row, col = i // 2, i % 2
                y_range = [-200, 200]
                y_label = "Ángulo (°)"
                graph_type = "angle"

            *init_scale, visible_grid = config.get(graph_type)[i]
            motor = upgradableGraph(
                self.graph_widget,
                labels[i],
                [row, col],
                y_range,
                self.display_window,
                [i, graph_type, init_scale, visible_grid]
            )
            motor.plot_item.setLabel("left", y_label)
            if row == 2:
                motor.plot_item.setLabel("bottom", "Tiempo (s)")
            motor.has_new_data = False
            self.motors.append(motor)

        self.sim_signal_manager = SimulationSignalManager.get_instance()
        self.phy_signal_manager = PhysicalSignalManager.get_instance()

        if self.graphs_amount == 3:
            self.kin_thread = KinematicsThread()
            self.kin_thread.result_ready.connect(self._apply_cartesian_sim)
            self.kin_thread.start()
        else:
            self.kin_thread = None

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

    # ------------------------------------------------------------------
    # Callbacks de datos
    # ------------------------------------------------------------------
    def _mark_dirty(self):
        for motor in self.motors:
            motor.has_new_data = True
        self._schedule_render()

    def sim_angular_buffer_update(self, data):
        if self.is_paused:
            return
        data[1] *= -1
        data[2] *= -1
        for motor, value in zip(self.motors, data):
            motor.add_sim(value)
        self._mark_dirty()

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
        self._mark_dirty()

    def sim_cartesian_buffer_update(self, data):
        if self.is_paused:
            return
        angles = np.array([
            np.deg2rad(data[0]),
            np.deg2rad(-data[1]),
            np.deg2rad(-data[2]),
            np.deg2rad(data[4]),
        ])
        self.kin_thread.push_angles(angles)

    def _apply_cartesian_sim(self, pos: list):
        for motor, value in zip(self.motors, pos):
            motor.add_sim(value)
        self._mark_dirty()

    def phy_cartesian_buffer_update(self, pos_data, temp_data):
        if self.is_paused:
            return
        angles = np.array([
            np.deg2rad(pos_data[0] - 150.0),
            np.deg2rad(150.0 - pos_data[1]),
            np.deg2rad(150.0 - pos_data[2]),
            np.deg2rad(pos_data[4] - 150.0),
        ])
        _w = KinematicsWorker()
        cartesian_pos = _w.cd(angles[0], angles[1], angles[2], angles[3])
        for motor, pos_value, temp_value in zip(self.motors, cartesian_pos, temp_data):
            motor.add_phy(pos_value, temp_value)
        self._mark_dirty()

    # ------------------------------------------------------------------
    # Control de ciclo de vida
    # ------------------------------------------------------------------
    def start(self):
        self.is_paused = False

    def pause(self):
        self.is_paused = not self.is_paused

    def stop(self):
        self.is_paused = True
        if self.kin_thread is not None:
            self.kin_thread.stop()
        for motor in self.motors:
            motor.stop()
