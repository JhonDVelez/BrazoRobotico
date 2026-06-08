"""
Modulo de acoplamiento con el motor de fisicas PyBullet.

Proporciona la clase RobotArmPhysics que gestiona la carga del
modelo URDF, el control de las articulaciones y la ejecucion
de los pasos de simulacion.

Conexiones:
    - Utilizado por PhysicsWorker para controlar la simulacion.
    - Emite robot_loaded cuando termina de cargar el modelo URDF.
"""

import math
import pybullet as p
from PyQt6.QtCore import pyqtSignal, QDir
from PyQt6.QtWidgets import QWidget
from src.services.data.signals import ConfigSignalManager


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
        self.missing_counters = {}

        self.sphere_visual_path = sphere_visual_path
        self.sphere_collision_path = sphere_collision_path
        self.col_id = None
        self.vis_id = None

        # Inicializar con el radio por defecto (20mm)
        self.update_sphere_scale(20.0)

    def update_sphere_scale(self, radius_mm: float):
        """
        Actualiza el tamaño de las esferas en PyBullet.

        Args:
            radius_mm (float): Nuevo radio en mm.
        """
        scale = radius_mm / 20.0
        mesh_scale = [scale, scale, scale]

        # Crear nuevas formas de colision y visuales
        self.col_id = p.createCollisionShape(
            shapeType=p.GEOM_MESH,
            fileName=self.sphere_collision_path,
            meshScale=mesh_scale
        )
        self.vis_id = p.createVisualShape(
            shapeType=p.GEOM_MESH,
            fileName=self.sphere_visual_path,
            meshScale=mesh_scale,
            rgbaColor=[1, 0.5, 0, 1]
        )

        # Si ya existen esferas, debemos recrearlas o actualizar su forma
        # En PyBullet no es trivial cambiar la forma de un cuerpo existente,
        # lo mas seguro es eliminarlas y dejar que update_spheres las recree
        if hasattr(self, 'spheres') and self.spheres:
            for color, body_id in list(self.spheres.items()):
                p.removeBody(body_id)
            self.spheres.clear()
            self.missing_counters.clear()
            # Las esferas liberadas tambien deben ser recreadas si es posible,
            # pero por ahora las removemos para evitar inconsistencias fisicas.
            self.released_spheres.clear()

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
        """
        Actualiza las posiciones de las esferas segun las detecciones de la camara.

        Si una esfera no se detecta durante 5 frames seguidos, se oculta.
        Las esferas en proceso de pick and place (released) se ignoran.

        Args:
            poses (dict): Diccionario {color: posicion_o_dict}.
        """
        detected_colors = set(poses.keys())

        for color, pose in poses.items():
            if color in self.released_spheres:
                continue

            # Reiniciar contador si se detecta
            self.missing_counters[color] = 0

            # Extraer la posicion si viene en un diccionario
            pos_list = pose.get('position') if isinstance(pose, dict) else pose

            if color in self.spheres:
                self.show_sphere(self.spheres.get(color), pos_list)
            else:
                self.create_sphere(color, pos_list)

        # Incrementar contadores para esferas no detectadas
        for color in list(self.spheres.keys()):
            if color not in detected_colors and color not in self.released_spheres:
                self.missing_counters[color] = self.missing_counters.get(
                    color, 0) + 1
                if self.missing_counters[color] >= 5:
                    self.hide_sphere(self.spheres[color])

    def hide_all_spheres(self):
        """Oculta todas las esferas de la simulacion inmediatamente."""
        for color, body_id in self.spheres.items():
            if color not in self.released_spheres:
                self.hide_sphere(body_id)
                self.missing_counters[color] = 5

    def create_sphere(self, color, posicion):
        # Mapeo mm a metros alineado con UI rotada 180
        # Py_X = UI_X, Py_Y = -UI_Z, Py_Z = UI_Y
        x, y, z = posicion
        pos = [y * 0.001, x * 0.001, z * 0.001]

        # Calcular masa proporcional al volumen (base 20mm -> 0.05kg)
        radius = ConfigSignalManager.get_instance().get_param(
            "camera.json", "sphere_radius", default=20.0)
        mass = 0.05 * (radius / 20.0)**3

        body_id = p.createMultiBody(
            baseMass=mass,
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
            contactDamping=50.0,
            collisionMargin=0.000001
        )
        p.setCollisionFilterGroupMask(body_id, -1, 1, 1)
        return body_id

    def get_sphere_position(self):
        sphere_state = {}
        for color, id in self.spheres.items():
            position, orientation = p.getBasePositionAndOrientation(id)
            # Mapeo inverso: Metros a mm y swap de ejes para UI
            # UI(x,y,z) -> PyBullet(-x,z,y)
            pos = [
                position[0] * 1000,  # UI_X = -Py_X
                position[2] * 1000,  # UI_Y = Py_Z (Vertical)
                -position[1] * 1000   # UI_Z = Py_Y
            ]

            # Mapeo de cuaternion (x, y, z, w) siguiendo el cambio de base
            quat = [
                orientation[0],  # UI_qx = -Py_qx
                orientation[2],  # UI_qy = Py_qz
                -orientation[1],  # UI_qz = Py_qy
                orientation[3]   # w se mantiene
            ]

            sphere_state[color] = {
                'position': pos, 'orientation': quat}
        return sphere_state

    def set_sphere_position(self, id, new_pos):
        # Asegurar que sea una lista de coordenadas
        position = new_pos.get('position') if isinstance(
            new_pos, dict) else new_pos

        y, x, z = position
        # Convertir mm a metros y mapear ejes: UI(x,y,z) -> PyBullet(y,x,z)
        pos = [(x+100) * 0.001, y * 0.001, (z+102.3) * 0.001]
        # print(f'set: {pos}')
        p.resetBasePositionAndOrientation(
            id, pos, [0, 0, 0, 1])

    def release_sphere(self, color):
        """
        Interrumpe el seguimiento por camara de una esfera para usar fisica real.

        Args:
            color (str): Clave de color de la esfera a liberar.
        """
        if color not in self.spheres:
            return
        self.released_spheres.add(color)
        p.setCollisionFilterGroupMask(self.spheres[color], -1, 1, 1)

    def reattach_sphere(self, color):
        """
        Reanuda el seguimiento por camara de una esfera.

        Args:
            color (str): Clave de color de la esfera a reasociar.
        """
        if color in self.released_spheres:
            self.released_spheres.remove(color)

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
