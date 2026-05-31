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
from src.services.simulation.physics_pybullet import RobotArmPhysics


class PhysicsWorker(QThread):
    """Worker encargado de actualizar la simulacion de PyBullet en segundo plano.

    Gestiona la sincronizacion entre las posiciones objetivo, la simulacion
    fisica y la representacion 3D mostrada en la interfaz.

    Args:
        robot_id: Identificador del robot cargado en PyBullet.
    """

    # Señales locales para comunicación con el controlador
    # (Evita el uso de SignalManagers globales en el worker)
    model_updated = pyqtSignal(list, dict)
    sensor_updated = pyqtSignal(list)

    def __init__(self, robot_id) -> None:
        super().__init__()
        self.target_position = [0, 0, 0, 0, 0, 0]
        self.target_position_prev = [1, 0, 0, 0, 0, 0]
        self.physic = None
        self.timer = None
        self._running = False
        self._paused = False
        self.max_velocity = 1.2

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
                is_moving = any(
                    abs(x - y) >= 0.000001
                    for x, y in zip(self.target_position, self.physic.get_joint_positions())
                )
                if is_moving or self.physic.has_released_spheres():
                    self.physic.step_simulation()

    @pyqtSlot()
    def update_3d_model(self):
        """Actualiza los angulos de la simulacion mostrados en el modelo 3D.

        Emite las posiciones articulares actuales al modelo 3D de la interfaz.
        """
        if self._running:
            self.model_updated.emit(
                self.physic.get_joint_positions(), self.physic.get_sphere_position())

    @pyqtSlot()
    def update_graphs(self):
        """Envia datos de posiciones a las graficas.

        Se ejecuta tipicamente cada 100 ms a traves del tick
        sync_simulation_tick de GlobalTimer.
        """
        if self._running:
            self.sensor_updated.emit(
                self.physic.get_joint_positions())

    @pyqtSlot(list)
    def update_target(self, target_position):
        """Actualiza los angulos objetivo de la simulacion.

        Aplica un offset de -2.617994 rad a cada posicion para
        alinear el sistema de coordenadas de la GUI con el de PyBullet.

        Args:
            target_position (list): Lista de 6 posiciones objetivo en radianes.
        """
        self.model_updated.emit(
            self.physic.get_joint_positions(), self.physic.get_sphere_position())
        # print(f'on sim {self.target_position}')
        self.target_position = [
            pos - 2.617994 for pos in target_position]
        self.update_simulation()

    def update_sphere_initial_positions(self, poses: dict):
        self.physic.update_spheres(poses)

    @pyqtSlot(str)
    def release_sphere(self, color: str):
        """
        Libera una esfera para que PyBullet deje de recibir poses de camara.

        Args:
            color (str): Identificador de la esfera seleccionada.
        """
        self.physic.release_sphere(color)
