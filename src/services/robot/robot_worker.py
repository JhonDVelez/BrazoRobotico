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
import queue
import serial
from PyQt6.QtCore import QThread, pyqtSignal

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

    _TELEMETRY_PATTERN = re.compile(r"([A-F])(\d+\.?\d*)T[A-F](\d+)")

    def __init__(self, com: str):
        """
        Inicializa el worker serial y abre la conexión con el puerto COM.

        Args:
            com (str): Nombre del puerto serial (e.g., 'COM3' o '/dev/ttyACM0').
        """
        super().__init__()
        self._com = com
        self._cm904 = None
        self._send_queue = queue.Queue()
        self._running = True

        # Intentar abrir el puerto serial
        try:
            self._cm904 = serial.Serial(self._com, 9600, timeout=1)
            self.connection_status_changed.emit(True)
        except (serial.SerialException, PermissionError, OSError) as e:
            print(f"No se pudo abrir {self._com}: {e}")
            self._cm904 = None
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
        return self._cm904 is not None and getattr(self._cm904, 'is_open', False)

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
            try:
                valorm = self._send_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            self._send_and_receive(valorm)

    def _send_and_receive(self, valorm):
        """
        Realiza la transacción de bajo nivel: envía PWMs y recibe telemetría.

        Args:
            valorm (list): Comandos de posición originales.
        """
<<<<<<< HEAD
=======
        # Intercepción de datos antes del procesamiento de envío (e.g. compensación de backlash)
        if self._compensator:
            valorm = self._compensator.process_data(valorm)

>>>>>>> 1825586cf103f63ef7f9c90d4540b2f568c648da
        if not all(0 <= x <= 300 for x in valorm):
            print("Error de envío de datos: Valores fuera de rango")
            return

        # Reconexión automática si el puerto se cerró
        if self._cm904 is None or not getattr(self._cm904, 'is_open', False):
            try:
                self._cm904 = serial.Serial(self._com, 9600, timeout=1)
                self.connection_status_changed.emit(True)
            except (serial.SerialException, PermissionError, OSError) as e:
                print(f"No se pudo abrir {self._com} antes de enviar: {e}")
                self.connection_status_changed.emit(False)
                return

        try:
            self._cm904.reset_input_buffer()
        except (serial.SerialException, OSError) as e:
            print(f"[DEBUG] Error limpiando buffer serial: {e}")
            self.connection_status_changed.emit(False)
            self._cm904 = None
            return

        # Envío de trama compacta: A<pwm>B<pwm>C<pwm>D<pwm>E<pwm>F<pwm>\n
        try:
            frame = self._build_command_frame(valorm)
            self._cm904.write(frame)
            self._cm904.flush()
        except (serial.SerialException, OSError) as e:
            print(f"[DEBUG] Error al escribir en serial: {e}")
            self.connection_status_changed.emit(False)
            try:
                if self._cm904:
                    self._cm904.close()
            except (serial.SerialException, OSError):
                pass
            self._cm904 = None
            return

        # Recepción y parseo de telemetría
        try:
            result = self._read_and_filter()
            if result is None:
                return

            self._last_positions, self._last_temperaturas = result

            self.data_received.emit(
                self._last_positions.copy(), self._last_temperaturas.copy())

<<<<<<< HEAD
        except Exception as e:
            print(f"Error lectura: {e}")
            self.connection_status_changed.emit(False)
            try:
                if self._cm904:
                    self._cm904.close()
            except Exception:
                pass
=======
        except (serial.SerialException, OSError, UnicodeDecodeError) as e:
            print(f"[DEBUG] Error en lectura de telemetría ({type(e).__name__}): {e}")
            self.connection_status_changed.emit(False)
>>>>>>> 1825586cf103f63ef7f9c90d4540b2f568c648da
            self._cm904 = None

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
<<<<<<< HEAD
        Lee una linea del puerto serial, parsea y filtra la telemetria.

        Integra lectura, parseo regex, deteccion de tramas nulas,
        filtro anti-ruido electromagnetico con escape de seguridad
        (si un salto >35° persiste mas de 4 tramas, se acepta como movimiento real).
=======
        Lee una ráfaga de telemetría disponible sin bloquear el hilo serial.
>>>>>>> 1825586cf103f63ef7f9c90d4540b2f568c648da

        Returns:
            tuple[list, list] | None: (posiciones, temperaturas) o None si no hay datos validos.
        """
<<<<<<< HEAD
        try:
            if not self._cm904.in_waiting:
                return None
        except Exception:
            self.connection_status_changed.emit(False)
            self._cm904 = None
            return None
=======
        timeout = 1
        start = time.time()
        data = b""
        while time.time() - start < timeout:
            try:
                available = self._cm904.in_waiting
            except (serial.SerialException, OSError):
                print("[DEBUG] Puerto serial perdido durante lectura de in_waiting")
                self.connection_status_changed.emit(False)
                self._cm904 = None
                return ""
>>>>>>> 1825586cf103f63ef7f9c90d4540b2f568c648da

        try:
            line = self._cm904.readline().decode('ascii', errors='ignore').strip()
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

        # Deteccion de tramas nulas / caidas de tension
        if all(v is not None and abs(v) < 0.001 for v in temp_pos[:4]):
            return list(self._last_valid_positions), list(self._last_temperaturas)

        # Filtro anti-ruido electromagnetico con escape de seguridad
        trama_valida = True
        for i in range(6):
            if temp_pos[i] is not None:
                diff = abs(temp_pos[i] - self._last_valid_positions[i])
                if diff > 35.0:
                    self._jump_freeze_count[i] += 1
                    if self._jump_freeze_count[i] <= 4:
                        trama_valida = False
                else:
                    self._jump_freeze_count[i] = 0

        if not trama_valida:
            return list(self._last_valid_positions), list(self._last_temperaturas)

        # Actualizacion limpia de la telemetria
        positions = list(self._last_valid_positions)
        for i in range(6):
            if temp_pos[i] is not None:
                positions[i] = temp_pos[i]
                self._last_valid_positions[i] = temp_pos[i]

        return positions, temperatures

<<<<<<< HEAD
=======
    def _filter_positions(self, positions: list) -> list:
        """
        Filtra tramas nulas y saltos electromagnéticos de la telemetría física.

        Args:
            positions (list): Lecturas crudas de posición para los motores A-F.

        Returns:
            list: Posiciones validadas y persistentes para publicar al sistema.
        """
        if all(abs(value) < 0.001 for value in positions[:4]):
            return list(self._last_valid_positions)

        valid_frame = True
        for index, position in enumerate(positions):
            difference = abs(position - self._last_valid_positions[index])
            if difference > 35.0:
                self._jump_freeze_count[index] += 1
                if self._jump_freeze_count[index] <= 4:
                    valid_frame = False
            else:
                self._jump_freeze_count[index] = 0

        if not valid_frame:
            return list(self._last_valid_positions)

        self._last_valid_positions = list(positions)
        return list(positions)

>>>>>>> 1825586cf103f63ef7f9c90d4540b2f568c648da
    def stop(self):
        """
        Detiene el hilo de ejecución y cierra el puerto serial de forma segura.
        """
        self._running = False
        try:
            if self._cm904 and getattr(self._cm904, 'is_open', False):
                self._cm904.close()
        except (serial.SerialException, OSError):
            pass
        self.connection_status_changed.emit(False)
        self.quit()
        self.wait()
