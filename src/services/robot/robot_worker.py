"""
Modulo para la comunicacion serial con el hardware del robot.

Este modulo define la clase RobotWorker, la cual gestiona el envio de comandos
y la recepcion de telemetria (posicion y temperatura) desde la placa de
control (OpenCM9.04) utilizando un hilo dedicado.

Conexiones:
    - Utiliza `PhysicalSignalManager` para reportar el estado de conexion.
    - Emite `data_received` al recibir telemetria valida.
    - Recibe datos mediante una cola (`queue.Queue`) para evitar bloqueos.
"""

import re
import time
import queue
import serial
from PyQt6.QtCore import QThread, pyqtSignal

class RobotWorker(QThread):
    """
    Worker encargado de la comunicacion serial bidireccional con el robot.

    Gestiona un buffer de recepcion, procesa expresiones regulares para extraer
    datos de telemetria y utiliza una cola de prioridad para los comandos de salida.

    Attributes:
        data_received (pyqtSignal): Señal que envia (lista_posiciones, lista_temperaturas).
        connection_status_changed (pyqtSignal): Señal que informa cambio en el estado serie.
    """
    # Definimos señales locales para el Controller
    data_received = pyqtSignal(list, list)
    connection_status_changed = pyqtSignal(bool)

    def __init__(self, com: str, compensator=None):
        """
        Inicializa el worker serial y abre la conexion con el puerto COM.

        Args:
            com (str): Nombre del puerto serial (e.g., 'COM3' o '/dev/ttyACM0').
            compensator (RobotCompensator, optional): Objeto para ajustar comandos de salida.
        """
        super().__init__()
        self._com = com
        self._cm904 = None
        self._compensator = compensator
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

        self._recv_buffer = ""
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
        Verifica si hay una conexion serial activa.

        Returns:
            bool: True si esta conectado.
        """
        return self._cm904 is not None and getattr(self._cm904, 'is_open', False)

    def get_last_positions(self) -> list:
        """
        Obtiene la ultima lectura de posiciones de los servos.

        Returns:
            list: Lista de 6 posiciones (grados) o None.
        """
        return self._last_positions.copy()

    def get_last_temperatures(self) -> list:
        """
        Obtiene la ultima lectura de temperaturas de los motores.

        Returns:
            list: Lista de 6 temperaturas (Celsius) o None.
        """
        return self._last_temperaturas.copy()

    def enqueue_data(self, valorm):
        """
        Añade nuevos comandos a la cola de envio.

        Descarta comandos anteriores que aun no se hayan procesado para
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
        Bucle principal del hilo de comunicacion.

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
        Realiza la transaccion de bajo nivel: envia PWMs y recibe telemetria.

        Args:
            valorm (list): Comandos de posicion originales.
        """
        # Intercepcion de datos antes del procesamiento de envio (e.g. compensacion de backlash)
        if self._compensator:
            valorm = self._compensator.process_data(valorm)

        if not all(0 <= x <= 300 for x in valorm):
            print("Error de envio de datos: Valores fuera de rango")
            return

        # Reconexion automatica si el puerto se cerro
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
        except Exception as e:
            print(f"Error limpiando buffer: {e}")
            self.connection_status_changed.emit(False)
            self._cm904 = None
            return

        # Envio de trama compacta: A<pwm>B<pwm>C<pwm>D<pwm>E<pwm>F<pwm>\n
        try:
            frame = self._build_command_frame(valorm)
            self._cm904.write(frame)
            self._cm904.flush()
        except (serial.SerialException, OSError) as e:
            print(f"Error al escribir en serial: {e}")
            self.connection_status_changed.emit(False)
            try:
                if self._cm904:
                    self._cm904.close()
            except Exception:
                pass
            self._cm904 = None
            return

        # Recepcion y parseo de telemetria
        try:
            raw_frame = self._read_telemetry_frame()
            if not raw_frame:
                return

            parsed = self._parse_telemetry(raw_frame)
            if parsed is None:
                return

            positions, temperatures = parsed
            self._last_positions = self._filter_positions(positions)
            self._last_temperaturas = temperatures

            # Notificacion de nuevos datos locales
            self.data_received.emit(
                self._last_positions.copy(), self._last_temperaturas.copy())

        except Exception as e:
            print(f"Error lectura: {e}")

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

    def _read_telemetry_frame(self) -> str:
        """
        Lee una rafaga de telemetria disponible sin bloquear el hilo serial.

        Returns:
            str: Texto ASCII acumulado desde el puerto serie.
        """
        timeout = 0.03
        start = time.time()
        data = b""
        while time.time() - start < timeout:
            try:
                available = self._cm904.in_waiting
            except Exception:
                self.connection_status_changed.emit(False)
                self._cm904 = None
                return ""

            if available:
                chunk = self._cm904.read(available)
                if chunk:
                    data += chunk
                    if b'\n' in data:
                        break
            else:
                time.sleep(0.001)

        return data.decode('ascii', errors='ignore').strip() if data else ""

    def _parse_telemetry(self, frame: str):
        """
        Extrae posiciones y temperaturas desde una trama completa del robot.

        Args:
            frame (str): Trama con tokens tipo `A150.0TA35` para motores A-F.

        Returns:
            tuple[list, list] | None: Posiciones y temperaturas si hay 6 motores.
        """
        pattern = re.compile(r"([A-F])(\d+\.?\d*)T[A-F](\d+)")
        matches = pattern.findall(frame)
        if len(matches) < 6:
            return None

        positions = [None] * 6
        temperatures = list(self._last_temperaturas)
        for motor_char, position_value, temperature_value in matches:
            index = ord(motor_char) - ord('A')
            if 0 <= index < 6:
                positions[index] = float(position_value)
                temperatures[index] = int(temperature_value)

        if any(position is None for position in positions):
            return None

        return positions, temperatures

    def _filter_positions(self, positions: list) -> list:
        """
        Filtra tramas nulas y saltos electromagneticos de la telemetria fisica.

        Args:
            positions (list): Lecturas crudas de posicion para los motores A-F.

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

    def stop(self):
        """
        Detiene el hilo de ejecucion y cierra el puerto serial de forma segura.
        """
        self._running = False
        try:
            if self._cm904 and getattr(self._cm904, 'is_open', False):
                self._cm904.close()
        except Exception:
            pass
        self.connection_status_changed.emit(False)
        self.quit()
        self.wait()
