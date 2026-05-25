"""
Controlador principal para el servicio de robot.

Actua como la unica interfaz entre la logica de negocio (Features)
y el procesamiento de hardware (Worker). Implementa el patron
de fachada para ocultar la complejidad del worker y compensador.

Conexiones:
    - Combina RobotWorker (comunicacion serial) y RobotCompensator
      (procesamiento) bajo una unica interfaz.
    - Utiliza PhysicalSignalManager para reportar estado de conexion.
"""

from PyQt6.QtCore import QObject
from .robot_worker import RobotWorker
from .robot_compensator import RobotCompensator
from src.services.data.signals import PhysicalSignalManager


class RobotController(QObject):
    """Controlador principal que orquesta la comunicacion con el robot.

    Gestiona el ciclo de vida del worker serial y expone metodos
    de alto nivel para mover el robot y consultar su estado.

    Args:
        com (str): Puerto COM del robot (ej. 'COM3', '/dev/ttyACM0').
    """

    def __init__(self, com: str):
        super().__init__()
        self._compensator = RobotCompensator()
        self._worker = RobotWorker(com, self._compensator)
        self._signal_manager = PhysicalSignalManager.get_instance()

    # --- Getters ---

    def get_worker(self) -> RobotWorker:
        """Retorna el worker del robot.

        Returns:
            RobotWorker: Instancia del worker serial.
        """
        return self._worker

    def get_compensator(self) -> RobotCompensator:
        """Retorna el compensador del robot.

        Returns:
            RobotCompensator: Instancia del compensador de datos.
        """
        return self._compensator

    def move_to(self, positions: list):
        """API publica para mover el robot.

        Valida que las posiciones esten en el rango permitido (0-300)
        y encola el comando en el worker.

        Args:
            positions (list): Lista de 6 posiciones objetivo (0-300).
        """
        if not all(0 <= x <= 300 for x in positions):
            print("Error: Valores fuera de rango")
            return
        self._worker.enqueue_data(positions)

    def start_service(self):
        """Inicia el hilo del worker.

        El worker comienza a procesar comandos de la cola y
        a recibir telemetria del robot.
        """
        self._worker.start()

    def stop_service(self):
        """Detiene el hilo del worker.

        Detiene el ciclo de comunicacion y cierra el puerto serial.
        """
        self._worker.stop()
