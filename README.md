# OpenBotV Studio

<div align="center">

![OpenBotV Studio](src/resources/img/openbotv_v1.png)

**Simulador y estudio de teleoperación para el brazo robótico OpenBotV**

*Proyecto de tesis — Jhon D. Velez & Jeisson I. Sanchez*

`Python 3.13` · `PyQt6` · `Qt Quick 3D` · `PyBullet` · `OpenCV`

</div>

---

## 📖 ¿Qué es OpenBotV Studio?

OpenBotV Studio es una aplicación de escritorio (Windows x64) que integra la
**simulación 3D**, la **física** y la **teleoperación** del brazo robótico
OpenBotV. Permite controlar un gemelo digital del robot (renderizado con
Qt Quick 3D y simulado físicamente con PyBullet), sincronizar sus movimientos
con el robot físico por conexión serie y analizar la telemetría resultante
(gráficas de comparación simulación vs. mundo real, control PID y corrección
de coordenadas por compensación).

## ✨ Funcionalidades

| Modo de control | Descripción |
|---|---|
| **Sliders** | Control manual motor a motor del brazo. |
| **Cinemática** | Control por cinemática directa e inversa (posición/orientación del efector). |
| **Pick & Place** | Toma y colocación de objetos con planificación de movimiento. |

Otros componentes principales:

- **Motor 3D (Qt Quick 3D / QML)**: escena del brazo OpenBotV con sombras, mapas y mallas propias.
- **Física (PyBullet)**: simulación de contacto, colisiones y dinámica con mallas concavas (VHACD).
- **Dominio simulación / físico**: cada modo puede ejecutarse contra el gemelo digital o contra el robot real vía puerto serie (pyserial).
- **Visión (OpenCV)**: integración de cámaras para retroalimentación visual.
- **Telemetría y gráficas**: comparación en vivo entre el estado simulado y el físico, guardado de datos a CSV/Excel y curvas de control PID.
- **Calibración**: corrección de coordenadas mediante tabla de compensación.
- **Interfaz**: sistema de docks (ADS), temas claro/oscuro que siguen el tema de Windows, splash screen con precarga de recursos y notificaciones (toasts y diálogos).

## 💻 Requisitos

- Windows 10 o superior (x64).
- Para ejecutar desde fuente: [Miniconda](https://docs.conda.io/en/latest/miniconda.html) o Anaconda.

## 📦 Instalación (usuario final)

Descarga la última versión desde la sección
[**Releases**](https://github.com/JhonDVelez/OpenBotV-Studio/releases) del
repositorio. Hay dos formatos:

### Opción A — Instalador (recomendada)

1. Descarga `OpenBotV-Studio-Setup-vX.Y.Z.exe`.
2. Ejecútalo: instalará la app en `C:\Program Files\OpenBotV-Studio`
   (requiere permisos de administrador).
3. Opcionalmente marca la casilla de acceso directo en el escritorio.
4. Desinstalación limpia desde *Configuración → Aplicaciones*.

### Opción B — Portable

1. Descarga `OpenBotV-Studio-vX.Y.Z-portable.zip`.
2. Descomprímelo donde quieras (sin instalación, sin registro).
3. Ejecuta `OpenBotV-Studio.exe` que está dentro de la carpeta descomprimida.

> **Datos de la app**: tanto la configuración (`config/`) como los logs
> (`logs/`) se guardan en `~/Documents/OpenBotVStudio/`, independientemente
> de dónde esté instalado el programa.

## 🛠️ Compilación desde fuente

### 1. Preparar el entorno

```powershell
conda env create -f environment.yml
conda activate .venv
```

### 2. Ejecutar en desarrollo

```powershell
python src\main.py
```

### 3. Compilar el ejecutable

El build se automatiza con `installer\build.ps1`, pero también puede hacerse
manualmente paso a paso:

```powershell
# Ejecutable onedir (resultado en dist\OpenBotV-Studio\)
pyinstaller installer\main.spec --noconfirm

# Portable: comprimir el resultado
Compress-Archive -Path dist\OpenBotV-Studio `
    -DestinationPath dist\OpenBotV-Studio-portable.zip -Force

# Instalador: requiere [Inno Setup 7](https://jrsoftware.org/isdl.php)
& "<ruta-a-Inno-Setup>\ISCC.exe" installer\OpenBotV-Studio.iss
```

El spec (`installer\main.spec`) gestiona todo el empaquetado: recursos
(`src/resources`), SVGs de los temas, dependencias de QtQuick3D, icono del exe
y metadatos de versión (`installer\version_info.py`).

## ⚙️ Uso de `installer\build.ps1`

Script de automatización que encadena los pasos anteriores con verificación
de errores. Se ejecuta desde la raíz del proyecto:

```powershell
.\installer\build.ps1              # muestra el menú interactivo
.\installer\build.ps1 -Task All    # sin menú: ejecuta los 3 pasos
```

Al abrirlo sin argumentos aparece este menú:

```
OpenBotV Studio - Build
  [1] Solo PyInstaller       (regenera dist\OpenBotV-Studio)
  [2] Solo Portable          (zip de dist\OpenBotV-Studio)
  [3] Solo Instalador        (Inno Setup)
  [4] Portable + Instalador  (sin recompilar el exe)
  [5] Todo                   (1 + 2 + 3)
  [0] Salir
```

- **[1] Solo PyInstaller**: reconstruye el ejecutable con el código actual.
- **[2] Solo Portable**: genera el zip; requiere que exista `dist\`.
- **[3] Solo Instalador**: genera el Setup con Inno Setup; requiere `dist\`.
- **[4] Portable + Instalador**: empaqueta lo ya compilado sin recompilar.
- **[5] Todo**: la secuencia completa de release.

Detalles de comportamiento:

- Si un paso falla, el script se detiene y muestra el error en rojo antes de
  continuar (evita empaquetar artefactos rotos).
- Si el código de `src\` es más reciente que el exe de `dist\`, avisa para
  que recompiles antes de empaquetar.
- Al finalizar (o tras un error) espera a que presiones una tecla para no
  cerrar la ventana; usa `-NoPause` para ejecutarlo en automatización.

## 🐞 Solución de problemas

Si la aplicación no arranca o se cierra inesperadamente, el log completo de
errores se escribe en:

```
~/Documents/OpenBotVStudio/logs/openbotv_studio.log
```

Abre un [issue](https://github.com/JhonDVelez/OpenBotV-Studio/issues)
incluyendo el contenido de ese archivo.

## 📁 Estructura del repositorio

```
├── src/                  # Código fuente de la aplicación
│   ├── main.py           # Punto de entrada (splash, precarga, arranque)
│   ├── main_window/      # Ventana principal y mixins
│   ├── features/         # Módulos de UI: sliders, cinemática, pick&place,
│   │                     #   gráficas, cámara, simulación, calibración
│   ├── services/         # Servicios: datos, robot (serie), visión,
│   │                     #   simulación, styling, UI
│   └── resources/        # Recursos: QML, mallas, URDF, iconos, imágenes
├── installer/            # main.spec, version_info.py, .iss, build.ps1
├── environment.yml       # Entorno conda reproducible
└── LICENSE.txt           # GNU GPL v3
```

## 📄 Licencia y derechos

Copyright © 2026 **Jhon D. Velez & Jeisson I. Sanchez**

Este programa es software libre: puedes redistribuirlo y/o modificarlo bajo
los términos de la **GNU General Public License** publicada por la Free
Software Foundation, en su versión 3 o (a tu elección) cualquier versión
posterior. Consulta el archivo [`LICENSE.txt`](LICENSE.txt) para el texto
completo.

Este programa se distribuye con la esperanza de que sea útil, pero **sin
ninguna garantía**; sin siquiera la garantía implícita de comerciabilidad o
aptitud para un propósito particular.

**Licencias de terceros**: las bibliotecas empleadas conservan sus propias
licencias (p. ej. PyBullet — zlib; NumPy, SciPy, Pandas, Matplotlib — BSD;
qdarktheme, pyqtgraph — MIT; OpenCV — Apache-2.0; Qt Advanced Docking System
— LGPL). PyQt6 y PyQt6-Charts se utilizan y distribuyen bajo los términos de
la **GPLv3** (existe una licencia comercial alternativa de Riverbank que no
se usa en este proyecto).

---
<div align="center">
<sub>Proyecto de grado — Universidad Distrital Francisco José de Caldas</sub>
</div>
