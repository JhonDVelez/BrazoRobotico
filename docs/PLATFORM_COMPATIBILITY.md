# Compatibilidad Multiplataforma (Windows & Linux)

## Overview

El proyecto ahora es compatible con **Windows** y **Linux** mediante una capa de abstracción para el manejo de eventos de dispositivos.

## Cambios Realizados

### 1. Nuevo módulo: `device_monitor.py`
Ubicación: `src/gui/device_monitor.py`

Este módulo proporciona:
- **Clase abstracta `DeviceMonitor`**: Define la interfaz común
- **`WindowsDeviceMonitor`**: Implementación para Windows usando `win32con`
- **`LinuxDeviceMonitor`**: Implementación para Linux usando `pyudev`
- **`CameraEventFilterLinux`**: Monitoreo específico de cámaras en Linux
- **Factory `get_device_monitor()`**: Retorna la implementación correcta según el SO

### 2. Cambios en `app_window.py`
- ✅ Importa `get_device_monitor` en lugar de `win32con`
- ✅ Usa `self._device_monitor` en lugar de `self._dev_filter`
- ✅ Eliminadas clases específicas de Windows (`DEV_BROADCAST_HDR`, `DeviceEventFilter`)

### 3. Cambios en `calibration_window.py`
- ✅ Importa `get_device_monitor` en lugar de `win32con`
- ✅ Usa `self._device_monitor` en lugar de `self._dev_filter`
- ✅ Método `uninstall_filter()` llamado en `closeEvent()`

### 4. Actualización de dependencias
En `requirements.txt`:
- `pyudev==0.24.1` (necesario solo en Linux)
- En Windows puede estar comentado sin afectar la funcionalidad

## Configuración por Plataforma

### Windows
```bash
# Sin cambios - usa win32con (ya incluido en pywin32)
pip install -r requirements.txt
python src/main.py
```

### Linux (Ubuntu/Debian)
```bash
# Instalar dependencias del sistema
sudo apt-get install libudev-dev

# Instalar dependencias Python
pip install -r requirements.txt

# O instalar pyudev específicamente
pip install pyudev

# Ejecutar
python src/main.py
```

### Linux (Fedora/RHEL)
```bash
# Instalar dependencias del sistema
sudo dnf install systemd-devel

# Instalar dependencias Python
pip install pyudev

# Ejecutar
python src/main.py
```

## Eventos Monitoreados

### Windows
- **Puertos Seriales**: `WM_DEVICECHANGE` + `DBT_DEVICEARRIVAL/DBT_DEVICEREMOVECOMPLETE`
- **Cámaras**: `WM_DEVICECHANGE` + `DBT_DEVNODES_CHANGED`

### Linux
- **Puertos Seriales**: Monitorea `/dev/tty*` (ttyUSB, ttyACM, etc.)
- **Cámaras**: Monitorea dispositivos video4linux (`/dev/video*`)

## Testing Multiplataforma

### En Windows
```python
# El filtro de eventos nativos debe activarse automáticamente
# Prueba conectando/desconectando:
# - Puerto serial (Arduino, microcontrolador)
# - Cámara USB
```

### En Linux
```python
# El monitoreo pyudev debe activarse automáticamente
# Prueba conectando/desconectando:
# - Puerto serial: ls -la /dev/ttyUSB* o /dev/ttyACM*
# - Cámara: ls -la /dev/video*
```

## Solución de Problemas

### Error: `ImportError: No module named 'win32con'`
**En Linux**: Esto es normal y esperado. El código detecta automáticamente el SO.

### Error: `ImportError: No module named 'pyudev'`
**En Linux**: Instala pyudev:
```bash
pip install pyudev
```

### Los eventos no se detectan en Linux
1. Verifica que `pyudev` esté instalado:
   ```bash
   python -c "import pyudev; print('OK')"
   ```
2. Verifica los permisos de acceso a `/dev`:
   ```bash
   # Para puertos seriales
   ls -la /dev/ttyUSB*
   
   # Para cámaras
   ls -la /dev/video*
   ```

## Compatibilidad SO

| Sistema Operativo | Estado | Notas |
|---|---|---|
| Windows 10/11 | ✅ Totalmente soportado | Usa win32con |
| Ubuntu 20.04+ | ✅ Totalmente soportado | Requiere pyudev |
| Fedora 38+ | ✅ Totalmente soportado | Requiere systemd-devel |
| Debian 11+ | ✅ Totalmente soportado | Requiere libudev-dev |
| macOS | ⚠️ Parcialmente | Usa DummyDeviceMonitor (no hay eventos) |

## Ejemplos de Uso

### Uso directo (si necesitas el monitor en otro lugar)
```python
from src.gui.device_monitor import get_device_monitor

def on_serial_event():
    print("Puerto serial conectado/desconectado")

def on_camera_event():
    print("Cámara conectada/desconectada")

# Obtener el monitor apropiado
monitor = get_device_monitor(on_serial_event, on_camera_event)

# Instalar en la aplicación
monitor.install_filter(QCoreApplication.instance())

# Limpiar cuando termine
monitor.uninstall_filter()
```

### Solo monitoreo de cámaras
```python
monitor = get_device_monitor(
    camera_callback=on_camera_event,
    camera_only=True
)
monitor.install_filter(QCoreApplication.instance())
```

## Notas Técnicas

1. **Threading**: Linux usa threads para monitorear dispositivos (pyudev.Monitor es bloqueante)
2. **Callbacks**: Se invocan con `QTimer.singleShot()` para mantener thread-safety con Qt
3. **Performance**: Mínimo overhead, los eventos solo se generan cuando cambian dispositivos
4. **Logging**: Actualmente imprime en consola con `print()` - puedes agregar logging profesional si lo necesitas

## Futuras Mejoras

- [ ] Agregar logging con `logging` module
- [ ] Soportar macOS con `pyobjc`
- [ ] Agregar tests unitarios para ambas plataformas
- [ ] Crear instaladores específicos por SO
