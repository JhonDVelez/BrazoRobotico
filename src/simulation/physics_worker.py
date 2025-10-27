from PyQt6.QtCore import QThread, QTimer, pyqtSignal, pyqtSlot
from data import SimulationSignalManager
from .physics_pybullet import RobotArmPhysics


class PhysicsWorker(QThread):
    """ Worker encargado de actualizar la simulation de pybullet
    """

    update_model = pyqtSignal(list)

    def __init__(self, robot_id) -> None:
        super().__init__()
        self.target_position_prev = [1, 0, 0, 0, 0, 0]
        self.model_ogl = None
        self.physic = None
        self.timer = None
        self._running = False
        self._paused = False
        self.max_velocity = None
        self.signal_manager = SimulationSignalManager.get_instance()
        self.signal_manager.update_pybullet_signal.connect(
            self.update_simulation)

        self.physic = RobotArmPhysics()
        self.physic.robot_loaded.connect(self.get_data)
        self.physic.load_models(robot_id)

    def set_max_velocity(self, max_vel):
        """ Define la velocidad maxima de los motores en la simulación

        Args:
            max_vel (float): velocidad maxima en radianes por segundo
        """
        if max_vel > 0:
            self.max_velocity = max_vel
        else:
            print("La velocidad maxima debe ser mayor a 0, "
                  "usando la velocidad maxima por defecto: 1 rad/s")
            self.max_velocity = 1.2

    def run(self):
        """ Ciclo principal del subproceso el cual actualiza el robot cada n milisegundos
        """
        self._running = True
        self.set_max_velocity(5.5)
        # Si esta pausado actualiza activa nuevamente el ciclo
        if self._paused:
            self._paused = False

        self.get_data()

    def pause(self):
        """Pausa la simulación"""
        self._running = False
        self._paused = True

    def stop(self):
        """Detener la simulación"""
        self.physic.reset_simulation()
        self._running = False
        self._paused = False

    def get_data(self):
        """ Emite una señal que solicita datos de posición de los motores a la interfaz
        """
        self.signal_manager.get_data_signal.emit()

    @pyqtSlot(list)
    def update_simulation(self, target_positions):
        """ Actualización de la posición de los motores del robot
        """
        # Compara si la cantidad de posiciones ingresadas es igual a la cantidad de uniones del
        # robot
        target_positions = [
            pos - 2.6179938779914944 for pos in target_positions]
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
                # Actualiza la simulation si la diferencia entre los ángulos objetivos y los ángulos
                # actuales es mayor o igual a 0.01 rad o 0.573°
                if any(abs(x - y) >= 0.01 for x, y in zip(target_positions, actual_positions)):
                    self.physic.step_simulation()
                QTimer.singleShot(16, self.get_data)
