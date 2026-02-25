import pybullet as p
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget


class RobotArmPhysics(QWidget):
    """ Establece las físicas del modelo 3D asi como la comunicación con el environment de pybullet,
        opengl y los datos obtenidos del urdf.
        Funciona como la interfaz de bajo nivel entre los comandos de Python y el motor de física.
    """
    # Señal emitida cuando el robot ha sido cargado exitosamente en el entorno de física
    robot_loaded = pyqtSignal()

    def __init__(self):
        """ Inicializa la clase RobotArmPhysics definiendo variables e iniciando el env de pybullet

        Args:
            gui (bool, optional): Define si se muestra la gui de pybullet. Defaults to False.
        """
        super().__init__()
        # Listas para almacenar metadatos de las articulaciones (Joints)
        self.joint_indices = []
        self.joint_names = []
        self.joint_positions = []
        self.joint_velocities = []
        self.initial_states = []
        # Identificador único del robot dentro del servidor de PyBullet
        self.robot_id = None

    def get_robot_id(self) -> int:
        """ Obtiene el id del robot del motor de físicas de pybullet.
            Es esencial para que otras funciones sepan a qué objeto aplicar fuerzas o movimientos.
        """
        if self.robot_id:
            return self.robot_id

    def get_joint_positions(self):
        """ Obtiene el estado angular/lineal actual de todas las articulaciones del robot.
            Extrae específicamente el valor de la posición (índice 0 del estado de la junta).
        """

        return [p.getJointState(self.robot_id, 1)[0],
                p.getJointState(self.robot_id, 2)[0],
                p.getJointState(self.robot_id, 3)[0],
                p.getJointState(self.robot_id, 4)[0],
                p.getJointState(self.robot_id, 5)[0],
                p.getJointState(self.robot_id, 6)[0]]

    def set_joint_positions(self, positions, max_velocity=1.2):
        """ Establece las posiciones objetivo de las articulaciones utilizando control por posición.
            Aplica un lazo de control interno para mover el robot hacia el ángulo deseado.
        """
        # Validación: El robot debe existir y el número de posiciones debe coincidir con los motores
        if self.robot_id is None or len(positions) != len(self.joint_indices):
            return

        for i, pos in enumerate(positions):
            # Configura el motor de cada articulación
            p.setJointMotorControl2(
                bodyUniqueId=self.robot_id,
                jointIndex=self.joint_indices[i],
                controlMode=p.POSITION_CONTROL, # Modo de control de posición
                targetPosition=pos,             # Ángulo o desplazamiento objetivo
                maxVelocity=max_velocity,        # Límite de velocidad del motor
                force=500                       # Fuerza/Torque máximo aplicado para el movimiento
            )

    def step_simulation(self):
        """ Avanza un paso de la simulación física (normalmente 1/240 segundos).
            Es necesario llamar a esta función para que los cálculos de setJointMotorControl2 se ejecuten.
        """
        p.stepSimulation()

    def load_models(self, robot_id):
        """ Configura el ID del robot y dispara la recolección de información del modelo.
        """
        self.robot_id = robot_id

        self.get_robot_info()
        self.robot_loaded.emit()

    def get_robot_info(self):
        """ Obtiene información del robot directamente del servidor de física, 
            identificando qué articulaciones son móviles para ignorar las fijas.
        """
        # Consulta cuántas articulaciones (fijas y móviles) tiene el modelo URDF cargado
        num_joints = p.getNumJoints(self.robot_id)

        for i in range(num_joints):
            # Obtiene el tipo de articulación (revolute, prismatic, fixed, etc.)
            joint_type = p.getJointInfo(self.robot_id, i)[2]

            # Solo considerar articulaciones móviles (rotacionales o prismáticas)
            if joint_type in [p.JOINT_REVOLUTE, p.JOINT_PRISMATIC]:
                self.joint_indices.append(i)

    def reset_simulation(self):
        """ Reinicia el estado de las articulaciones a su posición cero (Home).
            A diferencia de setJointMotorControl2, esto teletransporta las juntas sin aplicar física.
        """
        p.resetJointState(self.robot_id, 1, 0)
        p.resetJointState(self.robot_id, 2, 0)
        p.resetJointState(self.robot_id, 3, 0)
        p.resetJointState(self.robot_id, 4, 0)
        p.resetJointState(self.robot_id, 5, 0)
        p.resetJointState(self.robot_id, 6, 0)