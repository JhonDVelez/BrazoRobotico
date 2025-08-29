import numpy as np
from PyQt6.QtCore import QThread, QTimer
from numpy.typing import NDArray
from simulation.physics_pybullet import RobotArmPhysics
from gui.sliders_interface import SlidersWidget


class PhysicsWorker(QThread):
    """ Worker encargado de actualizar la simulacion de pybullet """

    def __init__(self, controller, robot_path) -> None:
        super().__init__()
        self.controller = controller
        self.target_position_prev = [1, 0, 0, 0, 0, 0]
        self.model_ogl = None
        self.physic = RobotArmPhysics(robot_path)
        self.timer = None
        self.max_velocity = None

    def get_robot_id(self):
        """ Obtiene el numero de identificacion del robot en la simulacion de pybullet.

        Returns:
            : _description_
        """
        return self.physic.get_robot_id()

    def set_model_instance(self, model_ogl):
        self.model_ogl = model_ogl

    def set_initial_states(self, initial_states):
        self.physic.set_initial_states(initial_states)

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
        self.timer = QTimer()
        self.timer.setInterval(4)  # 4ms 250 Hz
        self.timer.timeout.connect(self.update_simulation)
        self.timer.start()
        self.exec()

    def update_simulation(self):
        """ Actualizacion de la posicion de los motores del robot
        """
        target_positions = self.get_position_rad()
        # print(target_positions)
        if len(target_positions) <= len(self.physic.joint_indices):
            actual_positions = self.physic.get_joint_positions()
            if not all(x == y for x, y in zip(target_positions, self.target_position_prev)):
                self.physic.set_joint_positions(
                    target_positions, self.max_velocity)
                self.target_position_prev = target_positions
            if not all(abs(x - y) < 0.01 for x, y in zip(target_positions, actual_positions)):
                self.physic.step_simulation()

    def get_position_rad(self) -> NDArray:
        """ Obtiene los valores objetivos de los slider/spinBox y los convierte a radianes

        Returns:
            NDArray: Array de valores objetivos en radianes
        """
        pos = SlidersWidget.get_sliders_state()
        if pos is None:
            pos = []
        return np.deg2rad(np.array(pos))
