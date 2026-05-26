"""
Modulo que define el gestor de senales para la configuracion del sistema.

Permite el acceso y modificacion de parametros de configuracion de forma
centralizada y reactiva, sin acceso directo a archivos desde los componentes.
"""

from PyQt6.QtCore import pyqtSignal, QObject


class ConfigSignalManager(QObject):
    """
    Gestor de senales y datos para la configuracion.

    Actua como un almacen en memoria de la configuracion actual y facilita
    la comunicacion entre los componentes que requieren datos y el controlador
    que los persiste.

    Signals:
        config_updated: Emite (filename, keys, value) cuando un parametro cambia.
        change_requested: Emite (filename, keys, value) para solicitar un cambio persistente.
    """
    _instance = None
    config_updated = pyqtSignal(str, list, object)
    change_requested = pyqtSignal(str, list, object)

    def __init__(self):
        super().__init__()
        self._cache = {}

    @classmethod
    def get_instance(cls):
        """
        Obtiene la instancia unica del gestor (patron Singleton).

        Returns:
            ConfigSignalManager: Instancia unica.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_all_config(self, filename: str, data: dict):
        """
        Puebla el cache interno con la configuracion completa de un archivo.

        Args:
            filename (str): Nombre del archivo (e.g. 'settings.json').
            data (dict): Contenido completo del archivo.
        """
        self._cache[filename] = data

    def get_param(self, filename: str, *keys: str, default=None):
        """
        Obtiene un parametro del cache de forma segura.

        Args:
            filename (str): Archivo donde buscar.
            *keys (str): Secuencia de llaves anidadas.
            default (any, optional): Valor a retornar si no existe.

        Returns:
            any: Valor encontrado o default.
        """
        data = self._cache.get(filename)
        if data is None:
            return default
        
        temp = data
        for key in keys:
            if isinstance(temp, dict) and key in temp:
                temp = temp[key]
            else:
                return default
        return temp

    def update_param(self, filename: str, keys: list, value: object, notify: bool = True):
        """
        Actualiza un parametro en el cache local.

        Args:
            filename (str): Archivo a modificar.
            keys (list): Lista de llaves anidadas.
            value (object): Nuevo valor.
            notify (bool): Si se debe emitir la señal config_updated.
        """
        if filename not in self._cache:
            self._cache[filename] = {}
        
        data = self._cache[filename]
        target = data
        for key in keys[:-1]:
            target = target.setdefault(key, {})
        
        target[keys[-1]] = value
        
        if notify:
            self.config_updated.emit(filename, keys, value)

    def request_change(self, filename: str, *keys: str, value: object):
        """
        Solicita un cambio persistente en la configuracion.

        Args:
            filename (str): Archivo a modificar.
            *keys (str): Llaves anidadas.
            value (object): Nuevo valor.
        """
        self.change_requested.emit(filename, list(keys), value)
