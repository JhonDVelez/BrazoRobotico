import os
from pathlib import Path
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QIcon, QPixmap
import PyQt6Ads as ads
import qdarktheme
import qdarktheme.dist
import qdarktheme.dist.dark
import qdarktheme.dist.dark.stylesheet
import qdarktheme.dist.light
import qdarktheme.dist.light.stylesheet
from src.services.styling.theme_stylesheet import (
    dark_style, light_style, ADS_DARK_STYLE, ADS_LIGHT_STYLE
)
from src.services.data.signals import ThemeSignalManager, ConfigSignalManager


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

        self.theme_signal_manager = ThemeSignalManager.get_instance()

    def update_theme(self, scheme: Qt.ColorScheme | None):
        """ Se ejecuta cada vez que cambia el tema del sistema.
            Ahora incluye lógica de fallback para evitar 'Tema desconocido'.
        """
        config_manager = ConfigSignalManager.get_instance()

        # Si el esquema es inválido o None, intentamos determinarlo
        if scheme not in [Qt.ColorScheme.Dark, Qt.ColorScheme.Light]:
            if not self.actual_theme in [Qt.ColorScheme.Dark, Qt.ColorScheme.Light]:
                # Recuperar de la configuración guardada
                theme_str = config_manager.get_param(
                    "settings.json", "theme", default="dark").lower()
                self.actual_theme = Qt.ColorScheme.Dark if theme_str == "dark" else Qt.ColorScheme.Light

            scheme = self.actual_theme

        if scheme == Qt.ColorScheme.Dark:
            self._load_dark_theme()
            config_manager.request_change(
                "settings.json", "theme", value="dark")
        else:
            self._load_light_theme()
            config_manager.request_change(
                "settings.json", "theme", value="light")

        # Emitir señal según el estado actual
        is_dark = self.actual_theme == Qt.ColorScheme.Dark
        self.theme_signal_manager.emit_theme_change(is_dark)

        self.actual_theme = scheme

    def _apply_theme_from_signal(self, is_dark: bool):
        """ Aplica el tema cuando se recibe una señal de otra ventana (sin emitir de nuevo).
        """
        config_manager = ConfigSignalManager.get_instance()
        if is_dark:
            self._load_dark_theme()
            config_manager.request_change(
                "settings.json", "theme", value="dark")
        else:
            self._load_light_theme()
            config_manager.request_change(
                "settings.json", "theme", value="light")
        self.actual_theme = Qt.ColorScheme.Dark if is_dark else Qt.ColorScheme.Light

    def load_current_theme(self):
        self.update_theme(self.theme_signal_manager.get_current_theme())

    def toggle_theme_event(self):
        """Cambia manualmente entre tema claro y oscuro.

        Si no hay un tema actual, lo determina desde la configuracion
        guardada. Emite la señal de cambio de tema y aplica el nuevo
        tema a la interfaz.
        """
        self.actual_theme = (
            Qt.ColorScheme.Light
            if self.actual_theme == Qt.ColorScheme.Dark
            else Qt.ColorScheme.Dark
        )

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

        # Aplicar estilo específico a dock_manager si existe
        if hasattr(self.parent, 'dock_manager'):
            self.parent.dock_manager.setStyleSheet(ADS_DARK_STYLE)

        # Actualizar title_bar si existe
        if hasattr(self.parent, 'title_bar') and self.parent.title_bar is not None:
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
        self._update_toolbar_icons(True)
        self._update_sim_icons(True)

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

        # Aplicar estilo específico a dock_manager si existe
        if hasattr(self.parent, 'dock_manager'):
            self.parent.dock_manager.setStyleSheet(ADS_LIGHT_STYLE)

        # Actualizar title_bar si existe
        if hasattr(self.parent, 'title_bar') and self.parent.title_bar is not None:
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
        self._update_toolbar_icons(False)
        self._update_sim_icons(False)

    def _update_toolbar_icons(self, is_dark: bool):
        mapping = [
            ('model_action',     'sim_view'),
            ('camera_action',    'camera_view'),
            ('graphs_action',    'graphs_view'),
            ('controls_action',  'controls_view'),
            ('charuco_action',   'charuco'),
            ('sphere_action',    'sphere'),
        ]
        for action_name, icon_name in mapping:
            if not hasattr(self.parent, action_name):
                continue
            icon = self.theme_signal_manager.get_toolbar_icon(
                icon_name, is_dark)
            getattr(self.parent, action_name).setIcon(icon)

    def _update_sim_icons(self, is_dark: bool):
        mapping = [
            ('start_action',  'start'),
            ('pause_action',  'pause'),
            ('stop_action',   'stop'),
            ('reset_action',  'reset'),
        ]
        for action_name, icon_name in mapping:
            if not hasattr(self.parent, action_name):
                continue
            icon = self.theme_signal_manager.get_toolbar_icon(
                icon_name, is_dark)
            getattr(self.parent, action_name).setIcon(icon)
