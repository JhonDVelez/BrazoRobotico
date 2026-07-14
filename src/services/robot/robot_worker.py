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
import time
import serial
import threading
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
        self._lock = threading.Lock()
        self._telemetry_counter = 0

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
        with self._lock:
            return list(self._last_positions)

    def get_last_temperatures(self) -> list:
        """
        Obtiene la última lectura de temperaturas de los motores.

        Returns:
            list: Lista de 6 temperaturas (Celsius) o None.
        """
        with self._lock:
            return list(self._last_temperaturas)

    def get_last_positions_locked(self) -> list:
        """
        Lectura segura (bajo cerrojo) de posiciones de servos.

        Returns:
            list: Copia de 6 posiciones (grados).
        """
        with self._lock:
            return list(self._last_positions)

    def get_last_temperatures_locked(self) -> list:
        """
        Lectura segura (bajo cerrojo) de temperaturas de motores.

        Returns:
            list: Copia de 6 temperaturas (Celsius).
        """
        with self._lock:
            return list(self._last_temperaturas)

    def get_telemetry_counter(self) -> int:
        """
        Devuelve un contador incremental de telemetria procesada.

        Permite a los consumidores detectar de forma atomica si hay
        datos nuevos sin necesidad de comparar listas completas.

        Returns:
            int: Numero de tramas validas procesadas.
        """
        with self._lock:
            return self._telemetry_counter

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
        Bucle principal del hilo de comunicación continuo y asíncrono.

        En cada ciclo intenta extraer un comando de la cola de envío con un
        tiempo de espera corto; si lo hay, lo transmite. De forma
        independiente, lee de inmediato cualquier telemetria pendiente en el
        buffer de entrada del puerto serie y la procesa, actualizando el
        estado interno bajo cerrojo. Esto garantiza telemetria en tiempo real
        y a la maxima velocidad del hardware, sin bloqueos ni congelamiento.
        """
        while self._running:
            try:
                valorm = self._send_queue.get(timeout=0.005)
            except queue.Empty:
                valorm = None

            if valorm is not None:
                self._send_command(valorm)

            self._read_telemetry_continuous()

    def _send_command(self, valorm):
        """
        Transmite una trama de comando al microcontrolador sin descartar
        la telemetria pendiente en el buffer de entrada.

        Args:
            valorm (list): Comandos de posición originales (grados 0-300).
        """
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

    def _read_telemetry_continuous(self):
        """
        Lee de forma continua las lineas de telemetria disponibles en el
        puerto serie y actualiza el estado interno cuando se completa una
        trama valida de 6 motores. No bloquea: solo procesa lo disponible.
        """
        if self._cm904 is None or not getattr(self._cm904, 'is_open', False):
            return
        try:
            waiting = self._cm904.in_waiting
        except (serial.SerialException, OSError):
            self.connection_status_changed.emit(False)
            self._cm904 = None
            return
        if not waiting:
            return

        while self._cm904.in_waiting:
            try:
                line = self._cm904.readline().decode(
                    'ascii', errors='ignore').strip()
            except (serial.SerialException, OSError):
                self.connection_status_changed.emit(False)
                self._cm904 = None
                return
            if not line:
                continue
            matches = self._TELEMETRY_PATTERN.findall(line)
            if len(matches) >= 6:
                self._update_from_matches(matches)

    def _update_from_matches(self, matches):
        """
        Procesa 6+ coincidencias de telemetria, aplica los filtros anti-ruido
        y de trama nula, y actualiza el estado interno bajo cerrojo.

        Args:
            matches (list): Lista de tuplas (motor, posicion, temperatura).
        """
        temp_pos = [None] * 6
        with self._lock:
            temperatures = list(self._last_temperaturas)
            last_valid = list(self._last_valid_positions)

        for motor_char, position_value, temperature_value in matches:
            idx = ord(motor_char) - ord('A')
            if idx < 6:
                temp_pos[idx] = float(position_value)
                temperatures[idx] = int(temperature_value)

        # Deteccion de tramas nulas / caidas de tension
        if all(v is not None and abs(v) < 0.001 for v in temp_pos[:4]):
            with self._lock:
                positions = list(self._last_valid_positions)
                temps = list(self._last_temperaturas)
            self._emit_telemetry(positions, temps)
            return

        # Filtro anti-ruido electromagnetico con escape de seguridad
        trama_valida = True
        for i in range(6):
            if temp_pos[i] is not None:
                diff = abs(temp_pos[i] - last_valid[i])
                if diff > 35.0:
                    self._jump_freeze_count[i] += 1
                    if self._jump_freeze_count[i] <= 4:
                        trama_valida = False
                else:
                    self._jump_freeze_count[i] = 0

        if not trama_valida:
            with self._lock:
                positions = list(self._last_valid_positions)
                temps = list(self._last_temperaturas)
            self._emit_telemetry(positions, temps)
            return

        # Actualizacion limpia de la telemetria
        positions = list(last_valid)
        for i in range(6):
            if temp_pos[i] is not None:
                positions[i] = temp_pos[i]

        with self._lock:
            self._last_valid_positions = list(positions)
            self._last_positions = list(positions)
            self._last_temperaturas = list(temperatures)
            self._telemetry_counter += 1

        self._emit_telemetry(positions, temperatures)

    def _emit_telemetry(self, positions, temperatures):
        """
        Re-emite la telemetria procesada hacia los suscriptores.

        Args:
            positions (list): Posiciones de servos (grados).
            temperatures (list): Temperaturas de motores (Celsius).
        """
        self.data_received.emit(list(positions), list(temperatures))

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
