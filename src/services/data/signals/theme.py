"""
Módulo que define el gestor de señales del tema visual.

Proporciona el singleton ThemeSignalManager para la coordinación
de cambios de tema (claro/oscuro) entre los distintos componentes
de la aplicación.
"""

from PyQt6.QtCore import pyqtSignal, QObject
from PyQt6.QtGui import QIcon


class ThemeSignalManager(QObject):
    """
    Gestor de señales para el cambio de tema visual.

    Permite que múltiples componentes (widgets, gráficas, escena 3D)
    se sincronicen cuando el usuario alterna entre modo claro y oscuro.

    Signals:
        theme_changed: Emite True si el nuevo tema es oscuro.
    """
    _instance = None
    theme_changed = pyqtSignal(bool)
    current_theme = None

    def __init__(self):
        super().__init__()
        self._toolbar_icons = {
            'sim_view':      ('icons:armView_d.png',       'icons:armView_l.png'),
            'camera_view':   ('icons:cameraView_d.png',    'icons:cameraView_l.png'),
            'graphs_view':   ('icons:graphView_d.png',     'icons:graphView_l.png'),
            'controls_view': ('icons:controlsView_d.png',  'icons:controlsView_l.png'),
            'charuco':       ('icons:gridSearch_d.png',    'icons:gridSearch_l.png'),
            'sphere':        ('icons:geometrySearch_d.png','icons:geometrySearch_l.png'),
            'start':         ('icons:play_d.png',          'icons:play_l.png'),
            'pause':         ('icons:pause_d.png',         'icons:pause_l.png'),
            'stop':          ('icons:stop_d.png',          'icons:stop_l.png'),
            'reset':         ('icons:refresh_d.png',       'icons:refresh_l.png'),
            'minimize':      ('icons:minimize_d.png',      'icons:minimize_l.png'),
            'restore':       ('icons:restore_down_d.png',  'icons:restore_down_l.png'),
            'close':         ('icons:close_d.svg',         'icons:close_l.svg'),
        }
        self._icon_cache = {}

    @classmethod
    def get_instance(cls):
        """
        Obtiene la instancia única del gestor (patrón Singleton).

        Returns:
            ThemeSignalManager: Instancia única.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def emit_theme_change(self, dark_t: bool):
        """
        Emite la señal de cambio de tema a todos los suscriptores.

        Args:
            dark_t (bool): True para tema oscuro.
        """
        self.theme_changed.emit(dark_t)

    def set_current_theme(self, theme):
        """
        Almacena el tema actual.

        Args:
            theme: Identificador del tema.
        """
        self.current_theme = theme

    def get_current_theme(self):
        """
        Obtiene el tema actual almacenado.

        Returns:
            Tema actual o None.
        """
        return self.current_theme

    def get_toolbar_icon(self, name: str, is_dark: bool) -> QIcon:
        """
        Obtiene el icono de toolbar para el tema indicado, con cache.

        Args:
            name (str): Nombre de la entrada en _toolbar_icons.
            is_dark (bool): True para icono oscuro (_d), False para claro (_l).

        Returns:
            QIcon: Icono cacheado o recién creado.
        """
        key = (name, is_dark)
        if key not in self._icon_cache:
            dark_path, light_path = self._toolbar_icons[name]
            path = dark_path if is_dark else light_path
            self._icon_cache[key] = QIcon(path)
        return self._icon_cache[key]
