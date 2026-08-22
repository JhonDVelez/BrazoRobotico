"""
Módulo para la comunicación serial con el hardware del robot.

Este módulo define la clase RobotWorker, la cual gestiona el envío de comandos
y la recepción de telemetría (posición y temperatura) desde la placa de
control (OpenCM9.04) utilizando un hilo dedicado.

Conexiones:
    - Utiliza `PhysicalSignalManager` para reportar el estado de conexión.
    - Emite `data_received` al recibir telemetría válida.
    - Recibe datos mediante una cola (`queue.Queue`) para evitar bloqueos.
"""

import re
import time
import queue
import serial
import threading
import traceback
from PyQt6.QtCore import QThread, pyqtSignal
from src.services.robot.serial_manager import SerialPortManager

class RobotWorker(QThread):
    """
    Worker encargado de la comunicación serial bidireccional con el robot.

    Gestiona un buffer de recepción, procesa expresiones regulares para extraer
    datos de telemetría y utiliza una cola de prioridad para los comandos de salida.

    Attributes:
        data_received (pyqtSignal): Señal que envía (lista_posiciones, lista_temperaturas).
        connection_status_changed (pyqtSignal): Señal que informa cambio en el estado serie.
    """
    # Definimos señales locales para el Controller
    data_received = pyqtSignal(list, list)
    connection_status_changed = pyqtSignal(bool)
    port_released = pyqtSignal()

    _TELEMETRY_PATTERN = re.compile(r"([A-F])(\d+\.?\d*)T[A-F](\d+)")

    def __init__(self, com: str):
        """
        Inicializa el worker serial y abre la conexión con el puerto COM.

        Args:
            com (str): Nombre del puerto serial (e.g., 'COM3' o '/dev/ttyACM0').
        """
        super().__init__()
        self._com = com
        self._send_queue = queue.Queue()
        self._running = True
        self._suspended = False
        self._pause_event = threading.Event()
        self._pause_event.set()

        # Intentar abrir el puerto serial mediante SerialPortManager
        if SerialPortManager.get_instance().request_access(self._com, "RobotWorker"):
            self.connection_status_changed.emit(True)
        else:
            print(f"No se pudo abrir {self._com}")
            self.connection_status_changed.emit(False)

        self._last_positions = [None] * 6
        self._last_temperaturas = [None] * 6
        self._last_valid_positions = [150.0] * 6
        self._jump_freeze_count = [0] * 6

    # --- Getters and Setters ---
    def get_com(self) -> str:
        """
        Obtiene el nombre del puerto COM configurado.

        Returns:
            str: Nombre del puerto.
        """
        return self._com

    def get_is_connected(self) -> bool:
        """
        Verifica si hay una conexión serial activa.

        Returns:
            bool: True si esta conectado.
        """
        cm904 = SerialPortManager.get_instance().get_serial()
        return cm904 is not None and getattr(cm904, 'is_open', False)

    def get_last_positions(self) -> list:
        """
        Obtiene la última lectura de posiciones de los servos.

        Returns:
            list: Lista de 6 posiciones (grados) o None.
        """
        return self._last_positions.copy()

    def get_last_temperatures(self) -> list:
        """
        Obtiene la última lectura de temperaturas de los motores.

        Returns:
            list: Lista de 6 temperaturas (Celsius) o None.
        """
        return self._last_temperaturas.copy()

    def enqueue_data(self, valorm):
        """
        Añade nuevos comandos a la cola de envío.

        Descarta comandos anteriores que aún no se hayan procesado para
        asegurar que el robot reciba siempre el estado mas reciente.

        Args:
            valorm (list): Lista de 6 posiciones objetivo en grados (0-300).
        """
        while not self._send_queue.empty():
            try:
                self._send_queue.get_nowait()
            except queue.Empty:
                break
        self._send_queue.put(valorm)

    def run(self):
        """
        Bucle principal del hilo de comunicación.

        Extrae comandos de la cola y ejecuta la transaccion serial.
        """
        while self._running:
            self._pause_event.wait()
            try:
                valorm = self._send_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[DEBUG] [RobotWorker] Error en queue.get: {e}")
                continue

            try:
                self._send_and_receive(valorm)
            except Exception as e:
                print(f"[DEBUG] [RobotWorker] Excepción no controlada en _send_and_receive: {e}")
                traceback.print_exc()
                try:
                    self.connection_status_changed.emit(False)
                except Exception:
                    pass

    def _send_and_receive(self, valorm):
        """
        Realiza la transacción de bajo nivel: envía PWMs y recibe telemetría.

        Args:
            valorm (list): Comandos de posición originales.
        """
        try:
            if not all(0 <= x <= 300 for x in valorm):
                print("Error de envío de datos: Valores fuera de rango")
                return

            spm = SerialPortManager.get_instance()
            
            # Reconexión automática si el puerto se cerró (excepto durante suspensión)
            # Solo reconectar si RobotWorker es el trabajador activo
            if not self._suspended and spm.is_active("RobotWorker"):
                cm904 = spm.get_serial()
                if cm904 is None or not getattr(cm904, 'is_open', False):
                    print(f"[DEBUG] Attempting auto-reconnect serial, suspended: {self._suspended}")
                    try:
                        spm.request_access(self._com, "RobotWorker")
                        self.connection_status_changed.emit(True)
                    except Exception as e:
                        print(f"No se pudo abrir {self._com} antes de enviar: {e}")
                        self.connection_status_changed.emit(False)
                        return
                    cm904 = spm.get_serial()
                
                if cm904 is None or not getattr(cm904, 'is_open', False):
                    return

                # Envío de trama compacta: A<pwm>B<pwm>C<pwm>D<pwm>E<pwm>F<pwm>\n
                try:
                    frame = self._build_command_frame(valorm)
                    cm904.write(frame)
                    cm904.flush()
                except (serial.SerialException, OSError) as e:
                    print(f"[DEBUG] [RobotWorker] SerialException/OSError en write/flush: {e}")
                    self.connection_status_changed.emit(False)
                    try:
                        if cm904:
                            cm904.close()
                    except (serial.SerialException, OSError):
                        pass
                    return

                # Recepción y parseo de telemetría
                try:
                    result = self._read_and_filter()
                    if result is None:
                        return

                    self._last_positions, self._last_temperatures = result

                    self.data_received.emit(
                        self._last_positions.copy(), self._last_temperatures.copy())

                except Exception as e:
                    print(f"Error lectura: {e}")
                    traceback.print_exc()
                    self.connection_status_changed.emit(False)
            else:
                # Si no es activo o está suspendido, no intentar enviar
                return
        except Exception as e:
            print(f"[DEBUG] [RobotWorker] Excepción capturada en _send_and_receive: {e}")
            traceback.print_exc()
            try:
                self.connection_status_changed.emit(False)
            except Exception:
                pass


    def _build_command_frame(self, positions: list) -> bytes:
        """
        Construye la trama compacta esperada por el microcontrolador.

        Args:
            positions (list): Lista de 6 posiciones objetivo en grados (0-300).

        Returns:
            bytes: Trama ASCII `A...B...C...D...E...F...\n` con valores PWM.
        """
        frame = ""
        for index, char in enumerate(['A', 'B', 'C', 'D', 'E', 'F']):
            position = max(0.0, min(300.0, float(positions[index])))
            pwm_value = int(round(position * (1023 / 300)))
            frame += f"{char}{pwm_value}"
        return f"{frame}\n".encode('ascii')

    def _read_and_filter(self):
        """
        Lee una linea del puerto serial, parsea y filtra la telemetria.
        """
        cm904 = SerialPortManager.get_instance().get_serial()
        try:
            waiting = cm904.in_waiting
        except Exception:
            self.connection_status_changed.emit(False)
            return None

        if waiting == 0:
            time.sleep(0.05)
            try:
                waiting = cm904.in_waiting
            except Exception:
                self.connection_status_changed.emit(False)
                return None
            if waiting == 0:
                return None

        try:
            line = cm904.readline().decode('ascii', errors='ignore').strip()
            if not line:
                return None
        except Exception as e:
            print(f"Error leyendo del serial: {e}")
            return None

        matches = self._TELEMETRY_PATTERN.findall(line)
        if len(matches) < 6:
            return None

        temp_pos = [None] * 6
        temperatures = list(self._last_temperaturas)
        for motor_char, position_value, temperature_value in matches:
            idx = ord(motor_char) - ord('A')
            if idx < 6:
                temp_pos[idx] = float(position_value)
                temperatures[idx] = int(temperature_value)

        # Validacion de rango: filtrar valores fuera de rango fisico individualmente
        for i in range(6):
            if temp_pos[i] is not None and not (0 <= temp_pos[i] <= 300):
                temp_pos[i] = self._last_valid_positions[i]
            if temperatures[i] is not None and not (0 <= temperatures[i] <= 100):
                temperatures[i] = None

        # Deteccion de tramas nulas / caidas de tension
        if all(v is not None and abs(v) < 0.001 for v in temp_pos[:4]):
            return None

        # Filtro anti-ruido electromagnetico con correccion individual
        for i in range(6):
            if temp_pos[i] is not None:
                diff = abs(temp_pos[i] - self._last_valid_positions[i])
                if diff > 35.0:
                    self._jump_freeze_count[i] += 1
                    if self._jump_freeze_count[i] <= 4:
                        temp_pos[i] = self._last_valid_positions[i]
                else:
                    self._jump_freeze_count[i] = 0

        # Actualizacion limpia de la telemetria
        positions = list(self._last_valid_positions)
        for i in range(6):
            if temp_pos[i] is not None:
                positions[i] = temp_pos[i]
                self._last_valid_positions[i] = temp_pos[i]

        return positions, temperatures

    def force_abort(self):
        """Forzar detención inmediata e interrupción de IO serial."""
        self._running = False
        self._suspended = True
        
        # Interrumpir IO bloqueante inmediatamente
        cm904 = SerialPortManager.get_instance().get_serial()
        if cm904:
            try:
                cm904.cancel_read()
                cm904.cancel_write()
                cm904.close()
            except:
                pass
        
        # Vaciar cola de forma sincrónica
        while not self._send_queue.empty():
            try:
                self._send_queue.get_nowait()
            except queue.Empty:
                break
        
        self.quit()
        # No bloqueamos indefinidamente, esperamos un poco
        self.wait(1000)

    def suspend_serial(self):
        """Cierra el puerto serial para liberar el recurso COM."""
        self.release_and_cleanup()

    def release_and_cleanup(self):
        """Libera el puerto serial, limpia buffers y notifica."""
        self._suspended = True
        SerialPortManager.get_instance().release_access("RobotWorker")
        self.port_released.emit()

    def resume_serial(self):
        """
        Reabre el puerto serial despues de una suspension.
        """
        print(f"[DEBUG] Resuming serial for {self._com}, was suspended: {self._suspended}")
        self._suspended = False
        try:
            cm904 = SerialPortManager.get_instance().get_serial()
            if cm904 is None or not getattr(cm904, 'is_open', False):
                SerialPortManager.get_instance().request_access(self._com, "RobotWorker")
                self.connection_status_changed.emit(True)
                print(f"[DEBUG] Serial re-opened successfully")
        except Exception as e:
            print(f"Error reabriendo {self._com}: {e}")
            self.connection_status_changed.emit(False)

    def pause_transmission(self):
        self._pause_event.clear()

    def resume_transmission(self):
        self._pause_event.set()
