""" Modulo que actúa como controlador de flujo de datos centralizado.
    Implementa el patrón Worker-Widget-Controller y actúa como un mediador reactivo.
"""
from PyQt6.QtCore import QObject, QThread, pyqtSlot, pyqtSignal
from src.services.data.signals import PhysicalSignalManager, SimulationSignalManager
from src.services.data.enums import Modes, Units, Domains
from src.services.data.timers import GlobalTimer
from src.services.data.data_worker import DataWorker
from src.services.robot import RobotController


class DataController(QObject):
    """ Clase que actúa como controlador de datos entre la interfaz y la simulación o el 
        robot físico. Actúa como un puente reactivo distribuyendo señales.
    """

    # Señal interna para solicitar procesamiento al worker
    # (data, units, mode)
    request_processing = pyqtSignal(list, object, object)

    def __init__(self, mode: Modes, unit: Units, domain: Domains, robot_controller=None) -> None:
        super().__init__()
        self._mode = mode
        self._units = unit
        self._domain = domain
        self._signal_manager = None
        self._target_data = None  # Buffer de estado para posiciones objetivo
        self._robot_controller = robot_controller

        # Inicialización del Worker y Thread
        self._worker_thread = QThread()

        # Selección del dominio y SignalManager
        if self._domain is Domains.SIMULATION:
            self._signal_manager = SimulationSignalManager.get_instance()
        elif self._domain is Domains.PHYSICAL:
            self._signal_manager = PhysicalSignalManager.get_instance()
        else:
            raise ValueError(
                f"El dominio proporcionado {self._domain} no existe.")

        self._worker = DataWorker(self._signal_manager, self._robot_controller)
        self._worker.moveToThread(self._worker_thread)
        self._worker_thread.start()

        # Conexiones de señales del Worker
        self._setup_worker_connections()

        # Temporizador de sincronización
        self._sync_timer = GlobalTimer.get_instance()
        self._sync_timer.start()
        self._setup_timer_connections()

        # Suscripción a cambios de modo globales
        self._signal_manager.change_mode_signal.connect(self.set_mode)

        # Suscripción reactiva a nuevos datos de objetivos
        self._signal_manager.update_target_signal.connect(
            self.update_target_positions)

    def _setup_worker_connections(self):
        """ Configura las conexiones entre el controlador y su worker. """
        if self._domain is Domains.SIMULATION:
            self.request_processing.connect(
                self._worker.process_simulation_data)
            self._signal_manager.sensor_position_signal.connect(
                self._worker.update_graph_data)
            self._signal_manager.model_position_signal.connect(
                self._worker.update_model_data)

        elif self._domain is Domains.PHYSICAL:
            self.request_processing.connect(self._worker.process_physical_data)
            self._signal_manager.sensor_position_signal.connect(
                self._worker.update_robot_feedback)

    def _setup_timer_connections(self):
        """ Conecta el timer de sincronización según el dominio. """
        if self._domain is Domains.SIMULATION:
            self._sync_timer.sync_simulation_tick.connect(
                self._handle_sync_tick)
        elif self._domain is Domains.PHYSICAL:
            self._sync_timer.sync_robot_tick.connect(self._handle_sync_tick)

    def start(self):
        """ Mantenido por compatibilidad con la API anterior. 
            El thread ya se inicia en el __init__.
        """
        if not self._worker_thread.isRunning():
            self._worker_thread.start()

    @pyqtSlot()
    def _handle_sync_tick(self):
        """ Maneja el tick del reloj de sincronización despachando el buffer actual. """
        if self._target_data is not None:
            self.request_processing.emit(
                self._target_data, self._units, self._mode)

    # --- Getters y Setters explícitos (Protocolo de Encapsulamiento) ---

    def get_mode(self) -> Modes:
        return self._mode

    @pyqtSlot(object)
    def set_mode(self, mode: Modes):
        self._mode = mode

    def get_units(self) -> Units:
        return self._units

    def set_units(self, units: Units):
        self._units = units

    def get_domain(self) -> Domains:
        return self._domain

    @pyqtSlot(list)
    def update_target_positions(self, data: list):
        """ 
        Punto de entrada para que las features (Sliders, Cinemática) 
        actualicen el estado deseado de forma reactiva.
        """
        self._target_data = data

    def stop(self):
        """ Detiene los hilos de ejecución. """
        self._worker_thread.quit()
        self._worker_thread.wait()
