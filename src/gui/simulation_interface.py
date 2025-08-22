import os
from PyQt6.QtWidgets import QVBoxLayout, QWidget
from simulation.model_physics import RobotArmPhysics


class Model3D(QWidget):
    """ Clase encargada del modelo 3d mostrado en la interfaz
    """

    def __init__(self):
        super().__init__()
        robot_path = os.path.join(os.path.dirname(
            __file__), "..", "simulation", "urdf", 'openbot_v1.urdf')
        self.physics = RobotArmPhysics(robot_path)
        if not self.layout():
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            self.setLayout(layout)

        self.layout().addWidget(self.physics.getOGLModel())
