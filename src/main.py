"""Importa las librerias y modulos necesarios
"""
from PyQt6.QtWidgets import QApplication
from gui.app_interface import MainInterface
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication
import sys

if __name__ == '__main__':
    # Obtiene la imagen de la camara
    # print("Qt: v", QT_VERSION_STR, "\tPyQt: v", PYQT_VERSION_STR)
    app = QApplication(sys.argv)
    app.setStyle('fusion')
    QGuiApplication.styleHints().setColorScheme(Qt.ColorScheme.Dark)

    window = MainInterface()
    window.showMaximized()

    (app.exec())
