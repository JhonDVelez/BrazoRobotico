"""
Modulo de acoplamiento con el motor de fisicas PyBullet.

Proporciona la clase RobotArmPhysics que gestiona la carga del
modelo URDF, el control de las articulaciones y la ejecucion
de los pasos de simulacion.

Conexiones:
    - Utilizado por PhysicsWorker para controlar la simulacion.
    - Emite robot_loaded cuando termina de cargar el modelo URDF.
"""

import pybullet as p
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget


class RobotArmPhysics(QWidget):
    """Establece las fisicas del modelo 3D y la comunicacion con PyBullet.

    Gestiona el entorno de PyBullet/OpenGL, la carga del modelo URDF,
    el control posicional de las articulaciones y la obtencion de
    sus estados.

    Signals:
        robot_loaded (pyqtSignal): Se emite cuando el modelo URDF se
            ha cargado completamente.
    """

    def __init__(self):
        """Inicializa la clase y prepara las variables de articulaciones.

        Args:
            gui (bool, optional): Define si se muestra la GUI de PyBullet.
                Por defecto False.
        """
        super().__init__()
        self.joint_indices = []
        self.joint_names = []
        self.joint_positions = []
        self.robot_id = None

    def get_robot_id(self) -> int:
        """Obtiene el ID del robot en el motor de fisicas de PyBullet.

        Returns:
            int: Identificador del robot en la simulacion.
        """
        if self.robot_id:
            return self.robot_id

    def get_joint_positions(self):
        """Obtiene el estado actual de todas las articulaciones.

        Returns:
            list: Lista de 6 posiciones articulares en radianes.
        """
        return [p.getJointState(self.robot_id, 1)[0],
                p.getJointState(self.robot_id, 2)[0],
                p.getJointState(self.robot_id, 3)[0],
                p.getJointState(self.robot_id, 4)[0],
                p.getJointState(self.robot_id, 5)[0],
                p.getJointState(self.robot_id, 6)[0]]

    def set_joint_positions(self, positions, max_velocity=1.2):
        """Establece las posiciones objetivo de las articulaciones.

        Args:
            positions (list): Lista de posiciones objetivo en radianes.
            max_velocity (float, optional): Velocidad maxima (rad/s).
                Por defecto 1.2.
        """
        if self.robot_id is None or len(positions) != len(self.joint_indices):
            return
        positions[-2:] = [-x for x in positions[-2:]]
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
        """Avanza un paso de la simulacion en PyBullet."""
        p.stepSimulation()

    def load_models(self, robot_id):
        """Carga el modelo a partir del URDF y crea el plano.

        Args:
            robot_id (int): Identificador del robot cargado.
        """
        self.robot_id = robot_id
        self.get_robot_info()

    def get_robot_info(self):
        """Obtiene informacion del robot, principalmente los indices de cada junta.

        Recorre todas las articulaciones del modelo y almacena los
        indices de aquellas que son moviles (revolute o prismatic).
        """
        num_joints = p.getNumJoints(self.robot_id)
        for i in range(num_joints):
            joint_type = p.getJointInfo(self.robot_id, i)[2]
            if joint_type in [p.JOINT_REVOLUTE, p.JOINT_PRISMATIC]:
                self.joint_indices.append(i)
