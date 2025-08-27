import numpy as np
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
        p.configureDebugVisualizer(p.COV_ENABLE_MOUSE_PICKING, 1)
        p.configureDebugVisualizer(p.COV_ENABLE_RENDERING, 1)
        p.configureDebugVisualizer(p.COV_ENABLE_WIREFRAME, 0)
        p.configureDebugVisualizer(
            p.COV_ENABLE_GUI, 0, lightPosition=[10, 0, 10])

        p.setAdditionalSearchPath(pybullet_data.getDataPath())

        p.resetDebugVisualizerCamera(
            cameraDistance=0.5,
            cameraYaw=200,
            cameraPitch=-20,
            cameraTargetPosition=[0., 0., 0.2]
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

    def get_robot_id(self):
        """ Obtiene el id del robot del motor de fisicas de pybullet
        """
        if self.robot_id:
            return self.robot_id

    def get_link_states(self):
        """Obtiene el estado actual de todas las articulaciones"""
        if self.robot_id is None:
            return []

        joint_states = p.getLinkStates(self.robot_id, self.joint_indices)
        links_transform_matrix = []

        for i, state in enumerate(joint_states):
            position = np.array(self.initial_states[i]["position"]) - state[0]
            # print(
            #     f"link name: {self.initial_states[i]["link"]} initial: {np.array(self.initial_states[i]["position"])}, actual {state[0]}")
            orientation = np.array(state[1])
            rotation_matrix = p.getMatrixFromQuaternion(orientation)
            rotation_matrix = np.array(rotation_matrix).reshape(3, 3)
            transform_matrix = np.eye(4)
            transform_matrix[:3, :3] = rotation_matrix
            transform_matrix[:3, 3] = position
            links_transform_matrix.append(transform_matrix)
        return links_transform_matrix

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

    def get_end_effector_pose(self):
        """Obtiene la pose del end-effector"""
        if self.robot_id is None:
            return None, None

        # Asume que el end-effector es el último link
        num_joints = len(self.joint_indices)
        if num_joints > 0:
            link_state = p.getLinkState(self.robot_id, self.joint_indices[-1])
            position = link_state[0]
            orientation = link_state[1]
            return position, orientation
        return None, None

    def step_simulation(self):
        """Avanza un paso de la simulación"""
        p.stepSimulation()

    def reset_robot(self):
        """Resetea el robot a posición inicial"""
        if self.robot_id is None:
            return

        # Posición inicial (todas las articulaciones en 0)
        initial_positions = [0.0] * len(self.joint_indices)
        self.set_joint_positions(initial_positions)

        # Esperar a que se estabilice
        for _ in range(100):
            self.step_simulation()

    def get_joint_limits(self):
        """Obtiene los límites de las articulaciones"""
        if self.robot_id is None:
            return []

        limits = []
        for joint_idx in self.joint_indices:
            joint_info = p.getJointInfo(self.robot_id, joint_idx)
            lower_limit = joint_info[8]
            upper_limit = joint_info[9]
            limits.append((lower_limit, upper_limit))

    # def disconnect(self):
    #     """Desconecta de PyBullet"""
    #     p.disconnect()
