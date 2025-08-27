import numpy as np
from PyQt6.QtCore import QThread, QTimer
from simulation.physics_pybullet import RobotArmPhysics
from gui.sliders_interface import SlidersWidget


class PhysicsWorker(QThread):
    """ Worker encargado de actualizar la simulacion de pybullet """

    def __init__(self, controller, robot_path) -> None:
        super().__init__()
        self.controller = controller
        self.model_ogl = None
        self.physic = RobotArmPhysics(robot_path)
        self.timer = None

    def get_robot_id(self):
        return self.physic.get_robot_id()

    def set_model_instance(self, model_ogl):
        self.model_ogl = model_ogl

    def set_initial_states(self, initial_states):
        self.physic.set_initial_states(initial_states)

    def run(self):
        """Se ejecuta al iniciar el QThread"""
        self.timer = QTimer()
        self.timer.setInterval(4)  # 4ms 250 Hz
        self.timer.timeout.connect(self.update_simulation)
        self.timer.start()
        self.exec()

    def update_simulation(self):
        """Un paso de simulación"""
        print("update")
        max_velocity = 1

        target_positions = self.position_rad()
        if len(target_positions) <= len(self.physic.joint_indices):
            self.physic.set_joint_positions(target_positions, max_velocity)

        self.physic.get_link_states()
        # Avanzar simulación
        self.physic.step_simulation()

    def position_rad(self):
        pos = SlidersWidget.get_sliders_state()
        if pos is None:
            pos = []
        return np.deg2rad(np.array(pos))
