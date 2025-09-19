"""Importa las librerias y modulos necesarios
"""
import os
import sys
import pybullet as p
import pybullet_data
from PyQt6.QtGui import QGuiApplication, QPixmap, QFont
from PyQt6.QtWidgets import QApplication
from PyQt6.QtQuick import QQuickView, QQuickRenderControl
from PyQt6.QtCore import QUrl, Qt
from qdarktheme.qtpy.QtWidgets import QSplashScreen
from gui.app_interface import MainInterface


class Preloader:
    def __init__(self, qml: str, urdf: str):
        self.urdf_path = urdf
        self.qml_path = qml

    def preload_quick(self):
        """ Inicializa y fuerza render en offscreen
        """
        splash.showMessage(
            "Cargando modelos y texturas",
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
            Qt.GlobalColor.white
        )
        self.offscreen_window = QQuickView()
        self.render_control = QQuickRenderControl(parent=self.offscreen_window)
        self.offscreen_window.setSource(QUrl.fromLocalFile(self.qml_path))
        self.render_control.render()

        splash.showMessage(
            "Creando modelo 3D",
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
            Qt.GlobalColor.white
        )
        self.offscreen_window.create()
        self.offscreen_window.update()
        self.offscreen_window.rendererInterface()
        QGuiApplication.processEvents()
        return self.offscreen_window

    def preload_pybullet(self):
        splash.showMessage(
            "Creando motor de fisicas de simulacion",
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
            Qt.GlobalColor.white
        )
        p.connect(p.DIRECT)

        # Configurar la simulación
        p.setGravity(0, 0, -9.81)
        p.setTimeStep(1./240.)  # 240 Hz

        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        splash.showMessage(
            "Cargando modelos de simulación",
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
            Qt.GlobalColor.white
        )

        plane_id = p.createCollisionShape(p.GEOM_PLANE)
        ground_id = p.createMultiBody(0, plane_id)

        # Carga el modelo del robot
        robot_id = p.loadURDF(
            self.urdf_path,
            basePosition=[0, 0, 0],
            baseOrientation=p.getQuaternionFromEuler([0, 0, 0]),
            useFixedBase=True,  # o False si el robot es móvil
            flags=p.URDF_USE_INERTIA_FROM_FILE | p.URDF_USE_SELF_COLLISION
        )
        return robot_id


if __name__ == '__main__':
    # Obtiene la imagen de la cámara
    # print("Qt: v", QT_VERSION_STR, "\tPyQt: v", PYQT_VERSION_STR)
    app = QApplication(sys.argv)
    app.setStyle('fusion')

    img_path = os.path.join(os.path.dirname(__file__),
                            "gui", "img", "openbotv_v1.png")
    splash_pix = QPixmap(img_path).scaled(800, 450)

    # Crear splash
    splash = QSplashScreen(splash_pix)

    # Cambiar fuente del mensaje
    font = QFont("Arial", 12, QFont.Weight.Medium)  # Nombre, tamaño, peso
    splash.setFont(font)

    # Mostrar mensaje (puedes alinear arriba, abajo, centro, etc.)
    splash.showMessage(
        "Iniciando carga de datos",
        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
        Qt.GlobalColor.white
    )
    splash.show()
    app.processEvents()

    qml_path = os.path.join(os.path.dirname(__file__),
                            "simulation", "simulation.qml")
    urdf_path = os.path.join(os.path.dirname(
        __file__), "simulation", "urdf", 'openbot_v1.urdf')
    preloader = Preloader(qml_path, urdf_path)
    quickview = preloader.preload_quick()
    pybullet = preloader.preload_pybullet()

    window = MainInterface(quickview, pybullet)
    window.show()

    splash.finish(window)
    sys.exit(app.exec())
