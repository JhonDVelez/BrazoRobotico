import serial
import time
from PyQt6.QtCore import QThread, QTimer
from data.control_utils import PhysicalSignalManager, modes, units, domains


class robotWorker(QThread):
    def __init__(self, com: str):
        super().__init__()
        self.CM904 = serial.Serial(com, 9600, timeout=2)
        q1r, q2r, q3r, q4r, q5r, q6r = [], [], [], [], [], []
        q1rf, q2rf, q3rf, q4rf, q5rf, q6rf = [], [], [], [], [], []

        # ---------------- PROGRAMA ----------------
        start_time = time.time()
        cont = 0
        self.signal_manager = PhysicalSignalManager.get_instance()
        # Conectamos la señal con el slot
        self.signal_manager.send_to_robot.connect(self.get_data_from_interface)

    def run(self):
        self.signal_manager.get_data_signal.emit()

    def send_data_to_robot(self, valorm):
        if all(x >= 0 and x <= 300 for x in valorm):
            self.CM904.write(f"A{round(valorm[0]*(1023/300))}\n".encode())
            self.CM904.write(f"B{round(valorm[1]*(1023/300))}\n".encode())
            self.CM904.write(f"C{round(valorm[2]*(1023/300))}\n".encode())
            self.CM904.write(f"D{round(valorm[3]*(1023/300))}\n".encode())
            self.CM904.write(f"E{round(valorm[4]*(1023/300))}\n".encode())
            self.CM904.write(f"F{round(valorm[5]*(1023/300))}\n".encode())
            time.sleep(0.02)
        else:
            print("Error de envio de datos: Valores fuera de rango")

    def get_data_from_interface(self, datos):
        print(f"[RobotWorker] Enviando datos al puerto serial: {datos}")  
        self.send_data_to_robot(datos)
        QTimer.singleShot(4, self.signal_manager.get_data_signal.emit)
