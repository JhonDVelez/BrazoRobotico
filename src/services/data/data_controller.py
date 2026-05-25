"""
Modulo que actua como controlador de flujo de datos centralizado.

Implementa el patron Worker-Widget-Controller y actua como un mediador reactivo
entre los componentes de la interfaz (Features) y los servicios de ejecucion
(Simulacion o Robot Fisico).

Conexiones:
    - Escucha `update_target_signal` de `SimulationSignalManager` o `PhysicalSignalManager`.
    - Escucha ticks de `GlobalTimer` para sincronizacion.
    - Despacha procesamiento al `DataWorker` mediante `request_processing`.
"""

import numpy as np
from PyQt6.QtCore import QObject, QThread, pyqtSlot, pyqtSignal
from src.services.data.signals import PhysicalSignalManager, SimulationSignalManager
from src.services.data.enums import Modes, Units, Domains
from src.services.data.timers import GlobalTimer
from src.services.data.utils import deg_to_rad, rad_to_deg


class DataController(QObject):
    """
    Controlador de datos entre la interfaz y la ejecucion (Simulacion/Robot).

    Actua como un puente reactivo distribuyendo señales y gestionando el ciclo
    de vida del `DataWorker` en un hilo separado.

    Attributes:
        request_processing (pyqtSignal): Señal interna para solicitar
            procesamiento al worker. Envia (data, units, mode).
    """

    # Señal interna para solicitar procesamiento al worker
    # (data, units, mode)
    request_processing = pyqtSignal(list, object, object)

    def __init__(self, mode: Modes, unit: Units, domain: Domains, robot_controller=None) -> None:
        """
        Inicializa el DataController y configura el entorno de ejecucion.

        Args:
            mode (Modes): Modo de operacion inicial (Manual, Cinematico, etc.).
            unit (Units): Unidades de medida (Grados, Radianes, etc.).
            domain (Domains): Dominio de ejecucion (SIMULATION o PHYSICAL).
            robot_controller (RobotController, optional): Controlador del robot fisico.

        Raises:
            ValueError: Si el dominio proporcionado no es valido.
        """
        super().__init__()
        self._mode = mode
        self._units = unit
        self._domain = domain
        self._signal_manager = None
        self._target_data = None  # Buffer de estado para posiciones objetivo
        self._robot_controller = robot_controller

        # Seleccion del dominio y SignalManager
        if self._domain is Domains.SIMULATION:
            self._signal_manager = SimulationSignalManager.get_instance()
        elif self._domain is Domains.PHYSICAL:
            self._signal_manager = PhysicalSignalManager.get_instance()
        else:
            raise ValueError(
                f"El dominio proporcionado {self._domain} no existe.")

        # Conexiones de señales del Worker
        self._setup_connections()

        # Temporizador de sincronizacion
        self._sync_timer = GlobalTimer.get_instance()
        self._sync_timer.start()
        self._setup_timer_connections()

        # Suscripcion a cambios de modo globales
        self._signal_manager.change_mode_signal.connect(self.set_mode)

        # Suscripcion reactiva a nuevos datos de objetivos
        self._signal_manager.update_target_signal.connect(
            self.update_target_positions)

    def _setup_connections(self):
        """
        Configura las conexiones entre el controlador y su worker segun el dominio.
        """
        if self._domain is Domains.SIMULATION:
            self.request_processing.connect(
                self.process_simulation_data)
            self._signal_manager.sensor_position_signal.connect(
                self.update_graph_data)
            self._signal_manager.model_position_signal.connect(
                self.update_model_data)

        elif self._domain is Domains.PHYSICAL:
            self.request_processing.connect(self.process_physical_data)
            self._signal_manager.sensor_position_signal.connect(
                self.update_robot_feedback)

    def _setup_timer_connections(self):
        """
        Conecta el timer de sincronizacion segun el dominio activo.
        """
        if self._domain is Domains.SIMULATION:
            self._sync_timer.sync_simulation_tick.connect(
                self._handle_sync_tick)
        elif self._domain is Domains.PHYSICAL:
            self._sync_timer.sync_robot_tick.connect(self._handle_sync_tick)

    @pyqtSlot()
    def _handle_sync_tick(self):
        """
        Maneja el tick de sincronizacion despachando el buffer de datos actual.
        """
        if self._target_data is not None:
            self.request_processing.emit(
                self._target_data, self._units, self._mode)

    # --- Getters y Setters explicitos (Protocolo de Encapsulamiento) ---

    def get_mode(self) -> Modes:
        """
        Obtiene el modo de operacion actual.

        Returns:
            Modes: Modo activo.
        """
        return self._mode

    @pyqtSlot(object)
    def set_mode(self, mode: Modes):
        """
        Establece un nuevo modo de operacion.

        Args:
            mode (Modes): Nuevo modo a aplicar.
        """
        self._mode = mode

    def get_units(self) -> Units:
        """
        Obtiene las unidades de medida actuales.

        Returns:
            Units: Unidades activas.
        """
        return self._units

    def set_units(self, units: Units):
        """
        Establece las unidades de medida.

        Args:
            units (Units): Nuevas unidades.
        """
        self._units = units

    def get_domain(self) -> Domains:
        """
        Obtiene el dominio de ejecucion actual.

        Returns:
            Domains: Dominio activo (SIMULATION o PHYSICAL).
        """
        return self._domain

    @pyqtSlot(list)
    def update_target_positions(self, data: list):
        """
        Actualiza el buffer de posiciones objetivo de forma reactiva.

        Punto de entrada para que las Features (Sliders, Cinematica)
        actualicen el estado deseado.

        Args:
            data (list): Lista de nuevas posiciones objetivo.
        """
        self._target_data = data

    @pyqtSlot(list, object, object)
    def process_simulation_data(self, data, unit, mode):
        """
        Procesa datos destinados exclusivamente a la simulacion.

        Args:
            data (list): Vector de posiciones.
            unit (Units): Unidad de entrada.
            mode (Modes): Modo de control activo.
        """
        if data is None:
            return

        # Convertir a radianes para PyBullet si vienen en grados
        if unit is Units.RAD:
            processed_data = deg_to_rad(data)
        else:
            processed_data = np.array(data)

        self._signal_manager.update_pybullet_signal.emit(processed_data)

    @pyqtSlot(list, object, object)
    def process_physical_data(self, data, unit, mode):
        """
        Procesa datos destinados al robot fisico y sincroniza la simulacion.

        Args:
            data (list): Vector de posiciones deseado.
            unit (Units): Unidad de entrada.
            mode (Modes): Modo de control activo.
        """
        if data is None:
            return

        # El robot físico usualmente recibe grados, pero validamos
        if unit is Units.RAD:
            data_deg = rad_to_deg(data)
        else:
            data_deg = np.array(data)

        # Enviar al robot físico mediante el controlador serial
        if self._robot_controller:
            self._robot_controller.move_to(data_deg.tolist())

        # También actualizamos la simulación para que refleje el movimiento del robot
        # PyBullet usa radianes internamente
        data_rad = deg_to_rad(data_deg)
        self._signal_manager.update_pybullet_signal.emit(data_rad)

    @pyqtSlot(list)
    def update_graph_data(self, actual_positions):
        """
        Adapta posiciones recibidas para la actualizacion de graficos de tiempo real.

        Args:
            actual_positions (list): Posiciones en radianes.
        """
        # PyBullet envía radianes, los gráficos usan grados para el usuario
        pos_deg = rad_to_deg(actual_positions)
        self._signal_manager.update_graph_signal.emit(pos_deg)

    @pyqtSlot(list)
    def update_model_data(self, actual_positions):
        """
        Adapta posiciones para la actualizacion del modelo visual 3D (Quick3D).

        Args:
            actual_positions (list): Posiciones en radianes.
        """
        # PyBullet envía radianes, el modelo visual usa grados
        pos_deg = rad_to_deg(actual_positions)
        self._signal_manager.update_robot_signal.emit(pos_deg)

    @pyqtSlot(list)
    def update_robot_feedback(self, actual_positions):
        """
        Canaliza el feedback recibido desde el hardware fisico hacia el sistema.

        Args:
            actual_positions (list): Posiciones reales en grados.
        """
        # Reenvía los datos recibidos para que otros componentes los consuman reactivamente
        self._signal_manager.data_received.emit(actual_positions, [])
