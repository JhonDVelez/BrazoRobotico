import serial
import re
import time
import queue
from PyQt6.QtCore import QThread
from data import PhysicalSignalManager, GlobalTimer


class RobotWorker(QThread):

    def __init__(self, com: str):
        super().__init__()
        self.com = com
        self.cm904 = None
        self._send_queue = queue.Queue()
        self._running = True

        self.signal_manager = PhysicalSignalManager.get_instance()
        self.signal_manager.send_to_robot.connect(self.enqueue_data)
        # Intentar abrir el puerto serial, manejar errores sin crashear la app
        try:
            self.cm904 = serial.Serial(self.com, 9600, timeout=1)
            self.signal_manager.is_connected = True
        except (serial.SerialException, PermissionError, OSError) as e:
            print(f"No se pudo abrir {self.com}: {e}")
            self.cm904 = None
            self.signal_manager.is_connected = False

        self.sync_timer = GlobalTimer.get_instance()
        # Buffer para ensamblar tramas fragmentadas y estado último conocido
        self._recv_buffer = ""
        self._last_positions = [None] * 6
        self._last_temperaturas = [None] * 6

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

    def start(self):
        self._running = True
        self.run()

    def pause(self):
        self._running = False

    def _send_and_receive(self, valorm):
        if not all(0 <= x <= 300 for x in valorm):
            print("Error de envío de datos: Valores fuera de rango")
            return
        # print(f"Robot: {valorm}")
        # Verificar que el puerto esté abierto; intentar reconectar si es necesario
        if self.cm904 is None or not getattr(self.cm904, 'is_open', False):
            try:
                self.cm904 = serial.Serial(self.com, 9600, timeout=1)
                self.signal_manager.is_connected = True
            except (serial.SerialException, PermissionError, OSError) as e:
                print(f"No se pudo abrir {self.com} antes de enviar: {e}")
                self.signal_manager.is_connected = False
                return

        # Limpiar buffer de entrada antes de enviar
        try:
            self.cm904.reset_input_buffer()
        except Exception as e:
            print(f"Error limpiando buffer: {e}")
            self.signal_manager.is_connected = False
            self.cm904 = None
            return

        # Envío serial
        try:
            for i, char in enumerate(['A', 'B', 'C', 'D', 'E', 'F']):
                val_pwm = round(valorm[i] * (1023 / 300))
                self.cm904.write(f"{char}{val_pwm}\n".encode())
                time.sleep(0.05)
        except (serial.SerialException, OSError) as e:
            print(f"Error al escribir en serial: {e}")
            self.signal_manager.is_connected = False
            try:
                if self.cm904:
                    self.cm904.close()
            except Exception as e:
                print(e)
                pass
            self.cm904 = None
            return

        # Esperar respuesta con timeout
        # timeout = 2.0
        # start = time.time()
        # try:
        #     while not self.cm904.in_waiting:
        #         if time.time() - start > timeout:
        #             print("Timeout: el micro no respondió")
        #             return
        #         # time.sleep(0.001)
        # except Exception as e:
        #     print(f"Error comprobando in_waiting: {e}")
        #     self.signal_manager.is_connected = False
        #     self.cm904 = None
        #     return

        # Lectura robusta: ensamblar tramas fragmentadas usando un buffer
        try:
            timeout = 2.0
            start = time.time()
            data = b""
            # Leer hasta encontrar al menos un ';' o agotar timeout
            while time.time() - start < timeout:
                try:
                    avail = self.cm904.in_waiting
                except Exception as e:
                    print(f"Error comprobando in_waiting: {e}")
                    self.signal_manager.is_connected = False
                    self.cm904 = None
                    return

                if avail:
                    chunk = self.cm904.read(avail)
                    if chunk:
                        data += chunk
                        if b';' in data:
                            break
                else:
                    time.sleep(0.01)

            if not data:
                print("Timeout: no se recibió respuesta")
                return

            try:
                s = data.decode('ascii', errors='ignore')
            except Exception:
                s = ''

            # Añadir al buffer previo, separar por ';' y procesar tokens completos
            combined = self._recv_buffer + s
            parts = combined.split(';')
            complete_tokens = parts[:-1]
            self._recv_buffer = parts[-1]  # parte incompleta (si la hay)

            # Procesar cada token; actualizar último estado parcial
            for token in complete_tokens:
                token = token.strip()
                if not token:
                    continue

                # Buscar temp: formato T<LETTER><NUM>
                temp_match = re.search(r'T([A-F])(\d+)', token)

                # Buscar pos: preferimos letra delante, si no está inferimos desde temp
                pos_match = re.match(r'([A-F])(\d+(?:\.\d+)?)', token)

                pos_letter = None
                pos_val = None
                if pos_match:
                    pos_letter = pos_match.group(1)
                    pos_val = pos_match.group(2)
                else:
                    # intentar extraer número antes de 'T' si existe
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

            # Emitir snapshot con último estado conocido (copias para evitar mutación externa)
            self.sync_timer.sync_simulation_tick.emit()
            self.signal_manager.data_received.emit(self._last_positions.copy(), self._last_temperaturas.copy())

        except (serial.SerialException, OSError) as e:
            print(f"Error lectura (serial): {e}")
            self.signal_manager.is_connected = False
            try:
                if self.cm904:
                    self.cm904.close()
            except Exception:
                pass
            self.cm904 = None
        except Exception as e:
            print(f"Error lectura: {e}")
        #     self.signal_manager.is_connected = False
        #     try:
        #         if self.cm904:
        #             self.cm904.close()
        #     except Exception as e:
        #         print(e)
        #         pass
        #     self.cm904 = None
        # except Exception as e:
        #     print(f"Error lectura: {e}")

    def request_data(self):
        self.signal_manager.get_data_signal.emit()

    def stop(self):
        self._running = False
        try:
            if self.cm904 and getattr(self.cm904, 'is_open', False):
                self.cm904.close()
        except Exception as e:
            print(e)
            pass
        self.signal_manager.is_connected = False
        self.quit()
        self.wait()
