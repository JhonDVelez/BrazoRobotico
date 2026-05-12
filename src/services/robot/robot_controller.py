"""
Controlador principal para el servicio de robot. 
Actúa como la única interfaz entre la lógica de negocio (Features) 
y el procesamiento de hardware (Worker).
"""
from PyQt6.QtCore import QObject
from .robot_worker import RobotWorker
from .robot_compensator import RobotCompensator
from src.services.data.signals import PhysicalSignalManager


class RobotController(QObject):
    def __init__(self, com: str):
        super().__init__()
        # Inicialización de componentes internos
        self._compensator = RobotCompensator()
        self._worker = RobotWorker(com, self._compensator)
        self._signal_manager = PhysicalSignalManager.get_instance()

        # Conectar señales necesarias entre worker y controller si es necesario
        # Por ahora, mantenemos la lógica de comunicación serial en el worker

    # --- Getters ---
    def get_worker(self) -> RobotWorker:
        """ Retorna el worker del robot """
        return self._worker

    def get_compensator(self) -> RobotCompensator:
        """ Retorna el compensador del robot """
        return self._compensator

    def move_to(self, positions: list):
        """ API pública para mover el robot """
        if not all(0 <= x <= 300 for x in positions):
            print("Error: Valores fuera de rango")
            return
        # El worker se encargará de llamar al compensador antes del envío
        self._worker.enqueue_data(positions)

    def start_service(self):
        """ Inicia el hilo del worker """
        self._worker.start()

    def stop_service(self):
        """ Detiene el hilo del worker """
        self._worker.stop()
