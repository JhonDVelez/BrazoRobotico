import serial
import threading
from PyQt6.QtCore import QObject, pyqtSignal

class SerialPortManager(QObject):
    """Gestor centralizado para la comunicación serial con limpieza estricta de buffers."""
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
        """Solicita acceso al puerto serial y limpia buffers rigurosamente."""
        with self._lock:
            if self._active_worker == owner_id:
                if self._serial and self._serial.is_open:
                    try:
                        self._serial.reset_input_buffer()
                        self._serial.reset_output_buffer()
                    except Exception:
                        pass
                return True
            
            # Si hay otro propietario, cerrar limpiando buffers primero
            if self._serial and self._serial.is_open:
                try:
                    self._serial.reset_input_buffer()
                    self._serial.reset_output_buffer()
                except Exception:
                    pass
                try:
                    self._serial.close()
                except Exception:
                    pass
            
            try:
                self._serial = serial.Serial(com, 9600, timeout=0.5)
                self._serial.reset_input_buffer()
                self._serial.reset_output_buffer()
                self._active_worker = owner_id
                self._com = com
                return True
            except Exception as e:
                print(f"[SerialPortManager] Error abriendo {com}: {e}")
                self._serial = None
                self._active_worker = None
                return False

    def release_access(self, owner_id):
        """Libera el puerto serial y limpia buffers."""
        with self._lock:
            if self._active_worker == owner_id:
                if self._serial and self._serial.is_open:
                    try:
                        self._serial.reset_input_buffer()
                        self._serial.reset_output_buffer()
                    except Exception:
                        pass
                    try:
                        self._serial.close()
                    except Exception:
                        pass
                self._serial = None
                self._active_worker = None

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
