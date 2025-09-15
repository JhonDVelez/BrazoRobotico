from PyQt6.QtWidgets import QMainWindow, QMessageBox, QVBoxLayout, QWidget, QSizePolicy
from PyQt6.QtCore import QEvent, Qt, QSize, QRect
from PyQt6.QtGui import QColor
from qframelesswindow import TitleBarBase


class MainTitleBar(TitleBarBase):
    """ Custom title bar """

    def __init__(self, parent):
        super().__init__(parent)
        pass
