from PyQt6.QtCore import QThread, QTimer
from data.control_utils import PhysicalSignalManager
import serial
import time

from PyQt6.QtCore import QThread, QTimer

class robotWorker(QThread):
    def __init__(self, com: str):
        super().__init__()
        self.CM904 = serial.Serial(com, 9600, timeout=2)
        self.signal_manager = PhysicalSignalManager.get_instance()

        # Conectar señal de interfaz → slot local
        self.signal_manager.send_to_robot.connect(self.get_data_from_interface)

    def run(self):
        print("[DEBUG] robotWorker.run() iniciado con QTimer")

        # Crear un timer dentro del hilo
        self.timer = QTimer()
        self.timer.timeout.connect(self.request_data)
        self.timer.start(20)  # cada 20 ms → 50 Hz

        # Necesario para que el QTimer funcione dentro del QThread
        self.exec()

    def request_data(self):
        #print("[DEBUG] Emitiendo get_data_signal")
        self.signal_manager.get_data_signal.emit()

    def send_data_to_robot(self, valorm):
        if all(0 <= x <= 300 for x in valorm):
            #print(f"[DEBUG] Enviando al serial: {valorm}")
            self.CM904.write(f"A{round(valorm[0]*(1023/300))}\n".encode())
            self.CM904.write(f"B{round(valorm[1]*(1023/300))}\n".encode())
            self.CM904.write(f"C{round(valorm[2]*(1023/300))}\n".encode())
            self.CM904.write(f"D{round(valorm[3]*(1023/300))}\n".encode())
            self.CM904.write(f"E{round(valorm[4]*(1023/300))}\n".encode())
            self.CM904.write(f"F{round(valorm[5]*(1023/300))}\n".encode())
        else:
            print("Error de envío de datos: Valores fuera de rango")

    def get_data_from_interface(self, datos):
        #print(f"[RobotWorker] Recibido desde interfaz: {datos}")
        self.send_data_to_robot(datos)

    def stop(self):
        if hasattr(self, "timer"):
            self.timer.stop()
        self.quit()
        self.wait()


