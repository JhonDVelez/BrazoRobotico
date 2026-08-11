"""
Módulo que gestiona la actualización visual del modelo 3D en QtQuick.

Este módulo contiene la clase SimulationWorker, la cual actúa como un puente
entre los datos cinemáticos/físicos y las propiedades de los objetos 3D
definidos en el motor gráfico de Qt (QML/Quick3D), implementando throttling
y seguridad de hilos.
"""

from PyQt6.QtCore import QObject, QTimer, pyqtSlot
from PyQt6.QtGui import QVector3D, QQuaternion


class SimulationWorker(QObject):
    """
    Worker encargado de la sincronización visual del robot y su entorno
    de forma thread-safe y optimizada mediante throttling.
    """

    def __init__(self, root_object, robot_id):
        """
        Inicializa el worker con el objeto raíz de la escena QML.

        Args:
            root_object (QObject): Referencia al objeto 'root' del cargador QML.
            robot_id (str): Identificador único del robot.
        """
        super().__init__()
        self.root_object = root_object
        self.robot_id = robot_id
        self._pending_positions = None

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
            "amarillo":  ["sphereYellowPos", "sphereYellowRot"],
            "verde": ["sphereGreenPos", "sphereGreenRot"],
            "azul": ["sphereBluePos", "sphereBlueRot"],
            "naranja": ["sphereOrangePos", "sphereOrangeRot"],
            "morado": ["spherePurplePos", "spherePurpleRot"]
        }

        # Timer para throttling (60 FPS / ~16ms) para evitar saturar el loop principal y congelamientos
        self.throttle_timer = QTimer(self)
        self.throttle_timer.setInterval(16)
        self.throttle_timer.timeout.connect(self._process_pending_update)

    def start(self):
        if not self.throttle_timer.isActive():
            self.throttle_timer.start()

    def quit(self):
        if self.throttle_timer.isActive():
            self.throttle_timer.stop()

    def isRunning(self):
        return self.throttle_timer.isActive()

    def wait(self, msecs=None):
        pass

    @pyqtSlot(list)
    def update_simulation(self, joint_positions=None):
        """
        Actualiza los ángulos de rotación de cada eslabón en el modelo 3D (con buffering / throttling).
        """
        if joint_positions is None:
            joint_positions = [0, 0, 0, 0, 0, 0]
        self._pending_positions = list(joint_positions)

    def _process_pending_update(self):
        """Procesa la última posición pendiente de forma segura en el hilo GUI."""
        if self._pending_positions is None or self.root_object is None:
            return

        joint_positions = self._pending_positions
        self._pending_positions = None

        pos_copy = list(joint_positions)
        for i in (4, 5):
            if i < len(pos_copy):
                pos_copy[i] *= -1

        for motor_name, angle, direction in zip(self.joint_names,
                                                pos_copy,
                                                self.direction_rotation):
            motor = self.root_object.findChild(QObject, motor_name)
            if motor is not None:
                if direction == "z":
                    motor.setProperty("eulerRotation", QVector3D(0, 0, angle))
                elif direction == "y":
                    motor.setProperty("eulerRotation", QVector3D(0, angle, 0))
                elif direction == "x":
                    motor.setProperty("eulerRotation", QVector3D(angle, 0, 0))

    @pyqtSlot(float)
    def update_sphere_radius(self, radius):
        """
        Actualiza el radio de las esferas en la escena QML.
        """
        if self.root_object:
            self.root_object.setProperty("sphereRadius", float(radius))

    @pyqtSlot(dict)
    def update_sphere_pose_simulation(self, poses: dict):
        """
        Actualiza la posición visual de las esferas de color en la escena 3D.
        """
        if self.root_object is None:
            return
        for color, properties in self.colors.items():
            pos_prop, rot_prop = properties
            if color in poses:
                data = poses.get(color, {})
                pose = data.get('position')
                orientation = data.get('orientation')

                if pose is not None:
                    self.root_object.setProperty(
                        pos_prop, QVector3D(pose[0], pose[1], pose[2]))

                if orientation is not None and len(orientation) == 4:
                    quat = QQuaternion(
                        orientation[3],
                        orientation[0],
                        orientation[1],
                        orientation[2]
                    )
                    self.root_object.setProperty(rot_prop, quat)
            else:
                self.root_object.setProperty(pos_prop, QVector3D(0, 0, 0))
