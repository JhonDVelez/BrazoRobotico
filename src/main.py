""" Clase principal main donde se realiza la carga de datos necesarios en la splash screen ademas
    de la creación de la ventana principal de la interfaz y la muestra en pantalla.
"""
import os
import sys
import ctypes
import time
import cv2
import traceback
import pybullet as p
import pybullet_data
import PyQt6
from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QGuiApplication, QPixmap, QFont, QIcon, QSurfaceFormat
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtQuick import QQuickView
from qdarktheme.qtpy.QtWidgets import QSplashScreen
from gui import MainWindow
from data import config_manager as cfg


class PreloadedContainer:
    """ Contenedor que encapsula la vista precargada y su window container
    """

    def __init__(self, quick_view, window_container):
        self.quick_view = quick_view
        self.window_container = window_container
        self.is_ready = True


class CompletePreloader:
    def __init__(self, qml: str, urdf: str):
        self.urdf_path = urdf
        self.qml_path = qml
        self.dummy_parent = None
        self.preloaded_view = None
        self.preloaded_container = None
        self.window_container = None

    def create_parent_widget(self):
        """Crea un widget padre temporal para el proceso de precarga"""
        splash.showMessage(
            "Creando contenedor temporal",
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
            Qt.GlobalColor.white
        )

        try:
            # Widget padre temporal para la precarga
            self.dummy_parent = QWidget()
            self.dummy_parent.resize(800, 600)
            self.dummy_parent.setWindowFlags(
                Qt.WindowType.Tool |
                Qt.WindowType.FramelessWindowHint
            )
            self.dummy_parent.setAttribute(
                Qt.WidgetAttribute.WA_DontShowOnScreen, True)

            return True

        except Exception as e:
            print(f"Error creando widget padre: {e}")
            return False

    def preload_complete_quick3d_setup(self):
        """ Precarga QQuickView + WindowContainer + Renderizado
        """
        if not self.create_parent_widget():
            return None

        splash.showMessage(
            "Cargando QML y creando vista 3D",
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
            Qt.GlobalColor.white
        )

        try:
            self.preloaded_view = QQuickView()
            self.preloaded_view.setFormat(surf_format)
            self.preloaded_view.setFlag(Qt.WindowType.WindowStaysOnBottomHint)
            self.preloaded_view.setResizeMode(
                QQuickView.ResizeMode.SizeRootObjectToView)
            self.preloaded_view.resize(512, 288)
            self.preloaded_view.setSource(QUrl.fromLocalFile(self.qml_path))

            for _ in range(3):
                QGuiApplication.processEvents()
                time.sleep(0.1)

            self.preloaded_view.create()
            if not self.preloaded_view.isVisible():
                self.preloaded_view.show()
                self.preloaded_view.update()
                QGuiApplication.processEvents()

            splash.showMessage(
                "Renderizando y cacheando recursos",
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
                Qt.GlobalColor.white
            )
            self.safe_initial_render()
            container = PreloadedContainer(
                self.preloaded_view, None)

            splash.showMessage(
                "Vista 3D completamente precargada",
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
                Qt.GlobalColor.white
            )

            return container

        except Exception as e:
            print(f"Error en precarga completa: {e}")
            import traceback
            traceback.print_exc()
            return None

    def safe_initial_render(self):
        """Renderizado inicial seguro para cachear recursos"""
        try:
            # Renderizado para cachear recursos
            for i in range(5):
                splash.showMessage(
                    f"Cacheando recursos 3D ({i+1}/5)",
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
                    Qt.GlobalColor.white
                )
                self.preloaded_view.update()
                QGuiApplication.processEvents()
                time.sleep(0.2)
        except Exception as e:
            print(f"Error en renderizado inicial: {e}")

    def preload_pybullet(self):
        """ Carga PyBullet
        """
        splash.showMessage(
            "Inicializando motor de físicas",
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
            Qt.GlobalColor.white
        )

        try:
            p.connect(p.DIRECT)
            p.setGravity(0, 0, -9.81)
            p.setTimeStep(1./240.)

            p.setAdditionalSearchPath(pybullet_data.getDataPath())

            splash.showMessage(
                "Creando mundo de simulación",
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
                Qt.GlobalColor.white
            )

            # Crear entorno
            plane_id = p.createCollisionShape(p.GEOM_PLANE)
            ground_id = p.createMultiBody(0, plane_id)

            splash.showMessage(
                "Cargando robot URDF",
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
                Qt.GlobalColor.white
            )

            # Cargar robot
            robot_id = p.loadURDF(
                self.urdf_path,
                basePosition=[0, 0, 0],
                baseOrientation=p.getQuaternionFromEuler([0, 0, 0]),
                useFixedBase=True,
                flags=p.URDF_USE_INERTIA_FROM_FILE | p.URDF_ENABLE_CACHED_GRAPHICS_SHAPES
            )
            p.stepSimulation()

            return robot_id

        except Exception as e:
            print(f"Error en PyBullet: {e}")
            return None

    def cleanup_preload_resources(self):
        """ Limpia solo los recursos temporales de precarga
        """
        try:
            # Solo eliminar el widget padre temporal
            if self.dummy_parent:
                self.dummy_parent.deleteLater()
                self.dummy_parent = None
        except Exception as e:
            print(f"Error en cleanup: {e}")


if __name__ == '__main__':
    cfg.init_config()
    
    if sys.platform == "win32":
        myappid = 'laser.openbotv.control.lab'  # string único
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    
    os.environ["QSG_RHI_BACKEND"] = "opengl"

    surf_format = QSurfaceFormat()
    surf_format.setDepthBufferSize(24)
    surf_format.setStencilBufferSize(8)
    surf_format.setSamples(4)
    surf_format.setVersion(4, 1)   # OpenGL 4.1 mínimo para shadow maps
    surf_format.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
    QSurfaceFormat.setDefaultFormat(surf_format)

    app = QApplication(sys.argv)
    app.setStyle('fusion')
    app.setWindowIcon(QIcon(os.path.join(os.path.dirname(__file__),
                                         "gui", "img", 'laser_w.png')))
    app.setApplicationName("OpenBotv Control Lab")
    app.setDesktopFileName("OpenBotv Control Lab")

    # Splash screen
    img_path = os.path.join(os.path.dirname(__file__),
                            "gui", "img", "openbotv_v1.png")
    splash_pix = QPixmap(img_path).scaled(800, 450)
    splash = QSplashScreen(splash_pix)
    font = QFont("Arial", 12, QFont.Weight.Medium)
    splash.setFont(font)

    splash.showMessage(
        "Iniciando precarga completa de recursos",
        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
        Qt.GlobalColor.white
    )
    splash.show()
    app.processEvents()

    # Rutas
    qml_path = os.path.join(os.path.dirname(__file__),
                            "simulation", "simulation.qml")
    urdf_path = os.path.join(os.path.dirname(__file__),
                             "simulation", "urdf", 'openbot_v1.urdf')

    if cv2.ocl.haveOpenCL():
        cv2.ocl.setUseOpenCL(True)

    preloader = CompletePreloader(qml_path, urdf_path)
    preloaded_container = preloader.preload_complete_quick3d_setup()
    pybullet_robot = preloader.preload_pybullet()

    if preloaded_container and pybullet_robot:
        splash.showMessage(
            "Iniciando interfaz",
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
            Qt.GlobalColor.white
        )
        window = MainWindow(preloaded_container, pybullet_robot)
        window.setWindowTitle("OpenBotv Control Lab")
        preloader.cleanup_preload_resources()

        window.showMaximized()
        window.raise_()
        window.activateWindow()
        window.check_handle_visibility()
        splash.finish(window)
    sys.exit(app.exec())
