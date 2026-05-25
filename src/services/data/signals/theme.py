"""
Modulo que define el gestor de senales del tema visual.

Proporciona el singleton ThemeSignalManager para la coordinacion
de cambios de tema (claro/oscuro) entre los distintos componentes
de la aplicacion.
"""

from PyQt6.QtCore import pyqtSignal, QObject


class ThemeSignalManager(QObject):
    """
    Gestor de senales para el cambio de tema visual.

    Permite que multiples componentes (widgets, graficas, escena 3D)
    se sincronicen cuando el usuario alterna entre modo claro y oscuro.

    Signals:
        theme_changed: Emite True si el nuevo tema es oscuro.
    """
    _instance = None
    theme_changed = pyqtSignal(bool)
    current_theme = None

    @classmethod
    def get_instance(cls):
        """
        Obtiene la instancia unica del gestor (patron Singleton).

        Returns:
            ThemeSignalManager: Instancia unica.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def emit_theme_change(self, dark_t: bool):
        """
        Emite la senal de cambio de tema a todos los suscriptores.

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
