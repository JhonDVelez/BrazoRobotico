import serial
import threading
from PyQt6.QtCore import QObject, pyqtSignal

class SerialPortManager(QObject):
    """Gestor centralizado para la comunicación serial."""
    _instance = None
    
    def __init__(self):
        super().__init__()
        self._serial = None
        self._com = None
        self._lock = threading.Lock()
        self._io_lock = threading.Lock()
        self._active_worker = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def request_access(self, com, owner_id):
        """Solicita acceso al puerto serial."""
        with self._lock:
            print(f"[DEBUG] [SerialPortManager] {owner_id} solicitando acceso a {com}. Actualmente activo: {self._active_worker}")
            if self._active_worker == owner_id:
                return True
            
            # Si hay otro, cerrarlo
            if self._serial and self._serial.is_open:
                print(f"[DEBUG] [SerialPortManager] Cerrando puerto para {self._active_worker} antes de dar acceso a {owner_id}")
                self._serial.close()
            
            try:
                self._serial = serial.Serial(com, 9600, timeout=1)
                self._active_worker = owner_id
                self._com = com
                print(f"[SerialPortManager] Acceso concedido a {owner_id} en {com}")
                return True
            except Exception as e:
                print(f"[SerialPortManager] Error abriendo {com}: {e}")
                self._serial = None
                self._active_worker = None
                return False

    def release_access(self, owner_id):
        """Libera el puerto serial."""
        with self._lock:
            if self._active_worker == owner_id:
                if self._serial and self._serial.is_open:
                    self._serial.reset_input_buffer()
                    self._serial.reset_output_buffer()
                    self._serial.close()
                self._serial = None
                self._active_worker = None
                print(f"[SerialPortManager] Acceso liberado por {owner_id}")

    def is_active(self, owner_id):
        with self._lock:
            return self._active_worker == owner_id

    def get_serial(self):
        return self._serial

    def safe_write(self, data):
        with self._io_lock:
            if self._serial and self._serial.is_open:
                self._serial.write(data)
                self._serial.flush()

    def safe_readline(self):
        with self._io_lock:
            if self._serial and self._serial.is_open:
                return self._serial.readline()
            return b""

    def get_in_waiting(self):
        with self._io_lock:
            if self._serial and self._serial.is_open:
                return self._serial.in_waiting
            return 0
