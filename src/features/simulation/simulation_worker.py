"""
Modulo que gestiona la actualizacion visual del modelo 3D en QtQuick.

Este modulo contiene la clase SimulationWorker, la cual actua como un puente
entre los datos cinematicos/fisicos y las propiedades de los objetos 3D
definidos en el motor grafico de Qt (QML/Quick3D).
"""

from PyQt6.QtCore import QThread, QObject
from PyQt6.QtGui import QVector3D


class SimulationWorker(QThread):
    """
    Worker thread encargado de la sincronizacion visual del robot y su entorno.

    Manipula dinamicamente las propiedades de eulerRotation de los eslabones
    y las posiciones de las esferas detectadas en la escena 3D.
    """

    def __init__(self, root_object, robot_id):
        """
        Inicializa el worker con el objeto raiz de la escena QML.

        Args:
            root_object (QObject): Referencia al objeto 'root' del cargador QML.
            robot_id (str): Identificador unico del robot.
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
        self.colors = {
            "amarillo":  "sphereYellowPos",
            "verde": "sphereGreenPos",
            "azul": "sphereBluePos",
            "naranja": "sphereOrangePos",
            "morado": "spherePurplePos"
        }

    def update_simulation(self, joint_positions=None):
        """
        Actualiza los angulos de rotacion de cada eslabon en el modelo 3D.

        Args:
            joint_positions (list, optional): Lista de 6 angulos en grados.
                Defaults to None (posicion cero).
        """
        if joint_positions is None:
            joint_positions = [0, 0, 0, 0, 0, 0]
        for i in (1, 2, 4, 5):
            joint_positions[i] *= -1
        for motor_name, angle, direction in zip(self.joint_names,
                                                joint_positions,
                                                self.direction_rotation):
            motor = self.root_object.findChild(QObject, motor_name)
            if motor is not None:
                if direction == "z":
                    motor.setProperty("eulerRotation", QVector3D(0, 0, angle))
                elif direction == "y":
                    motor.setProperty("eulerRotation", QVector3D(0, angle, 0))
                elif direction == "x":
                    motor.setProperty("eulerRotation", QVector3D(angle, 0, 0))

    def update_sphere_pose_simulation(self, poses: dict):
        """
        Actualiza la posicion visual de las esferas de color en la escena 3D.

        Args:
            poses (dict): Diccionario {color: [x, y, z]} con coordenadas en mm.
        """
        for color, property_name in self.colors.items():
            if color in poses:
                pose = poses.get(color, {}).get('position', (0, 0, 0))
                if pose is not None:
                    # Mapeo de coordenadas cartesianas al espacio local de la escena QML
                    self.root_object.setProperty(
                        property_name, QVector3D(-pose[1], 100, pose[0]))
            else:
                # Ocultar o resetear esferas no detectadas
                self.root_object.setProperty(
                    property_name, QVector3D(0, 0, 0))
