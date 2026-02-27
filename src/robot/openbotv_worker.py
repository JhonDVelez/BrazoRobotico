import serial
import re
import time
from PyQt6.QtCore import QThread
from data import PhysicalSignalManager, GlobalTimer


class RobotWorker(QThread):
    """ Hilo de trabajo para el envió y recepción de datos del openbotv v1 físico
    """

    def __init__(self, com: str):
        super().__init__()
        self.cm904 = serial.Serial(com, 9600, timeout=1)

        self.signal_manager = PhysicalSignalManager.get_instance()
        # Conectar señal de interfaz → slot local
        self.signal_manager.send_to_robot.connect(self.send_data_to_robot)
        self.signal_manager.is_connected = True

        self.sync_timer = GlobalTimer.get_instance()
        self._running = True

    def request_data(self):
        """ Solicita datos a la interfaz dependiendo del modo activado
        """
        # print("[DEBUG] Emitiendo get_data_signal")
        self.signal_manager.get_data_signal.emit()

    def send_data_to_robot(self, valorm):
        if not all(0 <= x <= 300 for x in valorm):
            print("Error de envío de datos: Valores fuera de rango")
            return

        for i, char in enumerate(['A', 'B', 'C', 'D', 'E', 'F']):
            val_pwm = round(valorm[i] * (1023/300))
            self.cm904.write(f"{char}{val_pwm}\n".encode())
            time.sleep(0.05)

        # Esperar hasta que el micro responda
        timeout = 2.0
        start = time.time()
        while not self.cm904.in_waiting:
            if time.time() - start > timeout:
                print("Timeout: el micro no respondió")
                return
            time.sleep(0.001)

        # Lectura de datos
        try:
            line = self.cm904.readline().decode('ascii', errors='ignore').strip()

            if not line or ";" not in line:
                print(f"Respuesta inválida del micro: '{line}'")
                return

            posiciones = [None] * 6
            temperaturas = [None] * 6

            for i, char in enumerate(['A', 'B', 'C', 'D', 'E', 'F']):
                pos_match = re.search(rf"{char}(\d+)", line)
                temp_match = re.search(rf"T{char}(\d+)", line)
                if pos_match:
                    posiciones[i] = float(pos_match.group(1))
                if temp_match:
                    temperaturas[i] = int(temp_match.group(1))

            self.sync_timer.sync_tick.emit()
            self.signal_manager.data_received.emit(posiciones, temperaturas)

        except Exception as e:
            print(f"Error lectura: {e}")

    def stop(self):
        """ Detiene el envío de datos al robot.
        """
        self._running = False
        self.cm904.close()
        self.signal_manager.is_connected = False
        self.quit()
        self.wait()
