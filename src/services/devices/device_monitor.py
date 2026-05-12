"""
Módulo abstracto para monitoreo de dispositivos multiplataforma.
Abstrae la detección de cambios de dispositivos entre Windows y Linux.
"""

import sys
import threading
from abc import ABC, abstractmethod
from PyQt6.QtCore import QTimer, QAbstractNativeEventFilter


class DeviceMonitor(ABC):
    """Clase abstracta para monitoreo de dispositivos."""

    @abstractmethod
    def install_filter(self, app_instance):
        """Instala el filtro de eventos de dispositivos."""

    @abstractmethod
    def uninstall_filter(self):
        """Desinstala el filtro de eventos de dispositivos."""


class WindowsDeviceMonitor(DeviceMonitor):
    """Monitoreo de dispositivos para Windows usando win32con."""

    def __init__(self, serial_callback, camera_callback):
        self.serial_callback = serial_callback
        self.camera_callback = camera_callback
        self._event_filter = None

    def install_filter(self, app_instance):
        """Instala el filtro de eventos nativos de Windows."""
        try:
            self._event_filter = WinDeviceEventFilter(
                self.serial_callback,
                self.camera_callback
            )
            app_instance.installNativeEventFilter(self._event_filter)
        except ImportError:
            print("⚠️  win32con no está disponible. Instala: pip install pywin32")

    def uninstall_filter(self):
        """Desinstala el filtro de eventos nativos."""


class WinDeviceEventFilter(QAbstractNativeEventFilter):
    """Filtro de eventos nativos para Windows."""

    DBT_DEVTYP_PORT = 0x00000003

    def __init__(self, serial_callback, camera_callback):
        super().__init__()
        self.serial_callback = serial_callback
        self.camera_callback = camera_callback

    def nativeEventFilter(self, _eventType, message):
        """Filtra eventos nativos de Windows."""
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
                        QTimer.singleShot(0, self.serial_callback)

                elif msg.wParam == win32con.DBT_DEVNODES_CHANGED:
                    QTimer.singleShot(0, self.camera_callback)
        except ImportError:
            pass

        return False, 0


class LinuxDeviceMonitor(DeviceMonitor):
    """Monitoreo de dispositivos para Linux usando pyudev."""

    def __init__(self, serial_callback, camera_callback):
        self.serial_callback = serial_callback
        self.camera_callback = camera_callback
        self._monitor_thread = None
        self._should_run = False

    def install_filter(self, app_instance):
        """Inicia el monitoreo de dispositivos en Linux."""
        try:
            import pyudev
            self._should_run = True
            self._monitor_thread = threading.Thread(
                target=self._monitor_devices,
                daemon=True
            )
            self._monitor_thread.start()
        except ImportError:
            print("⚠️  pyudev no está instalado. Instala con: pip install pyudev")

    def uninstall_filter(self):
        """Detiene el monitoreo de dispositivos."""
        self._should_run = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2)

    def _monitor_devices(self):
        """Monitorea eventos de dispositivos en Linux."""
        try:
            import pyudev
            context = pyudev.Context()
            monitor = pyudev.Monitor.from_netlink(context)
            monitor.filter_by('tty')
            monitor.start()

            for device in monitor:
                if not self._should_run:
                    break

                action = device.action
                dev_path = device.get('DEVPATH', '').lower()

                if 'tty' in dev_path and action in ('add', 'remove'):
                    QTimer.singleShot(0, self.serial_callback)

                if 'video' in dev_path and action in ('add', 'remove', 'change'):
                    QTimer.singleShot(0, self.camera_callback)

        except Exception as e:
            print(f"❌ Error en monitoreo de dispositivos Linux: {e}")


class CameraEventFilterLinux(DeviceMonitor):
    """Versión simplificada de detección de cámaras para Linux."""

    def __init__(self, camera_callback):
        self.camera_callback = camera_callback
        self._monitor_thread = None
        self._should_run = False

    def install_filter(self, app_instance):
        """Inicia el monitoreo de cámaras en Linux."""
        try:
            import pyudev
            self._should_run = True
            self._monitor_thread = threading.Thread(
                target=self._monitor_cameras,
                daemon=True
            )
            self._monitor_thread.start()
        except ImportError:
            print("⚠️  pyudev no está instalado. Instala con: pip install pyudev")

    def uninstall_filter(self):
        """Detiene el monitoreo de cámaras."""
        self._should_run = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2)

    def _monitor_cameras(self):
        """Monitorea eventos de cámaras en Linux."""
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
                    QTimer.singleShot(0, self.camera_callback)

        except Exception as e:
            print(f"❌ Error en monitoreo de cámaras Linux: {e}")


class DummyDeviceMonitor(DeviceMonitor):
    """Monitor dummy para sistemas operativos no soportados."""

    def install_filter(self, app_instance):
        print("⚠️  Monitoreo de dispositivos no soportado en este SO")

    def uninstall_filter(self):
        pass


def get_device_monitor(serial_callback=None, camera_callback=None, camera_only=False):
    """
    Factory para obtener el monitor de dispositivos apropiado según el SO.

    Args:
        serial_callback: Función a llamar cuando se detecta cambio en puerto serial
        camera_callback: Función a llamar cuando se detecta cambio en cámara
        camera_only: Si True, solo monitorea cámaras (para calibration_window y color_window)

    Returns:
        DeviceMonitor: Instancia del monitor de dispositivos apropiado
    """
    if sys.platform.startswith('win'):
        return WindowsDeviceMonitor(serial_callback, camera_callback)
    elif sys.platform.startswith('linux'):
        if camera_only:
            return CameraEventFilterLinux(camera_callback)
        return LinuxDeviceMonitor(serial_callback, camera_callback)
    else:
        return DummyDeviceMonitor()
