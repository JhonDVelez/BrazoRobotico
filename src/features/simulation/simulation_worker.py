"""
Módulo que gestiona la actualización visual del modelo 3D en QtQuick.

Este módulo contiene la clase SimulationWorker, la cual actúa como un puente
entre los datos cinemáticos/físicos y las propiedades de los objetos 3D
definidos en el motor gráfico de Qt (QML/Quick3D).
"""

from PyQt6.QtCore import QThread, QObject
from PyQt6.QtGui import QVector3D, QQuaternion


class SimulationWorker(QThread):
    """
    Worker thread encargado de la sincronización visual del robot y su entorno.

    Manipula dinamicamente las propiedades de eulerRotation de los eslabones
    y las posiciones de las esferas detectadas en la escena 3D.
    """

    def __init__(self, root_object, robot_id):
        """
        Inicializa el worker con el objeto raíz de la escena QML.

        Args:
            root_object (QObject): Referencia al objeto 'root' del cargador QML.
            robot_id (str): Identificador único del robot.
        """
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
        self._motor_objects = {}
        for name in self.joint_names:
            motor = self.root_object.findChild(QObject, name)
            self._motor_objects[name] = motor

        self.colors = {
            "amarillo":  ["sphereYellowPos", "sphereYellowRot"],
            "verde": ["sphereGreenPos", "sphereGreenRot"],
            "azul": ["sphereBluePos", "sphereBlueRot"],
            "naranja": ["sphereOrangePos", "sphereOrangeRot"],
            "morado": ["spherePurplePos", "spherePurpleRot"]
        }

    def update_simulation(self, joint_positions=None):
        """
        Actualiza los ángulos de rotación de cada eslabón en el modelo 3D.

        Args:
            joint_positions (list, optional): Lista de 6 ángulos en grados.
                Defaults to None (posicion cero).
        """
        if joint_positions is None:
            joint_positions = [0, 0, 0, 0, 0, 0]
        for i in (1, 2, 4, 5):
            joint_positions[i] *= -1
        for motor_name, angle, direction in zip(self.joint_names,
                                                joint_positions,
                                                self.direction_rotation):
            motor = self._motor_objects.get(motor_name)
            if motor is not None:
                if direction == "z":
                    motor.setProperty("eulerRotation", QVector3D(0, 0, angle))
                elif direction == "y":
                    motor.setProperty("eulerRotation", QVector3D(0, angle, 0))
                elif direction == "x":
                    motor.setProperty("eulerRotation", QVector3D(angle, 0, 0))

    def update_sphere_radius(self, radius):
        """
        Actualiza el radio de las esferas en la escena QML.

        Args:
            radius (float): Nuevo radio en mm.
        """
        self.root_object.setProperty("sphereRadius", float(radius))

    def update_sphere_pose_simulation(self, poses: dict):
        """
        Actualiza la posición visual de las esferas de color en la escena 3D.

        Args:
            poses (dict): Diccionario {color: dict} con coordenadas y orientacion.
        """
        for color, properties in self.colors.items():
            pos_prop, rot_prop = properties
            if color in poses:
                data = poses.get(color, {})
                pose = data.get('position')
                orientation = data.get('orientation')

                if pose is not None:
                    # Mapeo de coordenadas cartesianas al espacio local de la escena QML
                    # UI(x,y,z) -> QML(x, y_up, z)
                    self.root_object.setProperty(
                        pos_prop, QVector3D(pose[0], pose[1], pose[2]))

                if orientation is not None and len(orientation) == 4:
                    # PyBullet entrega [x, y, z, w]. QQuaternion espera (w, x, y, z)
                    quat = QQuaternion(
                        orientation[3],
                        orientation[0],
                        orientation[1],
                        orientation[2]
                    )
                    self.root_object.setProperty(rot_prop, quat)
            else:
                # Ocultar o resetear esferas no detectadas
                self.root_object.setProperty(pos_prop, QVector3D(0, 0, 0))
