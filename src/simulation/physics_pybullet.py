import os
import pybullet as p
import pybullet_data
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget


class RobotArmPhysics(QWidget):
    """ Establece las fisicas del modelo 3D asi como la comunicacion con el environment de pybullet,
        opengl y los datos obtenidos del urdf.
    """
    robot_loaded = pyqtSignal()

    def __init__(self):
        """ Inicializa la clase RobotArmPhysics definiendo variables e iniciando el env de pybullet

        Args:
            gui (bool, optional): Define si se muestra la gui de pybullet. Defaults to False.
        """
        super().__init__()
        self.joint_indices = []
        self.joint_names = []
        self.joint_positions = []
        self.joint_velocities = []
        self.initial_states = []
        self.robot_id = None

    def get_robot_id(self) -> int:
        """ Obtiene el id del robot del motor de fisicas de pybullet
        """
        if self.robot_id:
            return self.robot_id

    def get_joint_positions(self):
        """ Obtiene el estado actual de todas las articulaciones
        """

        return [p.getJointState(self.robot_id, 1)[0],
                p.getJointState(self.robot_id, 2)[0],
                p.getJointState(self.robot_id, 3)[0],
                p.getJointState(self.robot_id, 4)[0],
                p.getJointState(self.robot_id, 5)[0],
                p.getJointState(self.robot_id, 6)[0]]

    def set_joint_positions(self, positions, max_velocity=0.5):
        """ Establece las posiciones objetivo de las articulaciones
        """
        if self.robot_id is None or len(positions) != len(self.joint_indices):
            return

        for i, pos in enumerate(positions):
            p.setJointMotorControl2(
                bodyUniqueId=self.robot_id,
                jointIndex=self.joint_indices[i],
                controlMode=p.POSITION_CONTROL,
                targetPosition=pos,
                maxVelocity=max_velocity,
                force=500
            )

    def step_simulation(self):
        """ Avanza un paso de la simulación
        """
        p.stepSimulation()

    def load_models(self, robot_id):
        """ Carga nuevamente el modelo a partir del URDF y crea el plano
        """
        self.robot_id = robot_id

        self.get_robot_info()
        self.robot_loaded.emit()

    def get_robot_info(self):
        """ Obtiene informacion del robot principalmente los indices de cada junta
        """
        # Obtener información de las articulaciones
        num_joints = p.getNumJoints(self.robot_id)

        for i in range(num_joints):
            joint_type = p.getJointInfo(self.robot_id, i)[2]

            # Solo considerar articulaciones móviles (revolute o prismatic)
            if joint_type in [p.JOINT_REVOLUTE, p.JOINT_PRISMATIC]:
                self.joint_indices.append(i)

    def reset_simulation(self):
        """ Borra los modelos del robot y el suelo para quitar la carga grafica por completo.
        """
        p.resetJointState(self.robot_id, 1, 0)
        p.resetJointState(self.robot_id, 2, 0)
        p.resetJointState(self.robot_id, 3, 0)
        p.resetJointState(self.robot_id, 4, 0)
        p.resetJointState(self.robot_id, 5, 0)
        p.resetJointState(self.robot_id, 6, 0)
