"""
Modulo de entrada principal de la aplicacion OpenBotv Control Lab.

Gestiona la secuencia de arranque: configuracion inicial, splash screen,
precarga del motor 3D (Quick3D/QML) y del motor de fisicas (PyBullet),
y finalmente la creacion y lanzamiento de la ventana principal.
"""

import os
import sys
import ctypes
import time
import cv2
import darkdetect
import pybullet as p
import pybullet_data
from PyQt6.QtCore import QUrl, Qt, QDir
from PyQt6.QtGui import QGuiApplication, QPixmap, QFont, QIcon, QSurfaceFormat
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtQuick import QQuickView
from qdarktheme.qtpy.QtWidgets import QSplashScreen
from src.main_window import MainWindow


class PreloadedContainer:
    """
    Contenedor que encapsula la vista Quick3D precargada y su contenedor de ventana.

    Attributes:
        quick_view (QQuickView): Vista Quick3D ya inicializada.
        window_container (QWidget or None): Contenedor de ventana asociado.
        is_ready (bool): Indica si la precarga se completo exitosamente.
    """

    def __init__(self, quick_view, window_container):
        self.quick_view = quick_view
        self.window_container = window_container
        self.is_ready = True


class CompletePreloader:
    """
    Gestor de precarga de recursos pesados antes de mostrar la interfaz.

    Realiza en orden: creacion de widget padre temporal, inicializacion
    de la vista Quick3D con renderizado de cache, y carga del entorno
    de simulacion PyBullet con el modelo URDF del robot.
    """

    def __init__(self, qml: str, urdf: str, box_v_path: str, box_c_path: str):
        """
        Args:
            qml (str): Ruta al archivo QML de la simulacion 3D.
            urdf (str): Ruta al archivo URDF del robot.
        """
        self.urdf_path = urdf
        self.qml_path = qml
        self.dummy_parent: QWidget | None = None
        self.preloaded_view: QQuickView | None = None
        self.preloaded_container: PreloadedContainer | None = None
        self.window_container = None
        self.box_visual_path = box_v_path
        self.box_collision_path = box_c_path
        self.col_id = None
        self.vis_id = None

    def create_parent_widget(self) -> bool:
        """
        Crea un widget padre temporal para el proceso de precarga.

        Returns:
            bool: True si el widget se creo correctamente, False en caso de error.
        """
        splash.showMessage(
            "Creando contenedor temporal",
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
            Qt.GlobalColor.white
        )

        try:
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

    def preload_complete_quick3d_setup(self) -> PreloadedContainer | None:
        """
        Precarga la vista Quick3D con su escena QML y cachea recursos graficos.

        Returns:
            PreloadedContainer or None: Contenedor con la vista precargada,
            o None si fallo la precarga.
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
        """
        Ejecuta ciclos de renderizado inicial para forzar el cacheo de recursos graficos.
        """
        try:
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

    def preload_pybullet(self) -> int | None:
        """
        Inicializa el motor de fisicas PyBullet y carga el modelo URDF del robot.

        Returns:
            int or None: ID del robot cargado en la simulacion, o None si fallo.
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

            plane_id = p.createCollisionShape(p.GEOM_PLANE)
            ground_id = p.createMultiBody(0, plane_id)

            splash.showMessage(
                "Cargando robot URDF",
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
                Qt.GlobalColor.white
            )
            # Create collision and visual shapes (For Static Concave Meshes)
            box_collision_id = p.createCollisionShape(
                shapeType=p.GEOM_MESH,
                fileName=self.box_collision_path,
                flags=p.GEOM_FORCE_CONCAVE_TRIMESH,
            )

            box_visual_id = p.createVisualShape(
                shapeType=p.GEOM_MESH,
                fileName=self.box_visual_path,
                rgbaColor=[1, 1, 1, 1]
            )

            box_id = p.createMultiBody(
                baseMass=0,
                baseCollisionShapeIndex=box_collision_id,
                baseVisualShapeIndex=box_visual_id,
                basePosition=[0.085, 0, 0],
                baseOrientation=p.getQuaternionFromEuler([0, 0, 0])
            )

            robot_id = p.loadURDF(
                self.urdf_path,
                basePosition=[0, 0, 0.09],
                baseOrientation=p.getQuaternionFromEuler([0, 0, 3.14159]),
                useFixedBase=True,
                flags=p.URDF_USE_INERTIA_FROM_FILE | p.URDF_ENABLE_CACHED_GRAPHICS_SHAPES
            )
            p.setCollisionFilterGroupMask(box_id, -1, 1, 1)
            p.changeDynamics(box_id, -1, collisionMargin=0.000001)
            p.setCollisionFilterGroupMask(robot_id, -1, 1, 1)
            p.changeDynamics(robot_id, 5, collisionMargin=0.000001)
            p.changeDynamics(robot_id, 6, collisionMargin=0.000001)
            p.stepSimulation()

            return robot_id

        except Exception as e:
            print(f"Error en PyBullet: {e}")
            return None

    def cleanup_preload_resources(self):
        """
        Libera los recursos temporales creados durante la precarga.
        """
        try:
            if self.dummy_parent:
                self.dummy_parent.deleteLater()
                self.dummy_parent = None
        except Exception as e:
            print(f"Error en cleanup: {e}")


if __name__ == '__main__':
    if sys.platform == "win32":
        myappid = 'laser.openbotv.control.lab'  # string único
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    if sys.platform == "linux":
        # Forzar xcb en Linux para evitar errores EGL/Wayland con NVIDIA+Qt6
        os.environ["QT_QPA_PLATFORM"] = "xcb"

    os.environ["QT_LOGGING_RULES"] = "qt.qpa.services=false"
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
    src_path = os.path.dirname(__file__)

    QDir.addSearchPath(
        "tabla", f"{src_path}/resources/tabla_compensacion")
    QDir.addSearchPath(
        "icons", f"{src_path}/resources/icons")
    QDir.addSearchPath(
        "img", f"{src_path}/resources/img")

    laser_icon_w = QIcon("img:laser_w.png")
    laser_icon_b = QIcon("img:laser_b.png")
    app.setWindowIcon(laser_icon_w if darkdetect.theme()
                      == "Dark" else laser_icon_b)
    app.setApplicationName("OpenBotv Control Lab")
    app.setDesktopFileName("OpenBotv Control Lab")

    # Splash screen
    img_path = os.path.join("img:openbotv_v1.png")
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
    QDir.addSearchPath(
        "qml", f"{src_path}/resources/qml")
    QDir.addSearchPath(
        "pybullet", f"{src_path}/resources/pybullet/")
    qml_path = QDir("qml:simulation.qml").path()
    urdf_path = QDir("pybullet:/urdf/openbot_v1.urdf").path()
    box_visual_path = QDir("pybullet:/meshes/visual/caja.obj").path()
    box_collision_path = QDir(
        "pybullet:/meshes/collision/caja_vhacd.obj").path()

    if cv2.ocl.haveOpenCL():
        cv2.ocl.setUseOpenCL(True)

    preloader = CompletePreloader(
        qml_path, urdf_path, box_visual_path, box_collision_path)
    preloaded_container = preloader.preload_complete_quick3d_setup()
    pybullet_robot = preloader.preload_pybullet()

    if preloaded_container and pybullet_robot:
        splash.showMessage(
            "Iniciando interfaz",
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
            Qt.GlobalColor.white
        )
        window = MainWindow(preloaded_container, pybullet_robot)
        window.setWindowTitle("OpenBotv-Control-Lab")
        preloader.cleanup_preload_resources()

        window.showMaximized()
        window.raise_()
        window.activateWindow()
        splash.finish(window)
    sys.exit(app.exec())
