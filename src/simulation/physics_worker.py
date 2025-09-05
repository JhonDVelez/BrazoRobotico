import numpy as np
from PyQt6.QtCore import QThread, QTimer
from numpy.typing import NDArray
from simulation.physics_pybullet import RobotArmPhysics
from gui.sliders_interface import SlidersWidget


class PhysicsWorker(QThread):
    """ Worker encargado de actualizar la simulacion de pybullet """

    def __init__(self) -> None:
        super().__init__()
        self.target_position_prev = [1, 0, 0, 0, 0, 0]
        self.model_ogl = None
        self.physic = None
        self.timer = None
        self.max_velocity = None

    def get_robot_id(self):
        """ Obtiene el numero de identificacion del robot en la simulacion de pybullet.

        Returns:
            : _description_
        """
        return self.physic.get_robot_id()

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
        if self.physic is None:
            self.physic = RobotArmPhysics(1)
        self._running = True
        self.set_max_velocity(1.0)
        self.update_simulation()

    def pause(self):
        """Pausa la simulación"""
        self._running = False

    def stop(self):
        """Detener la simulación"""
        self._running = False
        self.physic.reset_joint_positions()
        self.set_max_velocity(1.0)

    def update_simulation(self):
        """ Actualizacion de la posicion de los motores del robot
        """
        target_positions = self.get_position_rad()
        # Compara si la cantidad de posiciones ingresadas es igual a la cantidad de uniones del
        # robot
        if self._running:
            if len(target_positions) == len(self.physic.joint_indices):
                actual_positions = self.physic.get_joint_positions()
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
                QTimer.singleShot(4, self.update_simulation)

    def get_position_rad(self) -> NDArray:
        """ Obtiene los valores objetivos de los slider/spinBox y los convierte a radianes

        Returns:
            NDArray: Array de valores objetivos en radianes
        """
        pos = SlidersWidget.get_sliders_state()
        if pos is None:
            pos = []
        return np.deg2rad(np.array(pos))
