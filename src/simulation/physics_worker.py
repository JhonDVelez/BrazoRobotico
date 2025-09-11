from PyQt6.QtCore import QThread, QTimer, pyqtSlot
from simulation.physics_pybullet import RobotArmPhysics
from data.control_utils import SimulationSignalManager


class PhysicsWorker(QThread):
    """ Worker encargado de actualizar la simulacion de pybullet """

    def __init__(self) -> None:
        super().__init__()
        self.target_position_prev = [1, 0, 0, 0, 0, 0]
        self.model_ogl = None
        self.physic = None
        self.timer = None
        self._running = True
        self._paused = False
        self.max_velocity = None
        self.physic = RobotArmPhysics(1)
        self.physic.robot_loaded.connect(self.get_data)
        self.signal_manager = SimulationSignalManager.get_instance()
        self.signal_manager.update_pybullet_signal.connect(
            self.update_simulation)

    def set_max_velocity(self, max_vel):
        if max_vel > 0:
            self.max_velocity = max_vel
        else:
            print("La velocidad maxima debe ser mayor a 0, "
                  "usando la velocidad maxima por defecto: 1 rad/s")
            self.max_velocity = 1.0

    def run(self):
        """ Ciclo principal del subproceso el cual actualiza el robot cada n milisegundos 
        """
        self._running = True
        # Si esta pausado actualiza activa nuevamente el ciclo
        if self._paused:
            self._paused = False
            self.get_data()
        # Pero si esta detenido vuelve a cargar el modelo.
        else:
            self.physic.load_models()

    def pause(self):
        """Pausa la simulación"""
        self._running = False
        self._paused = True

    def stop(self):
        """Detener la simulación"""
        self._running = False
        self._paused = False
        self.physic.reset_simulation()

    def get_data(self):
        self.signal_manager.get_data_signal.emit()

    @pyqtSlot(list)
    def update_simulation(self, target_positions):
        """ Actualizacion de la posicion de los motores del robot
        """
        # Compara si la cantidad de posiciones ingresadas es igual a la cantidad de uniones del
        # robot
        if self._running:
            if len(target_positions) == len(self.physic.joint_indices):
                actual_positions = self.physic.get_joint_positions()
                self.signal_manager.actual_position_signal.emit(
                    actual_positions)
                # Relaciona las posiciones de los array y los compara entre si en caso de que sean
                # diferentes actualiza las posiciones objetivo
                if not all(x == y for x, y in zip(target_positions, self.target_position_prev)):
                    self.physic.set_joint_positions(
                        target_positions, self.max_velocity)
                    self.target_position_prev = target_positions
                # Actualiza la simulacion si la diferencia entre los angulos objetivos y los angulos
                # actuales es mayor o igual a 0.01 rad o 0.573°
                if any(abs(x - y) >= 0.01 for x, y in zip(target_positions, actual_positions)):
                    self.physic.step_simulation()

                QTimer.singleShot(4, self.get_data)
