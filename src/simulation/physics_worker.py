from PyQt6.QtCore import QThread, pyqtSignal, pyqtSlot, QElapsedTimer, QTimer
from data import SimulationSignalManager
from .physics_pybullet import RobotArmPhysics
from data import GlobalTimer


class PhysicsWorker(QThread):
    """ Worker encargado de actualizar la simulation de pybullet
    """

    def __init__(self, robot_id) -> None:
        super().__init__()
        self.target_position = [0, 0, 0, 0, 0, 0]
        self.target_position_prev = [1, 0, 0, 0, 0, 0]
        self.model_ogl = None
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
        self.sync_timer.start()

        self.physic = RobotArmPhysics()
        self.physic.load_models(robot_id)

        # Timer para debug de tiempo de sincronización
        # self._elapsed = QElapsedTimer()
        # self._elapsed.start()

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
        self.set_max_velocity(1.2)
        # Si esta pausado actualiza activa nuevamente el ciclo
        if self._paused:
            self._paused = False

    def pause(self):
        """Pausa la simulación"""
        self._running = False
        self._paused = True

    @pyqtSlot()
    def update_simulation(self):
        """ Actualización de la posición de los motores del robot
        """
        # Compara si la cantidad de posiciones ingresadas es igual a la cantidad de uniones del
        # robot
        if self._running:
            if len(self.target_position) == len(self.physic.joint_indices):
                # Relaciona las posiciones de los array y los compara entre si en caso de que sean
                # diferentes actualiza las posiciones objetivo
                if not all(x == y for x, y in zip(self.target_position, self.target_position_prev)):
                    self.physic.set_joint_positions(
                        self.target_position, self.max_velocity)
                    self.target_position_prev = self.target_position
                # Actualiza la simulation si la diferencia entre los ángulos objetivos y los ángulos
                # actuales es mayor o igual a 0.01 rad o 0.573°
                if any(abs(x - y) >= 0.001 for x, y in zip(self.target_position, self.physic.get_joint_positions())):
                    self.physic.step_simulation()

    @pyqtSlot()
    def update_3d_model(self):
        """ Actualiza los ángulos de la simulación que se muestran en el modelo 3d de la interfaz.
        """
        # print(self._elapsed.restart())  # Mostrar cada cuanto se entra en la función
        if self._running:
            self.signal_manager.model_position_signal.emit(
                self.physic.get_joint_positions())

    @pyqtSlot(list)
    def update_target(self, target_position):
        """ Actualiza los ángulos objetivos de la simulación y envía datos al modelo 3D y las 
            gráficas

        Args:
            target_position (list): Lista de 6 posiciones con los ángulos objetivos en radianes
        """
        # print(self._elapsed.restart()) # Mostrar cada cuanto se entra en la función
        # Envia datos al modelo 3D y la grafica
        self.signal_manager.sensor_position_signal.emit(
            self.physic.get_joint_positions())

        self.target_position = [
            pos - 2.617994 for pos in target_position]

        self.update_simulation()
