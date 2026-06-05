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
    SimulationSignalManager, ConfigSignalManager
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
        config_manager.set_value(filename, *keys, value=value)
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

        # Escuchar cambios de modo
        self.sim_signals.change_mode_signal.connect(self.set_mode)
        self.phys_signals.change_mode_signal.connect(self.set_mode)

        # --- Feedback desde Servicios (Ejecucion) ---
        # Feedback de Simulacion -> Actualizacion de UI
        self.sim_signals.sensor_position_signal.connect(
            self._on_simulation_feedback)
        self.sim_signals.model_position_signal.connect(self._on_model_feedback)

        # Feedback de Robot Fisico -> Actualizacion de UI y Sincronizacion
        self.phys_signals.data_received.connect(self._on_physical_feedback)

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
