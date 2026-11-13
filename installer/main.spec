# -*- mode: python ; coding: utf-8 -*-

import glob
import os
from PyInstaller.utils.hooks import collect_data_files

# Al ejecutar `pyinstaller installer\main.spec`, las rutas relativas del spec
# se resuelven contra la carpeta del spec (SPECPATH); calculamos la raíz del
# proyecto para referenciar todo de forma inequívoca.
ROOT = os.path.abspath(os.path.join(SPECPATH, '..'))

# ------------------------------------------------------------------
# DLLs de Qt6: en este entorno (pip PyQt6 + Qt de conda-forge) los
# binarios de Qt viven en Library/lib/qt6/bin y el hook estándar de
# PyInstaller NO los incluye. Hay que añadirlos explícitamente y poner
# Library/bin en el PATH para que se resuelvan sus dependencias
# transitivas (zstd, brotli, freetype, harfbuzz, ...).
from PyQt6.QtCore import QLibraryInfo

_qt_bin = QLibraryInfo.path(QLibraryInfo.LibraryPath.BinariesPath)
qt6_dlls = [(dll, '.') for dll in glob.glob(os.path.join(_qt_bin, 'Qt6*.dll'))]

_env_root = os.path.abspath(os.path.join(
    _qt_bin, os.pardir, os.pardir, os.pardir, os.pardir))
_env_bin = os.path.join(_env_root, 'Library', 'bin')
os.environ['PATH'] = _env_bin + os.pathsep + os.environ.get('PATH', '')

# DLLs de conda que PyInstaller no resuelve solo (dependencias de Qt6,
# matplotlib, PIL y pyqtgraph). Si no existe en el entorno, se ignora.
_conda_dlls = [
    'double-conversion.dll', 'harfbuzz.dll',          # Qt6
    'freetype.dll', 'openjp2.dll', 'jpeg8.dll',       # matplotlib / PIL
    'tiff.dll', 'zlib-ng2.dll', 'lcms2.dll',
    'libwebp.dll', 'libwebpmux.dll', 'libwebpdemux.dll',
    'qhull_r.dll',
]
for name in _conda_dlls:
    p = os.path.join(_env_bin, name)
    if os.path.isfile(p):
        qt6_dlls.append((p, '.'))

a = Analysis(
    [os.path.join(ROOT, 'src', 'main.py')],
    pathex=[ROOT],
    binaries=qt6_dlls,
    datas=[
        # Recursos de la app (img, icons, qml, pybullet, tabla_compensacion).
        # El destino conserva la estructura src/resources para que las rutas
        # relativas a __file__/sys._MEIPASS funcionen igual que en desarrollo.
        (os.path.join(ROOT, 'src', 'resources'), 'src/resources'),
        # SVGs usados por theme_manger (radio buttons de los temas).
        (os.path.join(ROOT, 'src', 'services', 'styling', 'theme_stylesheet', 'svg'),
         os.path.join('src', 'services', 'styling', 'theme_stylesheet', 'svg')),
        # SVGs internos de qdarktheme (referenciados via ${path} en runtime).
        *collect_data_files('qdarktheme'),
    ],
    hiddenimports=[
        # Fuerza los hooks de PyInstaller para que se incluyan los módulos
        # QML (qmldir + plugins) que el runtime de Quick3D carga dinámicamente.
        # (PyQt6.QtQuick3D no existe como binding en pip; el módulo QML
        # QtQuick3D se incluye vía la carpeta qml del entorno conda.)
        'PyQt6.QtQuick',
        'PyQt6.QtQml',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='OpenBotV-Studio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=os.path.join(SPECPATH, 'version_info.py'),
    icon=os.path.join(ROOT, 'src', 'resources', 'img', 'laser_b.ico'),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='OpenBotV-Studio',
)
