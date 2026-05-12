from PyQt6.QtCore import QThread, QObject
from PyQt6.QtGui import QVector3D


class SimulationWorker(QThread):
    """Worker thread para manejar gui del pybullet e incrustarla en la interfaz de pyqt
    """

    def __init__(self, root_object, robot_id):
        super().__init__()
        self.timer = None
        self.root_object = root_object
        self.joint_names = [
            "arm1_link_1",
            "arm2_link_1",
            "arm3_link_1",
            "arm4_link_1",
            "clamp_arm_link_1",
            "clamp2_link_1"
        ]
        self.direction_rotation = [
            "y",
            "z",
            "z",
            "y",
            "z",
            "x"
        ]
        self.colors = {
            "amarillo":  "sphereYellowPos",
            "verde": "sphereGreenPos",
            "azul": "sphereBluePos",
            "naranja": "sphereOrangePos",
            "morado": "spherePurplePos"
        }

    def update_simulation(self, joint_positions=None):
        """ Actualiza el modelo 3D de qtquick

        Args:
            joint_positions (list, optional): Posición actual de los motores en la simulación.
                                              Defaults to None.
        """
        if joint_positions is None:
            joint_positions = [0, 0, 0, 0, 0, 0]
        for i in (1, 2, 4, 5):
            joint_positions[i] *= -1
        for motor_name, angle, direction in zip(self.joint_names,
                                                joint_positions,
                                                self.direction_rotation):
            motor = self.root_object.findChild(QObject, motor_name)
            if direction == "z":
                motor.setProperty("eulerRotation", QVector3D(0, 0, angle))
            elif direction == "y":
                motor.setProperty("eulerRotation", QVector3D(0, angle, 0))
            elif direction == "x":
                motor.setProperty("eulerRotation", QVector3D(angle, 0, 0))

    def update_sphere_pose_simulation(self, poses: dict):
        for color, property_name in self.colors.items():
            if color in poses:
                pose = poses.get(color)
                if pose is not None:
                    self.root_object.setProperty(
                        property_name, QVector3D(-pose[1]-100, 100, pose[0]))
            else:
                self.root_object.setProperty(
                    property_name, QVector3D(0, 0, 0))
