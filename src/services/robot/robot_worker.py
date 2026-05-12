import serial
import re
import time
import queue
from PyQt6.QtCore import QThread, pyqtSignal
from ..data.signals import PhysicalSignalManager
from ..data.timers import GlobalTimer


class RobotWorker(QThread):
    # Definimos señales para comunicar resultados hacia el Controller
    data_received = pyqtSignal(list, list)

    def __init__(self, com: str, compensator=None):
        super().__init__()
        self._com = com
        self._cm904 = None
        self._compensator = compensator
        self._send_queue = queue.Queue()
        self._running = True

        self._signal_manager = PhysicalSignalManager.get_instance()

        # Intentar abrir el puerto serial
        try:
            self._cm904 = serial.Serial(self._com, 9600, timeout=1)
            self._signal_manager.is_connected = True
        except (serial.SerialException, PermissionError, OSError) as e:
            print(f"No se pudo abrir {self._com}: {e}")
            self._cm904 = None
            self._signal_manager.is_connected = False

        self._sync_timer = GlobalTimer.get_instance()
        self._recv_buffer = ""
        self._last_positions = [None] * 6
        self._last_temperaturas = [None] * 6

    # --- Getters and Setters ---
    def get_com(self) -> str:
        return self._com

    def get_is_connected(self) -> bool:
        return self._signal_manager.is_connected

    def get_last_positions(self) -> list:
        return self._last_positions.copy()

    def get_last_temperatures(self) -> list:
        return self._last_temperaturas.copy()

    def enqueue_data(self, valorm):
        """Descarta comandos anteriores si el micro no ha respondido aún."""
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
        # Intercepción de datos antes del procesamiento de envío
        if self._compensator:
            valorm = self._compensator.process_data(valorm)

        if not all(0 <= x <= 300 for x in valorm):
            print("Error de envío de datos: Valores fuera de rango")
            return

        if self._cm904 is None or not getattr(self._cm904, 'is_open', False):
            try:
                self._cm904 = serial.Serial(self._com, 9600, timeout=1)
                self._signal_manager.is_connected = True
            except (serial.SerialException, PermissionError, OSError) as e:
                print(f"No se pudo abrir {self._com} antes de enviar: {e}")
                self._signal_manager.is_connected = False
                return

        try:
            self._cm904.reset_input_buffer()
        except Exception as e:
            print(f"Error limpiando buffer: {e}")
            self._signal_manager.is_connected = False
            self._cm904 = None
            return

        try:
            for i, char in enumerate(['A', 'B', 'C', 'D', 'E', 'F']):
                val_pwm = round(valorm[i] * (1023 / 300))
                self._cm904.write(f"{char}{val_pwm}\n".encode())
                time.sleep(0.001)
        except (serial.SerialException, OSError) as e:
            print(f"Error al escribir en serial: {e}")
            self._signal_manager.is_connected = False
            try:
                if self._cm904:
                    self._cm904.close()
            except Exception:
                pass
            self._cm904 = None
            return

        try:
            timeout = 0.001
            start = time.time()
            data = b""
            while time.time() - start < timeout:
                try:
                    avail = self._cm904.in_waiting
                except Exception:
                    self._signal_manager.is_connected = False
                    self._cm904 = None
                    return
                if avail:
                    chunk = self._cm904.read(avail)
                    if chunk:
                        data += chunk
                        if b';' in data:
                            break
                else:
                    time.sleep(0.01)

            if not data:
                return

            try:
                s = data.decode('ascii', errors='ignore')
            except Exception:
                s = ''

            combined = self._recv_buffer + s
            parts = combined.split(';')
            complete_tokens = parts[:-1]
            self._recv_buffer = parts[-1]

            for token in complete_tokens:
                token = token.strip()
                if not token:
                    continue
                temp_match = re.search(r'T([A-F])(\d+)', token)
                pos_match = re.match(r'([A-F])(\d+(?:\.\d+)?)', token)

                pos_letter = None
                pos_val = None
                if pos_match:
                    pos_letter = pos_match.group(1)
                    pos_val = pos_match.group(2)
                else:
                    m = re.search(r'(\d+(?:\.\d+)?)(?=T)', token)
                    if m and temp_match:
                        pos_val = m.group(1)
                        pos_letter = temp_match.group(1)

                if pos_letter and pos_val is not None:
                    idx = ord(pos_letter) - ord('A')
                    try:
                        self._last_positions[idx] = float(pos_val)
                    except Exception:
                        pass
                if temp_match:
                    t_letter = temp_match.group(1)
                    t_val = temp_match.group(2)
                    idx = ord(t_letter) - ord('A')
                    try:
                        self._last_temperaturas[idx] = int(t_val)
                    except Exception:
                        pass

            self._sync_timer.sync_simulation_tick.emit()
            self._signal_manager.data_received.emit(
                self._last_positions.copy(), self._last_temperaturas.copy())
            self.data_received.emit(
                self._last_positions.copy(), self._last_temperaturas.copy())

        except Exception as e:
            print(f"Error lectura: {e}")

    def stop(self):
        self._running = False
        try:
            if self._cm904 and getattr(self._cm904, 'is_open', False):
                self._cm904.close()
        except Exception:
            pass
        self._signal_manager.is_connected = False
        self.quit()
        self.wait()
