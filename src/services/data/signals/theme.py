from PyQt6.QtCore import pyqtSignal, QObject


class ThemeSignalManager(QObject):
    """ Gestor de tema encargado de producir la señal necesaria para cambiar de colores y de
        imágenes según se necesite.
    """
    _instance = None
    theme_changed = pyqtSignal(bool)
    current_theme = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def emit_theme_change(self, dark_t: bool):
        self.theme_changed.emit(dark_t)

    def set_current_theme(self, theme):
        self.current_theme = theme

    def get_current_theme(self):
        return self.current_theme
