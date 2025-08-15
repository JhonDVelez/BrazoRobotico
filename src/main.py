"""Importa las librerias y modulos necesarios
"""
from PyQt6.QtWidgets import QApplication
from interface.appInterface import main_i
import sys

if __name__ == '__main__':
    # Obtiene la imagen de la camara
    # print("Qt: v", QT_VERSION_STR, "\tPyQt: v", PYQT_VERSION_STR)
    app = QApplication(sys.argv)

    window = main_i()
    window.show()

    (app.exec())
    
