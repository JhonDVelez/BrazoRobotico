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
from PyQt6.QtCore import pyqtSignal, QDir
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

        sphere_visual_path = QDir(
            "pybullet:/meshes/visual/sphere.obj").path()
        sphere_collision_path = QDir(
            "pybullet:/meshes/collision/sphere_vhacd.obj").path()
        self.spheres = {}
        self.released_spheres = set()
        self.col_id = p.createCollisionShape(
            shapeType=p.GEOM_MESH, fileName=sphere_collision_path, meshScale=[1, 1, 1])
        self.vis_id = p.createVisualShape(
            shapeType=p.GEOM_MESH, fileName=sphere_visual_path, meshScale=[1, 1, 1], rgbaColor=[1, 0.5, 0, 1])

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
        p.setCollisionFilterGroupMask(self.robot_id, -1, 1, 1)
        for joint_index in range(p.getNumJoints(self.robot_id)):
            p.setCollisionFilterGroupMask(self.robot_id, joint_index, 1, 1)

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

    def update_spheres(self, poses: dict):
        for color, pose in poses.items():
            if color in self.released_spheres:
                continue

            # Extraer la posicion si viene en un diccionario
            pos_list = pose.get('position') if isinstance(pose, dict) else pose

            if color in self.spheres:
                self.set_sphere_position(self.spheres.get(color), pos_list)
            else:
                self.create_sphere(color, pos_list)

    def create_sphere(self, color, posicion):
        # Convertir mm a metros y mapear ejes
        x, y, z = posicion
        pos = [y * 0.001, x * 0.001, z * 0.001]

        body_id = p.createMultiBody(
            baseMass=0.05,
            baseCollisionShapeIndex=self.col_id,
            baseVisualShapeIndex=self.vis_id,
            basePosition=pos
        )

        self.spheres[color] = body_id
        p.changeDynamics(
            body_id,
            -1,
            lateralFriction=0.3,
            restitution=0.5,
            contactStiffness=40000.0,
            contactDamping=50.0
        )
        p.setCollisionFilterGroupMask(body_id, -1, 1, 1)
        return body_id

    def get_sphere_position(self):
        sphere_state = {}
        for color, id in self.spheres.items():
            position, orientation = p.getBasePositionAndOrientation(id)
            # Mapeo inverso: Metros a mm y swap de ejes para UI
            pos = [
                -position[0] * 1000,  # UI_X = Py_X
                position[2] * 1000,  # UI_Y = Py_Z Hacia arriba
                position[1] * 1000  # UI_Z = Py_Y
            ]
            # print(f'get: {pos}')
            rot = p.getEulerFromQuaternion(orientation)
            rot = [
                rot[0],
                rot[2],
                rot[1]
            ]
            sphere_state[color] = {
                'position': pos, 'orientation': p.getEulerFromQuaternion(orientation)}
        return sphere_state

    def set_sphere_position(self, id, new_pos):
        # Asegurar que sea una lista de coordenadas
        position = new_pos.get('position') if isinstance(
            new_pos, dict) else new_pos

        y, x, z = position
        # Convertir mm a metros y mapear ejes: UI(x,y,z) -> PyBullet(y,x,z)
        pos = [(x+100) * 0.001, y * 0.001, (z+101) * 0.001]
        # print(f'set: {pos}')
        p.resetBasePositionAndOrientation(
            id, pos, [0, 0, 0, 1])
        # p.changeDynamics(id, -1, mass=0.0)

    def release_sphere(self, color):
        """
        Interrumpe el seguimiento por camara de una esfera para usar fisica real.

        Args:
            color (str): Clave de color de la esfera a liberar.
        """
        if color not in self.spheres:
            return
        self.released_spheres.add(color)
        # p.changeDynamics(self.spheres[color], -1, mass=0.05)
        p.setCollisionFilterGroupMask(self.spheres[color], -1, 1, 1)

    def has_released_spheres(self):
        """
        Indica si hay esferas liberadas que requieren avanzar la fisica.

        Returns:
            bool: True si al menos una esfera fue liberada.
        """
        return bool(self.released_spheres)

    def hide_sphere(self, id):
        self.set_sphere_position(id, [0, 0, 0])
        p.setCollisionFilterGroupMask(id, -1, 0, 0)

    def show_sphere(self, id, new_pos):
        self.set_sphere_position(id, new_pos)
        p.setCollisionFilterGroupMask(id, -1, 1, 1)
