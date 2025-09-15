from PyQt6.QtCore import QThread
from data.control_utils import PhysicalSignalManager, modes, units, domains, SimulationSignalManager


class robotWorker(QThread):
    def __init__(self):
        super().__init__()
        self.signal_manager = PhysicalSignalManager.get_instance()
        # Conectamos la señal con el slot
        self.signal_manager.send_to_robot.connect(self.recibir_datos)
    def send_data(self):
        pass
    def recibir_datos(self, datos):
        print("[RobotWorker] Datos recibidos:", datos)
       