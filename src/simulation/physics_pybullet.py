import os
import pybullet as p
import pybullet_data
from simulation.pybullet_env import SimulationEnv


class RobotArmPhysics:
    """ Establece las fisicas del modelo 3D asi como la comunicacion con el environment de pybullet,
        opengl y los datos obtenidos del urdf.
    """

    def __init__(self, urdf_path):
        """ Inicializa la clase RobotArmPhysics definiendo variables e iniciando el env de pybullet

        Args:
            urdf_path (str): Direccion absoluta del archivo urdf
            gui (bool, optional): Define si se muestra la gui de pybullet. Defaults to False.
        """

        self.joint_indices = []
        self.joint_names = []
        self.joint_positions = []
        self.joint_velocities = []
        self.initial_states = []

        self.urdf_path = urdf_path
        self.__init_pybullet()

    def __init_pybullet(self):
        """Inicializar PyBullet y cargar el URDF del robot"""
        self.env = SimulationEnv()
        self.env.reset()

        # Configurar la simulación
        p.setGravity(0, 0, -9.81)
        p.setTimeStep(1./240.)  # 240 Hz
        p.configureDebugVisualizer(p.COV_ENABLE_MOUSE_PICKING, 0)
        p.configureDebugVisualizer(p.COV_ENABLE_RENDERING, 1)
        p.configureDebugVisualizer(p.COV_ENABLE_WIREFRAME, 0)
        p.configureDebugVisualizer(
            p.COV_ENABLE_GUI, 0, lightPosition=[-10, 10, 10])

        p.setAdditionalSearchPath(pybullet_data.getDataPath())

        p.resetDebugVisualizerCamera(
            cameraDistance=0.6,
            cameraYaw=20,
            cameraPitch=-40,
            cameraTargetPosition=[0.2, 0., 0.1]
        )

        # Crear el suelo
        self.plane_id = p.createCollisionShape(p.GEOM_PLANE)
        self.ground_id = p.createMultiBody(0, self.plane_id)

        # Carga el modelo del robot
        self.robot_id = p.loadURDF(
            self.urdf_path,
            basePosition=[0, 0, 0],
            baseOrientation=p.getQuaternionFromEuler([0, 0, 0]),
            useFixedBase=True,  # o False si el robot es móvil
            flags=p.URDF_USE_INERTIA_FROM_FILE | p.URDF_USE_SELF_COLLISION
        )

        # Obtener información de las articulaciones
        num_joints = p.getNumJoints(self.robot_id)

        for i in range(num_joints):
            joint_info = p.getJointInfo(self.robot_id, i)
            joint_name = joint_info[1].decode('utf-8')
            joint_type = joint_info[2]

            # Solo considerar articulaciones móviles (revolute o prismatic)
            if joint_type in [p.JOINT_REVOLUTE, p.JOINT_PRISMATIC]:
                self.joint_indices.append(i)
                self.joint_names.append(joint_name)

        texture = p.loadTexture(os.path.join(os.path.dirname(
            __file__), "meshes", "visual", "texture", "base_link.png"))
        p.changeVisualShape(self.robot_id, 0, textureUniqueId=texture)

    def get_robot_id(self) -> int:
        """ Obtiene el id del robot del motor de fisicas de pybullet
        """
        if self.robot_id:
            return self.robot_id

    def get_joint_positions(self):
        """Obtiene el estado actual de todas las articulaciones"""

        return [p.getJointState(self.robot_id, 1)[0],
                p.getJointState(self.robot_id, 2)[0],
                p.getJointState(self.robot_id, 3)[0],
                p.getJointState(self.robot_id, 4)[0],
                p.getJointState(self.robot_id, 5)[0],
                p.getJointState(self.robot_id, 6)[0]]

    def set_initial_states(self, initital_states):
        self.initial_states = initital_states

    def set_joint_positions(self, positions, max_velocity=0.5):
        """Establece las posiciones objetivo de las articulaciones"""
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
        """Avanza un paso de la simulación"""
        p.stepSimulation()
