import pybullet as p
import os
import sys
import pyqtgraph as pg
from PyQt6.QtWidgets import QApplication
from simulation.urdf_scraping import RobotURDF
from simulation.model_opengl import OpenGLRobot
from simulation.pybullet_env import SimulationEnv


class RobotArmPhysics:
    """ Establece las fisicas del modelo 3D asi como la comunicacion con el environment de pybullet,
        opengl y los datos obtenidos del urdf.
    """

    def __init__(self, urdf_path):
        super().__init__()
        self.urdf_path = urdf_path
        self.env = SimulationEnv()
        self.env.reset()
        self.__init_pybullet()
        self.urdf = RobotURDF(self.robot_id)
        links = self.urdf.get_initial_state()
        self.model_ogl = OpenGLRobot(links)

    def __init_pybullet(self):
        """Inicializar PyBullet y cargar el URDF del robot"""
        # Configurar la simulación
        p.setGravity(0, 0, -9.81)
        p.setTimeStep(1./240.)  # 240 Hz

        # Crear el suelo
        self.plane_id = p.createCollisionShape(p.GEOM_PLANE)
        self.ground_id = p.createMultiBody(0, self.plane_id)

        # Carga el modelo del robot
        self.robot_id = p.loadURDF(
            self.urdf_path,
            basePosition=[0, 0, 0],
            baseOrientation=p.getQuaternionFromEuler([0, 0, 0]),
            useFixedBase=True  # o False si el robot es móvil
        )

    def getOGLModel(self):
        return self.model_ogl.gl_widget
