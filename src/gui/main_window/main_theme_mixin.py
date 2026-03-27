from pathlib import Path
from PyQt6.QtCore import pyqtSignal, QObject, Qt
import pyqtgraph as pg
import qdarktheme
import qdarktheme.dist
import qdarktheme.dist.dark
import qdarktheme.dist.dark.stylesheet
import qdarktheme.dist.light
import qdarktheme.dist.light.stylesheet
from .theme_stylesheet import dark_style, light_style
from data import config_manager as cfg


class MainThemeMixin:
    """ Mixin donde se gestionan los temas, colores, cambio entre claro y oscuro tanto de forma
        manual con el botón o de forma automática con el tema de windows.
    """
    theme_change = pyqtSignal(str)

    actual_theme = None

    def update_theme(self, scheme: Qt.ColorScheme):
        """ Se ejecuta cada vez que cambia el tema del sistema
        """
        if scheme == Qt.ColorScheme.Dark:
            self.load_dark_theme()
            cfg.set_value("settings.json", "theme", value="dark")
        elif scheme == Qt.ColorScheme.Light:
            self.load_light_theme()
            cfg.set_value("settings.json", "theme", value="light")
        else:
            print("Error: Tema desconocido")

    def toggle_theme_event(self):
        if self.actual_theme is None:
            theme = cfg.get("settings.json", "theme").lower()
            self.actual_theme = (
                Qt.ColorScheme.Dark if theme == "dark" else Qt.ColorScheme.Light
            )
        else:
            self.actual_theme = (
                Qt.ColorScheme.Light
                if self.actual_theme == Qt.ColorScheme.Dark
                else Qt.ColorScheme.Dark
            )

        # Emitir señal según el estado actual
        is_dark = self.actual_theme == Qt.ColorScheme.Dark
        self.theme_manager.emit_theme_change(is_dark)

        self.update_theme(self.actual_theme)

    def load_dark_theme(self):
        """ Modificaciones para el tema oscuro de qdarktheme.
        """
        qdarktheme.dist.dark.stylesheet.STYLE_SHEET = dark_style
        stylesheet = qdarktheme.load_stylesheet("dark")
        svg_path = (Path(__file__).resolve().parent.parent.parent.parent /
                    "src/gui/main_window/theme_stylesheet/svg/radio_button_checked_r.svg").as_posix()
        stylesheet += f"""
        QRadioButton::indicator:checked {{
            image: url("{svg_path}");
        }}"""
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
        self.graph_interface.graph_object.graph_widget.setBackground(
            pg.mkColor((32, 33, 36)))

    def load_light_theme(self):
        """ Modificaciones para el tema claro de qdarktheme.
        """
        qdarktheme.dist.light.stylesheet.STYLE_SHEET = light_style
        stylesheet = qdarktheme.load_stylesheet("light")
        svg_path = (Path(__file__).resolve().parent.parent.parent.parent /
                    "src/gui/main_window/theme_stylesheet/svg/radio_button_checked_b.svg").as_posix()
        stylesheet += f"""
        QRadioButton::indicator:checked {{
            image: url("{svg_path}");
        }}"""
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
        self.graph_interface.graph_object.graph_widget.setBackground(
            pg.mkColor((248, 249, 250)))


class ThemeManager(QObject):
    """ Gestor de tema encargado de producir la señal necesaria para cambiar de colores y de 
        imágenes según se necesite.
    """
    _instance = None
    theme_changed = pyqtSignal(bool)
    color_schemes = None
    theme_map = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def emit_theme_change(self, dark_t: bool):
        self.theme_changed.emit(dark_t)

    def set_color_scheme(self, color_scheme):
        self.color_schemes = color_scheme
        self.theme_map = {
            "light": self.color_schemes.Light,
            "dark": self.color_schemes.Dark
        }
