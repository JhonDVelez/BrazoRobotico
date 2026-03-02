import serial
import re
import time
import queue
from PyQt6.QtCore import QThread
from data import PhysicalSignalManager, GlobalTimer


class RobotWorker(QThread):

    def __init__(self, com: str):
        super().__init__()
        self.cm904 = serial.Serial(com, 9600, timeout=1)
        self._send_queue = queue.Queue()
        self._running = True

        self.signal_manager = PhysicalSignalManager.get_instance()
        self.signal_manager.send_to_robot.connect(
            self.enqueue_data)  # ya no bloquea
        self.signal_manager.is_connected = True

        self.sync_timer = GlobalTimer.get_instance()

    def enqueue_data(self, valorm):
        """Descarta comandos anteriores si el micro no ha respondido aún."""
        # Vaciar queue antes de meter el nuevo valor
        while not self._send_queue.empty():
            try:
                self._send_queue.get_nowait()
            except queue.Empty:
                break
        self._send_queue.put(valorm)

    def run(self):
        """Todo el trabajo serial ocurre aquí, en el hilo secundario."""
        while self._running:
            try:
                valorm = self._send_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            self._send_and_receive(valorm)

    def _send_and_receive(self, valorm):
        if not all(0 <= x <= 300 for x in valorm):
            print("Error de envío de datos: Valores fuera de rango")
            return

        # Limpiar buffer de entrada antes de enviar
        self.cm904.reset_input_buffer()

        # Envío serial
        for i, char in enumerate(['A', 'B', 'C', 'D', 'E', 'F']):
            val_pwm = round(valorm[i] * (1023 / 300))
            self.cm904.write(f"{char}{val_pwm}\n".encode())
            time.sleep(0.05)

        # Esperar respuesta con timeout
        timeout = 2.0
        start = time.time()
        while not self.cm904.in_waiting:
            if time.time() - start > timeout:
                print("Timeout: el micro no respondió")
                return
            time.sleep(0.001)

        # Lectura
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

            self.sync_timer.sync_simulation_tick.emit()
            self.signal_manager.data_received.emit(posiciones, temperaturas)

        except Exception as e:
            print(f"Error lectura: {e}")

    def request_data(self):
        self.signal_manager.get_data_signal.emit()

    def stop(self):
        self._running = False
        self.cm904.close()
        self.signal_manager.is_connected = False
        self.quit()
        self.wait()
