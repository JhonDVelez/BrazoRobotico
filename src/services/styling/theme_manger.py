import os
from pathlib import Path
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QIcon, QPixmap
import qdarktheme
import qdarktheme.dist
import qdarktheme.dist.dark
import qdarktheme.dist.dark.stylesheet
import qdarktheme.dist.light
import qdarktheme.dist.light.stylesheet
from src.services.styling.theme_stylesheet import dark_style, light_style
from src.services.data import config_manager as cfg
from src.services.data.signals import ThemeSignalManager


class ThemeManager:
    """ Mixin donde se gestionan los temas, colores, cambio entre claro y oscuro tanto de forma
        manual con el botón o de forma automática con el tema de windows.
    """
    actual_theme = None

    def __init__(self, parentWindow):
        self.parent = parentWindow

        self.sun_icon = QIcon("icons:sun.png")
        self.moon_icon = QIcon("icons:moon.png")
        self.laser_w = QPixmap("img:laser_w.png").scaledToHeight(
            20, Qt.TransformationMode.SmoothTransformation)
        self.laser_b = QPixmap("img:laser_b.png").scaledToHeight(
            20, Qt.TransformationMode.SmoothTransformation)

        self.theme_signal_manager = ThemeSignalManager().get_instance()

    def update_theme(self, scheme: Qt.ColorScheme | None):
        """ Se ejecuta cada vez que cambia el tema del sistema
        """
        if scheme == Qt.ColorScheme.Dark:
            self._load_dark_theme()
            cfg.set_value("settings.json", "theme", value="dark")
        elif scheme == Qt.ColorScheme.Light:
            self._load_light_theme()
            cfg.set_value("settings.json", "theme", value="light")
        else:
            print("Error: Tema desconocido")

    def _apply_theme_from_signal(self, is_dark: bool):
        """ Aplica el tema cuando se recibe una señal de otra ventana (sin emitir de nuevo).
        """
        if is_dark:
            self._load_dark_theme()
            cfg.set_value("settings.json", "theme", value="dark")
        else:
            self._load_light_theme()
            cfg.set_value("settings.json", "theme", value="light")
        self.actual_theme = Qt.ColorScheme.Dark if is_dark else Qt.ColorScheme.Light

    def _load_current_theme(self):
        self.update_theme(self.theme_signal_manager.get_current_theme())

    def toggle_theme_event(self):
        """_summary_

        Args:
            _checked (_type_, optional): _description_. Defaults to None.
        """
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
        self.theme_signal_manager.emit_theme_change(is_dark)

        self.update_theme(self.actual_theme)

    def _load_dark_theme(self):
        """ Modificaciones para el tema oscuro de qdarktheme.
        """
        qdarktheme.dist.dark.stylesheet.STYLE_SHEET = dark_style
        stylesheet = qdarktheme.load_stylesheet("dark")
        svg_path = (Path(__file__).resolve().parent /
                    "theme_stylesheet/svg/radio_button_checked_b.svg").as_posix()
        stylesheet += f"""
        QRadioButton::indicator:checked {{
            image: url("{svg_path}");
        }}"""
        self.parent.setStyleSheet(stylesheet)

        # Actualizar title_bar si existe
        if hasattr(self, 'title_bar') and self.title_bar is not None:
            self.parent.title_bar.minBtn.setNormalColor("#A8A8A8")
            self.parent.title_bar.minBtn.setHoverBackgroundColor("#44464A")
            self.parent.title_bar.maxBtn.setNormalColor("#A8A8A8")
            self.parent.title_bar.maxBtn.setHoverBackgroundColor("#44464A")
            self.parent.title_bar.closeBtn.setNormalColor("#A8A8A8")

        # Actualizar logo_label si existe
        if hasattr(self.parent, 'logo_label') and hasattr(self, 'laser_w'):
            self.parent.logo_label.setPixmap(self.laser_w)

        # Actualizar theme_action si existe
        if hasattr(self.parent, 'theme_action') and hasattr(self, 'sun_icon'):
            self.parent.theme_action.setIcon(self.sun_icon)

        self.theme_signal_manager.set_current_theme(Qt.ColorScheme.Dark)

    def _load_light_theme(self):
        """ Modificaciones para el tema claro de qdarktheme.
        """
        qdarktheme.dist.light.stylesheet.STYLE_SHEET = light_style
        stylesheet = qdarktheme.load_stylesheet("light")
        svg_path = (Path(__file__).resolve().parent /
                    "theme_stylesheet/svg/radio_button_checked_b.svg").as_posix()
        stylesheet += f"""
        QRadioButton::indicator:checked {{
            image: url("{svg_path}");
        }}"""
        self.parent.setStyleSheet(stylesheet)

        # Actualizar title_bar si existe
        if hasattr(self, 'title_bar') and self.title_bar is not None:
            self.parent.title_bar.minBtn.setNormalColor("#323238")
            self.parent.title_bar.minBtn.setHoverBackgroundColor("#A5AAB4")
            self.parent.title_bar.maxBtn.setNormalColor("#323238")
            self.parent.title_bar.maxBtn.setHoverBackgroundColor("#A5AAB4")
            self.parent.title_bar.closeBtn.setNormalColor("#323238")

        # Actualizar logo_label si existe
        if hasattr(self.parent, 'logo_label') and hasattr(self, 'laser_b'):
            self.parent.logo_label.setPixmap(self.laser_b)

        # Actualizar theme_action si existe
        if hasattr(self.parent, 'theme_action') and hasattr(self, 'moon_icon'):
            self.parent.theme_action.setIcon(self.moon_icon)

        self.theme_signal_manager.set_current_theme(Qt.ColorScheme.Light)
