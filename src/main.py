""" Clase principal main donde se realiza la carga de datos necesarios en la splash screen ademas
    de la creación de la ventana principal de la interfaz y la muestra en pantalla.
"""
import os
import sys
import time
import threading 
import pybullet as p
import pybullet_data
from PyQt6.QtGui import QGuiApplication, QPixmap, QFont, QIcon
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtQuick import QQuickView
from PyQt6.QtCore import QUrl, Qt
from qdarktheme.qtpy.QtWidgets import QSplashScreen

# Importación de la interfaz principal corregida
from gui.app_interface import MainInterface

# ==========================================================================
#         SISTEMA DE TELEMETRÍA GLOBAL (Compartido por toda la App)
# ==========================================================================
# Definimos esto a nivel de módulo para que sea el "punto de verdad" único.
telemetry = {
    'history_pos': [[] for _ in range(6)],
    'history_temp': [[] for _ in range(6)],
    'lock': threading.Lock(), # Crucial para evitar que el Worker y Matplotlib choquen
    'running': True
}

class PreloadedContainer:
    """ Contenedor de datos que encapsula la vista de QtQuick (QML). """
    def __init__(self, quick_view, window_container):
        self.quick_view = quick_view
        self.window_container = window_container
        self.is_ready = True

class CompletePreloader:
    """ Clase encargada de la lógica de precarga de recursos (3D y Físicas). """
    def __init__(self, qml: str, urdf: str, splash_ref):
        self.urdf_path = urdf
        self.qml_path = qml
        self.splash = splash_ref
        self.dummy_parent = None

    def create_parent_widget(self):
        self.splash.showMessage(
            "Creando contenedor temporal...",
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
            Qt.GlobalColor.white
        )
        try:
            self.dummy_parent = QWidget()
            self.dummy_parent.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
            return True
        except Exception as e:
            print(f"Error creando widget padre: {e}")
            return False

    def preload_complete_quick3d_setup(self):
        if not self.create_parent_widget(): return None

        self.splash.showMessage(
            "Cargando motor gráfico QML...",
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
            Qt.GlobalColor.white
        )

        try:
            view = QQuickView()
            view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
            view.setSource(QUrl.fromLocalFile(self.qml_path))

            # Forzar el procesamiento de eventos para que el motor QML arranque
            for i in range(3):
                QGuiApplication.processEvents()
                time.sleep(0.1)

            container = QWidget.createWindowContainer(view, self.dummy_parent)
            container.setMinimumSize(160, 120)
            
            return PreloadedContainer(view, container)
        except Exception as e:
            print(f"Error en precarga QML: {e}")
            return None

    def preload_pybullet(self):
        self.splash.showMessage(
            "Inicializando motor de físicas PyBullet...",
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
            Qt.GlobalColor.white
        )
        try:
            p.connect(p.DIRECT)
            p.setGravity(0, 0, -9.81)
            p.setAdditionalSearchPath(pybullet_data.getDataPath())
            
            p.createMultiBody(0, p.createCollisionShape(p.GEOM_PLANE))
            robot_id = p.loadURDF(self.urdf_path, useFixedBase=True)
            p.stepSimulation()
            return robot_id
        except Exception as e:
            print(f"Error en PyBullet: {e}")
            return None

if __name__ == '__main__':
    # Configuración básica de la App
    app = QApplication(sys.argv)
    app.setStyle('fusion')
    
    # --- RUTA DE RECURSOS ---
    # Usamos rutas absolutas basadas en la ubicación de este archivo
    base_dir = os.path.dirname(__file__)
    img_path = os.path.join(base_dir, "gui", "img", "openbotv_v1.png")
    qml_path = os.path.join(base_dir, "simulation", "simulation.qml")
    urdf_path = os.path.join(base_dir, "simulation", "urdf", 'openbot_v1.urdf')

    # --- SPLASH SCREEN ---
    splash_pix = QPixmap(img_path).scaled(800, 450, Qt.AspectRatioMode.KeepAspectRatio)
    splash = QSplashScreen(splash_pix)
    splash.show()
    app.processEvents()

    # --- PROCESO DE PRECARGA ---
    preloader = CompletePreloader(qml_path, urdf_path, splash)
    preloaded_container = preloader.preload_complete_quick3d_setup()
    pybullet_robot = preloader.preload_pybullet()

    if preloaded_container and pybullet_robot:
        splash.showMessage(
            "Ensamblando interfaz principal...",
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
            Qt.GlobalColor.white
        )
        
        # Instanciamos la ventana pasando la bolsa de telemetría global
        window = MainInterface(preloaded_container, pybullet_robot, telemetry)
        window.setWindowTitle("OpenBotv - Control & Telemetry")
        
        # Limpieza y visualización
        if preloader.dummy_parent:
            preloader.dummy_parent.deleteLater()
            
        window.showMaximized()
        splash.finish(window)
    else:
        print("Error crítico: No se pudieron cargar los recursos necesarios.")
        sys.exit(1)
        
    sys.exit(app.exec())