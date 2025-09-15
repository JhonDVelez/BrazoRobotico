import serial
import time
from PyQt6.QtCore import QThread, QTimer
from data.control_utils import PhysicalSignalManager, modes, units, domains


class robotWorker(QThread):
    def __init__(self):
        super().__init__()
        CM904 = serial.Serial('COM6', 9600, timeout=2)
        q1r, q2r, q3r, q4r, q5r, q6r = [], [], [], [], [], []
        q1rf, q2rf, q3rf, q4rf, q5rf, q6rf = [], [], [], [], [], []

        
        # ---------------- PROGRAMA ----------------
        start_time = time.time()
        cont = 0
        self.signal_manager = PhysicalSignalManager.get_instance()
        # Conectamos la señal con el slot
        self.signal_manager.send_to_robot.connect(self.recibir_datos)
    
    def run(self):
        QTimer.singleShot(4, self.get_data)

    def send_data(self, valorm):
        CM904.write(f"A{int(valorm[0]*(1023/300))}\n".encode())
        CM904.write(f"B{int(valorm[1]*(1023/300))}\n".encode())
        CM904.write(f"C{int(valorm[2]*(1023/300))}\n".encode())
        CM904.write(f"D{int(valorm[3]*(1023/300))}\n".encode())
        CM904.write(f"E{int(valorm[4]*(1023/300))}\n".encode())
        CM904.write(f"F{int(valorm[5]*(1023/300))}\n".encode())

    def recibir_datos(self, datos):
        print(f"[RobotWorker] Datos recibidos: {datos}")
        self.send_data(datos)
        QTimer.singleShot(4, self.get_data)

    def get_data(self):
        self.signal_manager.get_data_signal.emit()
       