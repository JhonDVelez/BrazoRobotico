"""
Módulo abstracto para monitoreo de dispositivos multiplataforma.

Abstrae la detección de cambios de dispositivos entre Windows y Linux.
Proporciona una fábrica (:func:`get_device_monitor`) que selecciona
la implementación adecuada según el sistema operativo.

Conexiones:
    - Utilizado por el módulo principal para detectar conexión/desconexión
      de cámaras y puertos serie en tiempo real.
    - Los callbacks se invocan via señales Qt con queued connection,
      marshaling automático al hilo del receptor.
"""

import sys
import threading
from abc import ABC, ABCMeta, abstractmethod
from PyQt6.QtCore import QObject, pyqtSignal, QAbstractNativeEventFilter, QCoreApplication


# Combined metaclass: ABCMeta + QObject's metaclass
class _QObjectABCMeta(ABCMeta, type(QObject)):
    """Metaclass combining ABC and QObject metaclasses."""
    pass


class _QObjectABC(QObject, metaclass=_QObjectABCMeta):
    """QObject con metaclass ABC para herencia múltiple."""
    pass


class DeviceMonitor(ABC):
    """Clase abstracta base para el monitoreo de dispositivos."""

    @abstractmethod
    def install_filter(self, app_instance):
        """Instala el filtro de eventos de dispositivos.

        Args:
            app_instance (QApplication): Instancia de la aplicacion Qt.
        """

    @abstractmethod
    def uninstall_filter(self):
        """Desinstala el filtro de eventos de dispositivos."""


class WindowsDeviceMonitor(_QObjectABC, DeviceMonitor):
    """Monitoreo de dispositivos para Windows usando win32con.

    Utiliza un filtro de eventos nativos de Windows para detectar
    cambios en puertos serie y dispositivos de video.
    """

    serial_changed = pyqtSignal()
    camera_changed = pyqtSignal()

    def __init__(self, serial_callback=None, camera_callback=None):
        """
        Args:
            serial_callback (callable): Funcion a invocar al cambiar puertos serie.
            camera_callback (callable): Funcion a invocar al cambiar camaras.
        """
        QObject.__init__(self)
        DeviceMonitor.__init__(self)
        self._serial_callback = serial_callback
        self._camera_callback = camera_callback
        self._event_filter = None

    def connect_callbacks(self, serial_callback, camera_callback):
        """Conecta callbacks a las señales Qt.

        Args:
            serial_callback (callable): Funcion a invocar al cambiar puertos serie.
            camera_callback (callable): Funcion a invocar al cambiar camaras.
        """
        if serial_callback:
            self.serial_changed.connect(serial_callback)
        if camera_callback:
            self.camera_changed.connect(camera_callback)

    def install_filter(self, app_instance):
        """Instala el filtro de eventos nativos de Windows.

        Args:
            app_instance (QApplication): Instancia de la aplicación Qt.
        """
        try:
            self._event_filter = WinDeviceEventFilter(self)
            app_instance.installNativeEventFilter(self._event_filter)
        except ImportError:
            print("win32con no está disponible. Instala: pip install pywin32")

    def uninstall_filter(self):
        """Desinstala el filtro de eventos nativos."""
        if self._event_filter:
            app = QCoreApplication.instance()
            if app:
                app.removeNativeEventFilter(self._event_filter)
            self._event_filter = None


class WinDeviceEventFilter(QAbstractNativeEventFilter):
    """Filtro de eventos nativos para Windows.

    Captura el mensaje WM_DEVICECHANGE y distingue entre cambios
    en puertos serie (DBT_DEVTYP_PORT) y cambios en el árbol
    de dispositivos (DBT_DEVNODES_CHANGED).
    """

    DBT_DEVTYP_PORT = 0x00000003

    def __init__(self, parent_monitor):
        """
        Args:
            parent_monitor (WindowsDeviceMonitor): Referencia al monitor padre.
        """
        super().__init__()
        self._parent = parent_monitor

    def nativeEventFilter(self, _eventType, message):
        """Filtra eventos nativos de Windows.

        Args:
            _eventType: Tipo de evento nativo (no utilizado).
            message: Mensaje nativo de Windows.

        Returns:
            tuple: (bool, int) indicando si el evento fue manejado.
        """
        try:
            import win32con
            from ctypes import wintypes, cast, POINTER
            import ctypes

            msg = wintypes.MSG.from_address(message.__int__())

            if msg.message == win32con.WM_DEVICECHANGE:
                if msg.wParam in (win32con.DBT_DEVICEARRIVAL,
                                  win32con.DBT_DEVICEREMOVECOMPLETE):

                    class DEV_BROADCAST_HDR(ctypes.Structure):
                        _fields_ = [
                            ("dbch_size", wintypes.DWORD),
                            ("dbch_devicetype", wintypes.DWORD),
                            ("dbch_reserved", wintypes.DWORD),
                        ]

                    hdr = cast(msg.lParam, POINTER(DEV_BROADCAST_HDR)).contents
                    if hdr.dbch_devicetype == self.DBT_DEVTYP_PORT:
                        self._parent.serial_changed.emit()

                elif msg.wParam == win32con.DBT_DEVNODES_CHANGED:
                    self._parent.camera_changed.emit()
        except ImportError:
            pass

        return False, 0


class LinuxDeviceMonitor(_QObjectABC, DeviceMonitor):
    """Monitoreo de dispositivos para Linux usando pyudev.

    Utiliza pyudev para monitorizar eventos de dispositivos tty
    y video4linux en un hilo separado.
    """

    camera_changed = pyqtSignal()
    serial_changed = pyqtSignal()

    def __init__(self, serial_callback=None, camera_callback=None):
        """
        Args:
            serial_callback (callable): Función al cambiar puertos serie.
            camera_callback (callable): Función al cambiar cámaras.
        """
        QObject.__init__(self)
        DeviceMonitor.__init__(self)
        self._serial_callback = serial_callback
        self._camera_callback = camera_callback
        self._monitor_thread = None
        self._should_run = False

    def connect_callbacks(self, serial_callback, camera_callback):
        """Conecta callbacks a las señales Qt.

        Args:
            serial_callback (callable): Función a invocar al cambiar puertos serie.
            camera_callback (callable): Función a invocar al cambiar cámaras.
        """
        if serial_callback:
            self.serial_changed.connect(serial_callback)
        if camera_callback:
            self.camera_changed.connect(camera_callback)

    def install_filter(self, app_instance):
        """Inicia el monitoreo de dispositivos en Linux.

        Args:
            app_instance (QApplication): Instancia de la aplicación Qt.
        """
        try:
            import pyudev
            self._should_run = True
            self._monitor_thread = threading.Thread(
                target=self._monitor_devices,
                daemon=True
            )
            self._monitor_thread.start()
        except ImportError:
            print("pyudev no está instalado. Instala con: pip install pyudev")

    def uninstall_filter(self):
        """Detiene el monitoreo de dispositivos."""
        self._should_run = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2)

    def _monitor_devices(self):
        """Monitorea eventos de dispositivos en Linux.

        Escucha eventos de dispositivos tty y video4linux
        y notifica a traves de los callbacks correspondientes.
        """
        try:
            import pyudev
            context = pyudev.Context()
            monitor = pyudev.Monitor.from_netlink(context)
            monitor.filter_by(subsystem='video4linux')
            monitor.filter_by(subsystem='tty')
            monitor.start()

            for device in iter(monitor.poll, None):
                if not self._should_run:
                    break

                subsystem = device.subsystem
                if subsystem == 'video4linux':
                    self.camera_changed.emit()
                elif subsystem == 'tty':
                    self.serial_changed.emit()

        except Exception as e:
            print(f"[DEBUG] Error en monitoreo de dispositivos Linux ({type(e).__name__}): {e}")


class CameraEventFilterLinux(_QObjectABC, DeviceMonitor):
    """Versión simplificada de detección de cámaras para Linux.

    Monitorea exclusivamente eventos de dispositivos video4linux.
    """

    camera_changed = pyqtSignal()

    def __init__(self, camera_callback=None):
        """
        Args:
            camera_callback (callable): Función al cambiar cámaras.
        """
        QObject.__init__(self)
        DeviceMonitor.__init__(self)
        self._camera_callback = camera_callback
        self._monitor_thread = None
        self._should_run = False

    def connect_callbacks(self, serial_callback, camera_callback):
        """Conecta callbacks a las señales Qt.

        Args:
            serial_callback: Ignored (camera-only monitor).
            camera_callback (callable): Funcion a invocar al cambiar camaras.
        """
        if camera_callback:
            self.camera_changed.connect(camera_callback)

    def install_filter(self, app_instance):
        """Inicia el monitoreo de camaras en Linux.

        Args:
            app_instance (QApplication): Instancia de la aplicación Qt.
        """
        try:
            import pyudev
            self._should_run = True
            self._monitor_thread = threading.Thread(
                target=self._monitor_cameras,
                daemon=True
            )
            self._monitor_thread.start()
        except ImportError:
            print("pyudev no está instalado. Instala con: pip install pyudev")

    def uninstall_filter(self):
        """Detiene el monitoreo de cámaras."""
        self._should_run = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2)

    def _monitor_cameras(self):
        """Monitorea eventos de cámaras en Linux.

        Escucha eventos de dispositivos video4linux (add, remove, change).
        """
        try:
            import pyudev
            context = pyudev.Context()
            monitor = pyudev.Monitor.from_netlink(context)
            monitor.filter_by('video4linux')
            monitor.start()

            for device in monitor:
                if not self._should_run:
                    break

                action = device.action
                if action in ('add', 'remove', 'change'):
                    self.camera_changed.emit()

        except Exception as e:
            print(f"[DEBUG] Error en monitoreo de cámaras Linux ({type(e).__name__}): {e}")


class DummyDeviceMonitor(DeviceMonitor):
    """Monitor dummy para sistemas operativos no soportados."""

    def install_filter(self, app_instance):
        """
        Args:
            app_instance (QApplication): Instancia de la aplicación Qt.
        """
        print("Monitoreo de dispositivos no soportado en este SO")

    def uninstall_filter(self):
        pass


def get_device_monitor(serial_callback=None, camera_callback=None, camera_only=False):
    """
    Fábrica para obtener el monitor de dispositivos apropiado según el SO.

    Args:
        serial_callback (callable, optional): Función a llamar cuando se detecta
            cambio en puerto serial.
        camera_callback (callable, optional): Función a llamar cuando se detecta
            cambio en cámara.
        camera_only (bool, optional): Si True, solo monitorea cámaras
            (para calibration_window y color_window).

    Returns:
        DeviceMonitor: Instancia del monitor de dispositivos apropiado para
        el sistema operativo actual.
    """
    if sys.platform.startswith('win'):
        monitor = WindowsDeviceMonitor(serial_callback, camera_callback)
        monitor.connect_callbacks(serial_callback, camera_callback)
        return monitor
    elif sys.platform.startswith('linux'):
        if camera_only:
            monitor = CameraEventFilterLinux(camera_callback)
        else:
            monitor = LinuxDeviceMonitor(serial_callback, camera_callback)
        monitor.connect_callbacks(serial_callback, camera_callback)
        return monitor
    else:
        return DummyDeviceMonitor()
