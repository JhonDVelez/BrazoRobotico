from PyQt6.QtCore import pyqtSignal, QObject
import qdarktheme
import qdarktheme.dist
import qdarktheme.dist.dark
import qdarktheme.dist.dark.stylesheet
import qdarktheme.dist.light
import qdarktheme.dist.light.stylesheet
from gui.main_window.theme_stylesheet import dark, light


class MainTheme:
    theme_change = pyqtSignal(str)

    def __init__(self):
        self.dark_theme = True

    def toggle_theme_event(self):
        if self.dark_theme:
            self.theme_manager.emit_theme_change(False)
            self.load_light_theme()
            self.dark_theme = False
            if hasattr(self, 'theme_menu'):
                self.theme_menu.setIcon(self.moon_icon)
        else:
            self.theme_manager.emit_theme_change(True)
            self.load_dark_theme()
            self.dark_theme = True
            if hasattr(self, 'theme_menu'):
                self.theme_menu.setIcon(self.sun_icon)

    def load_dark_theme(self):
        qdarktheme.dist.dark.stylesheet.STYLE_SHEET = dark.STYLE_SHEET
        stylesheet = qdarktheme.load_stylesheet("dark")
        self.setStyleSheet(stylesheet)
        self.title_bar.title_label.setStyleSheet(
            """background-color: rgba(42.000, 43.000, 46.000, 1.000); color: #ffffff;""")
        self.title_bar.left_container.setStyleSheet(
            """background-color: rgba(42.000, 43.000, 46.000, 1.000); border-radius: 0px""")
        self.title_bar.buttons_frame.setStyleSheet("""
            QWidget {background-color: rgba(42.000, 43.000, 46.000, 1.000); border-radius: 0px;}
            QToolButton {border: none; background: transparent;}
            QToolButton:hover {background-color: rgba(68.000, 70.000, 74.000, 1.000);}
            QToolButton:pressed {background-color: rgba(79.000, 80.000, 84.000, 1.000);}
            """)
        self.logo_label.setPixmap(self.laser_w)
        self.theme_action.setIcon(self.sun_icon)

    def load_light_theme(self):
        qdarktheme.dist.light.stylesheet.STYLE_SHEET = light.STYLE_SHEET
        stylesheet = qdarktheme.load_stylesheet("light")
        self.setStyleSheet(stylesheet)
        self.title_bar.title_label.setStyleSheet(
            """QLabel {color: #000000;}""")
        self.title_bar.title_label.setStyleSheet(
            """background-color: rgba(223.000, 225.000, 229.000, 1.000); color: #000000;""")
        self.title_bar.left_container.setStyleSheet(
            """background-color: rgba(223.000, 225.000, 229.000, 1.000); border-radius: 0px""")
        self.title_bar.buttons_frame.setStyleSheet("""
            QWidget {background-color: rgba(223.000, 225.000, 229.000, 1.000); border-radius: 0px;}
            QToolButton {border: none; background: transparent;}
            QToolButton:hover {background-color: rgba(215.000, 215.000, 215.000, 1.000);}
            QToolButton:pressed {background-color: rgba(196.000, 196.000, 196.000, 1.000);}
            """)
        self.logo_label.setPixmap(self.laser_b)
        self.theme_action.setIcon(self.moon_icon)


class ThemeManager(QObject):
    theme_changed = pyqtSignal(bool)
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def emit_theme_change(self, dark_t: bool):
        self.theme_changed.emit(dark_t)
