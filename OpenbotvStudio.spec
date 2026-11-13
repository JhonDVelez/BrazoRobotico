# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all

pyqt6_datas, pyqt6_binaries, pyqt6_hiddenimports = collect_all('PyQt6')

conda_bin = r"C:\Users\jeiso\miniforge3\envs\.venv\Library\bin"
qt_dlls = [(os.path.join(conda_bin, f), '.') for f in os.listdir(conda_bin) if f.startswith('Qt6') and f.endswith('.dll')]

qt_plugins_dir = r"C:\Users\jeiso\miniforge3\envs\.venv\Library\lib\qt6\plugins"

def get_plugin_binaries(plugin_name):
    p_dir = os.path.join(qt_plugins_dir, plugin_name)
    if os.path.exists(p_dir):
        return [(os.path.join(p_dir, f), plugin_name) for f in os.listdir(p_dir) if f.endswith('.dll')]
    return []

qt_plugin_binaries = (
    get_plugin_binaries('platforms') +
    get_plugin_binaries('imageformats') +
    get_plugin_binaries('iconengines') +
    get_plugin_binaries('styles')
)

qt_qml_dir = r"C:\Users\jeiso\miniforge3\envs\.venv\Library\lib\qt6\qml"
qt_qml_modules = [
    (os.path.join(qt_qml_dir, 'QtQuick3D'), 'QtQuick3D'),
    (os.path.join(qt_qml_dir, 'QtQuick'), 'QtQuick'),
    (os.path.join(qt_qml_dir, 'Qt'), 'Qt'),
]

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=pyqt6_binaries + qt_dlls + qt_plugin_binaries,
    datas=[
        ('src/resources', 'src/resources'),
    ] + pyqt6_datas + qt_qml_modules,
    hiddenimports=[
        'cv2',
        'pybullet',
        'darkdetect',
        'qdarktheme',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtQuick',
    ] + pyqt6_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PySide6'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='OpenbotvStudio',
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
    icon='src/resources/img/laser_b.png'
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='OpenbotvStudio',
)
