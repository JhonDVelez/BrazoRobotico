"""
Modulo que actua como controlador de flujo de datos centralizado (Cerebro).

Implementa la logica de negocio y orquestacion, actuando como un mediador reactivo
entre los controladores de interfaz (Features) y los controladores de ejecucion
(Servicios de Simulacion y Robot).

Reglas de Arquitectura:
    - Instancia unica gestionada por MainWindow.
    - Se comunica con otros controladores exclusivamente via SignalManagers.
    - No tiene acceso directo a Workers o Widgets ajenos.
"""

import math
from PyQt6.QtCore import QObject, pyqtSlot
from src.services.data import config_manager
from src.services.data.signals import (
    PhysicalSignalManager, PickPlaceSignalManager,
    SimulationSignalManager, ConfigSignalManager,
    CameraSignalManager, SlidersSignalManager, KinematicsSignalManager,
    SearchSignalManager
)
from src.services.data.enums import Modes, Units
from src.services.data.timers import GlobalTimer
from src.services.data.utils import deg_to_rad, rad_to_deg


class DataController(QObject):
    """
    Orquestador central del flujo de datos del sistema.

    Mantiene el estado global del robot (Digital Twin) y coordina la 
    sincronizacion entre la entrada del usuario, la simulacion fisica 
    y el hardware real.
    """

    _config_initialized = False

    def __init__(self) -> None:
        """
        Inicializa el DataController unico.
        """
        super().__init__()
        self._mode = Modes.SLIDERS
        self._units = Units.RAD
        self._target_data = None
        self._last_feedback = None
        self._TARGET_TOLERANCE = 3.0

        # Gestores de señales globales (Bus Inter-Controller)
        self.sim_signals = SimulationSignalManager.get_instance()
        self.phys_signals = PhysicalSignalManager.get_instance()
        self.pick_signals = PickPlaceSignalManager.get_instance()
        self.config_signals = ConfigSignalManager.get_instance()
        self.cam_signals = CameraSignalManager.get_instance()
        self.sliders_signals = SlidersSignalManager.get_instance()
        self.kin_signals = KinematicsSignalManager.get_instance()
        self.search_signals = SearchSignalManager.get_instance()

        # Inicialización de configuración (una sola vez)
        if not DataController._config_initialized:
            self._load_initial_config()
            self.config_signals.change_requested.connect(
                self._on_config_change_requested)
            DataController._config_initialized = True

        self._setup_global_connections()

        # Temporizador de sincronizacion centralizado
        self._sync_timer = GlobalTimer.get_instance()
        self._sync_timer.start()
        self._sync_timer.sync_simulation_tick.connect(self._handle_sync_tick)
        self._sync_timer.sync_robot_tick.connect(self._handle_sync_tick)

    def _load_initial_config(self):
        """Carga la configuracion persistente."""
        config_manager.init_config()
        for filename in config_manager.DEFAULTS.keys():
            data = config_manager.load(filename)
            self.config_signals.set_all_config(filename, data)

    @pyqtSlot(str, list, object)
    def _on_config_change_requested(self, filename: str, keys: list, value: object):
        """Persiste cambios de configuracion."""
        config_manager.set_value(filename, keys, value)
        self.config_signals.update_param(filename, keys, value)

    def _setup_global_connections(self):
        """
        Configura el ruteo de señales entre controladores.
        """
        # --- Entradas desde Features (UI) ---
        # Escuchar actualizaciones de objetivo desde cualquier dominio
        self.sim_signals.update_target_signal.connect(
            self.update_target_positions)
        self.phys_signals.update_target_signal.connect(
            self.update_target_positions)
        self.sliders_signals.update_target_signal.connect(
            self.update_target_positions)
        self.kin_signals.update_target_signal.connect(
            self.update_target_positions)

        # Escuchar cambios de modo
        self.sim_signals.change_mode_signal.connect(self.set_mode)
        self.phys_signals.change_mode_signal.connect(self.set_mode)
        self.sliders_signals.change_mode_signal.connect(self.set_mode)
        self.kin_signals.change_mode_signal.connect(self.set_mode)

        # --- Feedback desde Servicios (Ejecucion) ---
        # Feedback de Simulacion -> Actualizacion de UI
        self.sim_signals.sensor_position_signal.connect(
            self._on_simulation_feedback)
        self.sim_signals.model_position_signal.connect(self._on_model_feedback)

        # Feedback de Robot Fisico -> Actualizacion de UI y Sincronizacion
        self.phys_signals.data_received.connect(self._on_physical_feedback)

        # Bridge Pick and Place -> Simulation
        self.pick_signals.release_sphere_request.connect(
            self.sim_signals.release_sphere.emit)
        self.pick_signals.reattach_sphere_request.connect(
            self.sim_signals.reattach_sphere.emit)

        # Bridge Pick and Place -> Search (control de busqueda de esferas)
        self.pick_signals.search_circle_request.connect(
            self.search_signals.set_circle)

        # Bridge cinematica inversa: Pick and Place <-> Kinematics.
        # Ninguna feature conoce a la otra; el DataController media el dialogo.
        self.pick_signals.inverse_kinematics_requested.connect(
            self.kin_signals.inverse_kinematics_requested.emit)
        self.kin_signals.inverse_kinematics_ready.connect(
            self.pick_signals.inverse_kinematics_ready.emit)

        # Bridge Camera (vision) -> Simulation / Pick and Place
        self.cam_signals.clear_spheres_request.connect(
            self.sim_signals.clear_spheres.emit)
        self.cam_signals.poses_from_camera.connect(
            self.sim_signals.sphere_pos_from_camera.emit)
        self.cam_signals.poses_from_camera.connect(
            self.pick_signals.poses_from_camera.emit)
        self.cam_signals.spheres_detected_2d.connect(
            self.pick_signals.spheres_detected_2d.emit)

        # Bridge Simulation Control
        self.sim_signals.start_request.connect(self.sim_signals.start_simulation.emit)
        self.sim_signals.pause_request.connect(self.sim_signals.pause_simulation.emit)
        self.sim_signals.stop_request.connect(self.sim_signals.stop_simulation.emit)

        # Bridge Robot Control
        self.phys_signals.start_request.connect(self.phys_signals.start_service.emit)
        self.phys_signals.stop_request.connect(self.phys_signals.stop_service.emit)

    @pyqtSlot()
    def _handle_sync_tick(self):

        """Despacha posiciones y detecta llegada al objetivo."""
        if self._target_data is None:
            return

        data_rad = deg_to_rad(self._target_data)
        self.sim_signals.update_pybullet_signal.emit(data_rad.tolist())

        
        if self.phys_signals.is_connected:
            self.phys_signals.send_to_robot.emit(self._target_data)

        if self._last_feedback is not None:
            feedback = [-x+150 if i in (4, 5) else x+150 for i,
                        x in enumerate(self._last_feedback)]
            # print(f'target {self._target_data}')
            # print(f'feedback rad {feedback}')
            if all(
                abs(self._target_data[i] - feedback[i])
                < self._TARGET_TOLERANCE
                for i in range(min(len(self._target_data),
                                   len(feedback)))
            ):
                self.pick_signals.target_reached.emit(feedback)
                self._last_feedback = None

    # --- Slots de Procesamiento Lógico ---

    @pyqtSlot(list)
    def update_target_positions(self, data: list):
        """Actualiza el buffer de estado central."""
        self._target_data = data

    @pyqtSlot(object)
    def set_mode(self, mode: Modes):
        """Cambia el modo de operacion global."""
        self._mode = mode

    @pyqtSlot(list)
    def _on_simulation_feedback(self, actual_positions: list):
        """Procesa feedback de la simulacion para graficos y target_reached."""
        pos_deg = rad_to_deg(actual_positions)
        self.sim_signals.update_graph_signal.emit(pos_deg)
        if not self.phys_signals.is_connected:
            self._last_feedback = pos_deg

    @pyqtSlot(list, dict)
    def _on_model_feedback(self, motor_positions, sphere_positions):
        """Procesa feedback de la simulacion para el modelo 3D."""
        pos_deg = rad_to_deg(motor_positions)
        self.sim_signals.update_robot_signal.emit(pos_deg)
        self.sim_signals.sphere_pos_from_pybullet.emit(sphere_positions)

    @pyqtSlot(list, list)
    def _on_physical_feedback(self, actual_positions: list, temperatures: list):
        """Procesa feedback del robot real para sincronizar sistema."""
        self.phys_signals.update_graph_signal.emit(actual_positions)
        self._last_feedback = actual_positions
