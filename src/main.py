"""Importa las librerias y modulos necesarios
"""
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from gui.app_interface import MainInterface
import sys

if __name__ == '__main__':
    # Obtiene la imagen de la camara
    # print("Qt: v", QT_VERSION_STR, "\tPyQt: v", PYQT_VERSION_STR)
    app = QApplication(sys.argv)
    app.setStyle('fusion')
    # app.setAttribute(Qt.ApplicationAttribute.AA_DontCreateNativeWidgetSiblings)

    window = MainInterface()
    window.show()

    (app.exec())
