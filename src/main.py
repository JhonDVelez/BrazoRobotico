"""Importa las librerias y modulos necesarios
"""
from ctypes import alignment
import os
import sys
from PyQt6.QtGui import QGuiApplication, QPixmap
from PyQt6.QtWidgets import QApplication
from PyQt6.QtQuick import QQuickView, QQuickRenderControl
from PyQt6.QtCore import QUrl, Qt
from qdarktheme.qtpy.QtWidgets import QSplashScreen
from gui.app_interface import MainInterface


class Quick3DPreloader:
    def __init__(self, qml_path: str):
        self.offscreen_window = QQuickView()
        self.render_control = QQuickRenderControl(parent=self.offscreen_window)
        # self.offscreen_window.setColor("transparent")
        self.offscreen_window.setSource(QUrl.fromLocalFile(qml_path))
        self.render_control.render()

    def preload(self):
        """Inicializa y fuerza render en offscreen"""
        # Ojo: en Qt6 necesitas un QQuickGraphicsDevice y un QQuickRenderTarget aquí
        self.offscreen_window.create()

        # Forzar un update
        self.offscreen_window.update()
        self.offscreen_window.rendererInterface()
        QGuiApplication.processEvents()

        print("✅ QML precargado en memoria (pero no visible)")

        return self.offscreen_window


if __name__ == '__main__':
    # Obtiene la imagen de la camara
    # print("Qt: v", QT_VERSION_STR, "\tPyQt: v", PYQT_VERSION_STR)
    app = QApplication(sys.argv)
    app.setStyle('fusion')

    # --- Splash Screen ---
    splash_pix = QPixmap(400, 200)
    splash_pix.fill(Qt.GlobalColor.black)
    splash = QSplashScreen(splash_pix)
    splash.showMessage("Cargando modelos y texturas...",
                       Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignBottom,
                       Qt.GlobalColor.white)
    splash.show()
    app.processEvents()

    # --- Precarga ---
    qml_path = os.path.join(os.path.dirname(__file__),
                            "simulation", "simulation.qml")
    preloader = Quick3DPreloader(qml_path)
    quickview = preloader.preload()  # ✅ obtenemos el QQuickView

    # --- Ventana principal ---
    window = MainInterface(quickview)  # se lo pasamos a tu interfaz
    window.show()

    splash.finish(window)
    sys.exit(app.exec())
