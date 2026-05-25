"""
Modulo del worker de simulacion del brazo robotico en PyBullet.

Proporciona la clase PhysicsWorker que gestiona la actualizacion
periodica de la simulacion, la actualizacion del modelo 3D en la
interfaz y el envio de datos a las graficas.

Conexiones:
    - Conectado a SimulationSignalManager.update_pybullet_signal
      para recibir posiciones objetivo.
    - Conectado a los ticks de GlobalTimer (update_tick, model_tick,
      sync_simulation_tick) para sincronizar la simulacion.
    - Emite posiciones a traves de SimulationSignalManager
      (model_position_signal, sensor_position_signal).
"""

from PyQt6.QtCore import QThread, pyqtSignal, pyqtSlot, QElapsedTimer, QTimer
from src.services.data.signals import SimulationSignalManager
from src.services.simulation.physics_pybullet import RobotArmPhysics
from src.services.data.timers import GlobalTimer


class PhysicsWorker(QThread):
    """Worker encargado de actualizar la simulacion de PyBullet en segundo plano.

    Gestiona la sincronizacion entre las posiciones objetivo, la simulacion
    fisica y la representacion 3D mostrada en la interfaz.

    Args:
        robot_id: Identificador del robot cargado en PyBullet.
    """

    def __init__(self, robot_id) -> None:
        super().__init__()
        self.target_position = [0, 0, 0, 0, 0, 0]
        self.target_position_prev = [1, 0, 0, 0, 0, 0]
        self.physic = None
        self.timer = None
        self._running = False
        self._paused = False
        self.max_velocity = 1.2
        self.signal_manager = SimulationSignalManager.get_instance()
        self.signal_manager.update_pybullet_signal.connect(self.update_target)
        self.sync_timer = GlobalTimer.get_instance()
        self.sync_timer.update_tick.connect(self.update_simulation)
        self.sync_timer.model_tick.connect(self.update_3d_model)
        self.sync_timer.sync_simulation_tick.connect(self.update_graphs)
        self.sync_timer.start()

        self.physic = RobotArmPhysics()
        self.physic.load_models(robot_id)

    def set_max_velocity(self, max_vel):
        """Define la velocidad maxima de los motores en la simulacion.

        Args:
            max_vel (float): Velocidad maxima en radianes por segundo.
                Debe ser mayor a 0.
        """
        if max_vel > 0:
            self.max_velocity = max_vel
        else:
            print("La velocidad maxima debe ser mayor a 0, "
                  "usando la velocidad maxima por defecto: 1 rad/s")
            self.max_velocity = 1.2

    def run(self):
        """Ciclo principal del subproceso.

        Activa la simulacion y establece la velocidad maxima de los motores.
        """
        self._running = True
        self.set_max_velocity(1.2)
        if self._paused:
            self._paused = False

    def pause(self):
        """Pausa la simulacion."""
        self._running = False
        self._paused = True

    @pyqtSlot()
    def update_simulation(self):
        """Actualiza la posicion de los motores en la simulacion.

        Compara las posiciones objetivo con las previas y, si son
        diferentes, actualiza los motores. Avanza la simulacion si
        la diferencia entre objetivo y actual supera 0.0005 rad.
        """
        if self._running:
            if len(self.target_position) == len(self.physic.joint_indices):
                if not all(x == y for x, y in zip(self.target_position, self.target_position_prev)):
                    self.physic.set_joint_positions(
                        self.target_position, self.max_velocity)
                    self.target_position_prev = self.target_position
                if any(abs(x - y) >= 0.0005 for x, y in zip(self.target_position, self.physic.get_joint_positions())):
                    self.physic.step_simulation()

    @pyqtSlot()
    def update_3d_model(self):
        """Actualiza los angulos de la simulacion mostrados en el modelo 3D.

        Emite las posiciones articulares actuales al modelo 3D de la interfaz.
        """
        if self._running:
            self.signal_manager.model_position_signal.emit(
                self.physic.get_joint_positions())

    @pyqtSlot()
    def update_graphs(self):
        """Envia datos de posiciones a las graficas.

        Se ejecuta tipicamente cada 100 ms a traves del tick
        sync_simulation_tick de GlobalTimer.
        """
        if self._running:
            self.signal_manager.sensor_position_signal.emit(
                self.physic.get_joint_positions())

    @pyqtSlot(list)
    def update_target(self, target_position):
        """Actualiza los angulos objetivo de la simulacion.

        Aplica un offset de -2.617994 rad a cada posicion para
        alinear el sistema de coordenadas de la GUI con el de PyBullet.

        Args:
            target_position (list): Lista de 6 posiciones objetivo en radianes.
        """
        self.signal_manager.model_position_signal.emit(
            self.physic.get_joint_positions())
        self.target_position = [
            pos - 2.617994 for pos in target_position]
        self.update_simulation()
