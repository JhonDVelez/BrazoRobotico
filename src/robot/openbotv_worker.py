import serial
import time
from PyQt6.QtCore import QThread, QTimer
from data.control_utils import PhysicalSignalManager, modes, units, domains


class robotWorker(QThread):
    def __init__(self, com: str):
        super().__init__()
        print(f"Worker inicializado en el puerto: {com}")
        self.CM904 = serial.Serial(com, 115200, timeout=2)
        q1r, q2r, q3r, q4r, q5r, q6r = [], [], [], [], [], []
        q1rf, q2rf, q3rf, q4rf, q5rf, q6rf = [], [], [], [], [], []

        # ---------------- PROGRAMA ----------------
        start_time = time.time()
        cont = 0
        self.signal_manager = PhysicalSignalManager.get_instance()
        # Conectamos la señal con el slot
        self.signal_manager.send_to_robot.connect(self.get_data_from_interface)

    def run(self):
        QTimer.singleShot(0, self.signal_manager.get_data_signal.emit)

    def send_data_to_robot(self, valorm):
        if all(x >= 0 and x <= 300 for x in valorm):
            self.CM904.write(f"A{int(valorm[0]*(1023/300))}\n".encode())
            self.CM904.write(f"B{int(valorm[1]*(1023/300))}\n".encode())
            self.CM904.write(f"C{int(valorm[2]*(1023/300))}\n".encode())
            self.CM904.write(f"D{int(valorm[3]*(1023/300))}\n".encode())
            self.CM904.write(f"E{int(valorm[4]*(1023/300))}\n".encode())
            self.CM904.write(f"F{int(valorm[5]*(1023/300))}\n".encode())
            print("datos enviados")
        else:
            print("Error de envio de datos: Valores fuera de rango")

    def get_data_from_interface(self, datos):
        print(f"[RobotWorker] Datos recibidos: {datos}")
        self.send_data_to_robot(datos)
        QTimer.singleShot(4, self.signal_manager.get_data_signal.emit)
