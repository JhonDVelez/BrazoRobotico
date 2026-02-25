from PyQt6.QtCore import QThread, pyqtSignal, QObject
from PyQt6.QtGui import QVector3D
from qdarktheme.qtpy.QtCore import pyqtSlot
from data.control_utils import SimulationSignalManager


class SimWorker(QThread):
    """ Worker thread para manejar la actualización del modelo 3D. 
        Se encarga de transformar los datos de la simulación en movimientos visibles 
        en la interfaz de QtQuick.
    """

    def __init__(self, root_object, robot_id):
        super().__init__()
        self.hwnd = None
        self.timer = None
        # Referencia al objeto raíz del archivo QML (la escena 3D)
        self.root_object = root_object 
        
        # Nombres de los nodos (Joints) definidos en el archivo de diseño 3D (.qml)
        self.joint_names = [
            "arm1_link_1",
            "arm2_link_1",
            "arm3_link_1",
            "arm4_link_1",
            "clamp_arm_link_1",
            "clamp2_link_1"]
            
        # Define sobre qué eje debe rotar cada pieza según su orientación en el espacio 3D
        self.direction_rotation = [
            "y",
            "z",
            "z",
            "y",
            "z",
            "z"]

        # Acceso al gestor de señales de simulación (Patrón Singleton)
        self.signal_manager = SimulationSignalManager.get_instance()
        
        # Conexión: Cada vez que los datos del robot cambian, se dispara 'update_simulation'
        self.signal_manager.update_robot_signal.connect(self.update_simulation)

    @pyqtSlot(list)
    def update_simulation(self, joint_positions=None):
        """ Actualiza las propiedades de rotación del modelo 3D de QtQuick.

        Args:
            joint_positions (list, optional): Lista de 6 valores con los ángulos 
                                              actuales de los motores. Defaults to None.
        """
        # Inicialización de seguridad si no se reciben datos
        if joint_positions is None:
            joint_positions = [0, 0, 0, 0, 0, 0]
            
        # Inversión de signo para los motores 1 y 2 (corrección de sentido de giro 
        # para que la vista coincida con la cinemática del robot)
        for i in (1, 2):
            joint_positions[i] *= -1
            
        # Emparejamiento de cada motor con su nombre, ángulo y eje de rotación correspondiente
        for motor_name, angle, direction in zip(self.joint_names,
                                                joint_positions,
                                                self.direction_rotation):
            
            # Busca el componente 3D dentro de la jerarquía del archivo QML por su nombre
            motor = self.root_object.findChild(QObject, motor_name)
            
            if motor:
                # Aplica la rotación de Euler basándose en el eje definido ("z" o "y")
                # Se crea un QVector3D donde solo el eje activo recibe el valor del ángulo
                if direction == "z":
                    motor.setProperty("eulerRotation", QVector3D(0, 0, angle))
                elif direction == "y":
                    motor.setProperty("eulerRotation", QVector3D(0, angle, 0))