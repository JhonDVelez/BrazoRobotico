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

from PyQt6.QtCore import QObject, pyqtSlot, QTimer
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
        self._target_data = None  # Buffer de estado para posiciones objetivo

        # Gestores de señales globales (Bus Inter-Controller)
        self.sim_signals = SimulationSignalManager.get_instance()
        self.phys_signals = PhysicalSignalManager.get_instance()
        self.pick_signals = PickPlaceSignalManager.get_instance()
        self.config_signals = ConfigSignalManager.get_instance()
        self._pick_sphere_poses = {}

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

        # --- Flujo Pick and Place ---
        # CameraController publica poses; DataController conserva el ultimo estado.
        self.pick_signals.poses_from_camera.connect(
            self._on_pick_poses_from_camera)
        self.pick_signals.pick_requested.connect(self._on_pick_requested)
        self.pick_signals.inverse_kinematics_ready.connect(
            self._on_pick_inverse_kinematics_ready)

    @pyqtSlot()
    def _handle_sync_tick(self):
        """
        Despacha las posiciones del buffer a los servicios activos en cada tick.
        """
        if self._target_data is None:
            return

        # 1. Despacho a Simulacion (Siempre activo como Digital Twin)
        # El buffer viene en formato Servo (0-300). PyBullet espera Radianes.
        # PhysicsWorker se encarga del offset interno de 150 grados (2.61 rad).
        data_rad = deg_to_rad(self._target_data)
        self.sim_signals.update_pybullet_signal.emit(data_rad.tolist())

        # 2. Despacho a Robot Fisico (Si esta conectado)
        if self.phys_signals.is_connected:
            # El robot real recibe los valores 0-300 directamente
            self.phys_signals.send_to_robot.emit(self._target_data)

    # --- Slots de Procesamiento Lógico ---

    @pyqtSlot(list)
    def update_target_positions(self, data: list):
        """Actualiza el buffer de estado central."""
        self._target_data = data

    @pyqtSlot(object)
    def set_mode(self, mode: Modes):
        """Cambia el modo de operacion global."""
        self._mode = mode

    @staticmethod
    def _relative_to_servo(positions: list) -> list:
        """
        Convierte angulos relativos de UI a posiciones absolutas de servo.
        """
        return [float(value + 150.0) for value in positions]

    @staticmethod
    def _with_gripper(status: list, gripper_degrees: float) -> list:
        """Copia un objetivo y establece la pinza en grados relativos."""
        updated = list(status)
        updated[-1] = float(gripper_degrees + 150.0)
        return updated

    def _schedule_target(self, delay_ms: int, status: list):
        """Programa un objetivo para el buffer central del DataController."""
        QTimer.singleShot(
            delay_ms,
            lambda target=list(status): self.update_target_positions(target)
        )

    @pyqtSlot(dict)
    def _on_pick_poses_from_camera(self, poses: dict):
        """
        Guarda la ultima pose 3D detectada por color para Pick and Place.
        """
        self._pick_sphere_poses.update(poses)

    @pyqtSlot(str)
    def _on_pick_requested(self, color: str):
        """
        Inicia el flujo de Pick and Place para la esfera seleccionada.
        """
        sphere_pose = self._pick_sphere_poses.get(color)
        if not sphere_pose or 'position' not in sphere_pose:
            return

        x, y, z = sphere_pose['position']
        self.sim_signals.release_sphere.emit(color)
        self.sim_signals.change_mode_signal.emit(Modes.KINEMATIC)
        self.pick_signals.inverse_kinematics_requested.emit({
            'color': color,
            'coords': {'x': y, 'y': x, 'z': z+10},
            'gripper_degrees': -112
        })

    @pyqtSlot(dict)
    def _on_pick_inverse_kinematics_ready(self, result: dict):
        """
        Ejecuta la secuencia Pick and Place cuando llega el objetivo IK.
        """
        pick_open = result.get('target')
        if not pick_open:
            return

        home_neutral = self._relative_to_servo([0, 0, 0, 0, 90, 0])
        home_open = self._with_gripper(home_neutral, -112)
        pick_closed = self._with_gripper(pick_open, 7)
        home_closed = self._relative_to_servo([0, 0, 0, 0, 90, 7])

        self._schedule_target(0, home_neutral)
        self._schedule_target(900, home_open)
        self._schedule_target(2400, pick_open)
        self._schedule_target(4200, pick_closed)
        self._schedule_target(5600, home_closed)

    @pyqtSlot(list)
    def _on_simulation_feedback(self, actual_positions: list):
        """Procesa feedback de la simulacion para graficos."""
        # PyBullet envia radianes, graficos usan grados
        pos_deg = rad_to_deg(actual_positions)
        self.sim_signals.update_graph_signal.emit(pos_deg)

    @pyqtSlot(list, dict)
    def _on_model_feedback(self, motor_positions, sphere_positions):
        """Procesa feedback de la simulacion para el modelo 3D."""
        pos_deg = rad_to_deg(motor_positions)
        self.sim_signals.update_robot_signal.emit(pos_deg)
        self.sim_signals.sphere_pos_from_pybullet.emit(sphere_positions)

    @pyqtSlot(list, list)
    def _on_physical_feedback(self, actual_positions: list, temperatures: list):
        """Procesa feedback del robot real para sincronizar sistema."""
        # El robot envia grados. Sincronizamos graficos.
        self.phys_signals.update_graph_signal.emit(actual_positions)

        # OPCIONAL: Sincronizar simulación con el estado real del robot
        # if sync_mode:
        #     self.sim_signals.update_pybullet_signal.emit(deg_to_rad(actual_positions))
