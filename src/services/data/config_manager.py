"""
Modulo encargado de la gestion persistente de la configuracion del sistema.

Este modulo centraliza el acceso a archivos JSON (settings, camera, graphics),
asegurando que los directorios existan, los valores por defecto se mantengan
y los datos del usuario se fusionen correctamente durante las actualizaciones.
"""

import sys
import re
import json
from pathlib import Path
from PyQt6.QtCore import QStandardPaths


def get_app_dir() -> Path:
    """
    Determina la ruta del directorio base de la aplicacion.

    Funciona tanto en modo desarrollo (.py) como en ejecutables compilados
    (.exe o .elf) mediante PyInstaller.

    Returns:
        Path: Ruta absoluta al directorio raiz de la aplicacion.
    """
    if getattr(sys, "frozen", False):
        # Compilado con PyInstaller (--onefile o --onedir)
        return Path(sys.executable).parent
    else:
        # Modo desarrollo: usa la carpeta del script de entrada
        return Path(sys.argv[0]).resolve().parent


APP_DIR = get_app_dir()
GRAPH_DIR = APP_DIR / "graphs"


def get_config_dir() -> Path:
    """
    Determina la ruta del directorio de configuracion del usuario.

    Usa QStandardPaths para obtener la carpeta Documents localizada
    del sistema operativo (~/Documents en ingles, ~/Documentos en espanol, etc.).
    El directorio final es: ~/Documents/OpenBotVControlLab/config/

    Returns:
        Path: Ruta absoluta al directorio de configuracion.
    """
    docs = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.DocumentsLocation)
    return Path(docs) / "OpenBotVControlLab" / "config"


CONFIG_DIR = get_config_dir()


# Valores por defecto de cada archivo de configuración para asegurar integridad
DEFAULTS: dict[str, dict] = {
    "settings.json": {
        "window": {"width": 1280, "height": 720, "maximized": False},
        "theme": "dark",
        "content": {
            "model": True,
            "camera": False,
            "graphs": True,
            "controls": True
        },
        "simulation": {
            "activated": True,
            "shadows": True,
            "grid": True,
            "axes": False,
            "labels": False,
            "aa": True,
        },
        "camera": {
            "charuco": False,
            "circle": False,
            "view": {"charuco": False, "circle": False, "interval": 4},
            "calibrate": False,
            "color_calibrate": False,
        },
        "mode": {
            "sliders": True,
            "kinematics": False,
            "pick_place": False
        },
    },
    "camera.json": {
        "resolution": {"width": 1280, "height": 720, "fps": 30, },
        "sphere_radius": 20.0,
        "matrix": [
            [1446.148971641037, 0.0, 636.7973550159369],
            [0.0, 1447.6717541057947, 319.71811920663833],
            [0.0, 0.0, 1.0],
        ],
        "distortion coefficients": [
            [-13.931798783292495, 76.11684982580593, -0.006940719268868375,
             0.005651814170405385, 247.72613988745476, -14.020713760382487,
             77.81654802896536, 233.76774999933104, 0.0,
             0.0, 0.0, 0.0, 0.0, 0.0],
        ],
        "chessboard": {"x": 5, "y": 12, },
        "hsv_colors": {
            "amarillo": [20, 100, 100, 30, 255, 255],
            "verde": [40, 70, 70, 80, 255, 255],
            "azul": [100, 150, 50, 130, 255, 255],
            "naranja": [5, 150, 150, 15, 255, 255],
            "morado": [130, 50, 50, 160, 255, 255],
        },
    },
    "graphics.json": {
        "grid": {
            "angle": [
                [10, 50, True], [10, 50, True], [10, 50, True],
                [10, 50, True], [10, 50, True], [10, 50, True],
            ],
            "position": [
                [10, 100, True], [10, 100, True], [10, 100, True],
            ],
        }
    }
}


def _merge_defaults(defaults: dict, user_data: dict) -> dict:
    """
    Fusiona recursivamente los valores por defecto con los datos del usuario.

    Preserva las llaves personalizadas del usuario que no existan en los defaults.

    Args:
        defaults (dict): Diccionario base de configuracion.
        user_data (dict): Datos leidos desde el disco.

    Returns:
        dict: Diccionario fusionado resultante.
    """
    result = defaults.copy()
    for key, value in result.items():
        if key in user_data:
            # Si ambos son diccionarios, entramos a un nivel más profundo
            if isinstance(value, dict) and isinstance(user_data[key], dict):
                result[key] = _merge_defaults(value, user_data[key])
            else:
                # Si el usuario tiene un valor (y no es un dict), lo respetamos
                result[key] = user_data[key]

    # También añadimos llaves que el usuario tenga y que NO estén en defaults
    for key, value in user_data.items():
        if key not in result:
            result[key] = value

    return result


def init_config() -> None:
    """
    Inicializa el directorio de configuracion y verifica la integridad de los archivos.

    Crea los archivos faltantes o añade llaves nuevas introducidas en versiones
    recientes del software, reseteando archivos corruptos si es necesario.
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    for filename, defaults in DEFAULTS.items():
        path = CONFIG_DIR / filename

        if not path.exists():
            # Si no existe, lo creamos limpio
            path.write_text(_compact_dumps(defaults), encoding="utf-8")
            continue

        try:
            # Si existe, leemos lo que tiene el usuario
            user_config = json.loads(path.read_text(encoding="utf-8"))

            # Fusionamos: Default es la base, User sobreescribe
            new_config = _merge_defaults(defaults, user_config)

            # Solo sobreescribimos el archivo si hubo cambios (llaves faltantes añadidas)
            if new_config != user_config:
                path.write_text(_compact_dumps(new_config), encoding="utf-8")

        except (json.JSONDecodeError, OSError):
            # Si el archivo está roto, lo reseteamos por seguridad
            path.write_text(_compact_dumps(defaults), encoding="utf-8")


def load(filename: str) -> dict:
    """
    Carga un archivo de configuracion JSON completo.

    Args:
        filename (str): Nombre del archivo (e.g. 'camera.json').

    Returns:
        dict: Contenido del archivo o los defaults si falla.
    """
    init_config()
    path = CONFIG_DIR / filename
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # Archivo corrupto o ilegible → resetear
        defaults = DEFAULTS.get(filename, {})
        path.write_text(_compact_dumps(defaults), encoding="utf-8")
        return defaults


def save(filename: str, data: dict) -> None:
    """
    Persiste un diccionario de datos en un archivo JSON en CONFIG_DIR.

    Args:
        filename (str): Nombre del destino.
        data (dict): Contenido a guardar.
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    (CONFIG_DIR / filename).write_text(
        _compact_dumps(data),
        encoding="utf-8",
    )


def get(filename: str, *keys, default=None):
    """
    Realiza una busqueda segura y profunda de una llave en la configuracion.

    Args:
        filename (str): Archivo donde buscar.
        *keys (str): Secuencia de llaves anidadas.
        default (any, optional): Valor a retornar si falla la busqueda.

    Returns:
        any: Valor encontrado o el valor por defecto.
    """
    try:
        data = load(filename)
        # Navegamos por cada clave en la tupla keys
        for key in keys:
            if isinstance(data, dict):
                data = data.get(key, default)
            else:
                return default
        return data
    except Exception:
        # Por si el archivo no existe o está corrupto
        return default


def set_value(filename: str, keys: list[str], value) -> None:
    """
    Modifica o crea un valor en cualquier nivel de profundidad del JSON.

    Args:
        filename (str): Archivo a modificar.
        keys (list[str]): Lista de llaves anidadas. La ultima es la clave final.
        value (any): Nuevo valor a asignar.
    """
    data = load(filename)

    # Navegamos hasta el penúltimo nivel
    target = data
    for key in keys[:-1]:
        target = target.setdefault(key, {})

    # Asignamos el valor en la última clave
    target[keys[-1]] = value

    save(filename, data)


def _compact_dumps(obj, indent: int = 2) -> str:
    """
    Serializa un objeto JSON optimizando el espacio de listas numericas.

    Colapsa listas de numeros en una sola linea para mejorar la legibilidad
    en matrices de transformacion y coeficientes de distorsion.

    Args:
        obj (any): Objeto a serializar.
        indent (int): Sangria base.

    Returns:
        str: Cadena JSON formateada.
    """
    raw = json.dumps(obj, indent=indent, ensure_ascii=False)

    # Itera hasta que no haya más cambios (para arrays anidados).
    pattern = re.compile(
        r'\[\s*((?:-?[\d.eE+\-]+\s*,?\s*)+)\s*\]',
        re.DOTALL
    )

    prev = None
    while prev != raw:
        prev = raw

        def _collapse(m):
            nums = re.findall(r'-?[\d.eE+\-]+', m.group(1))
            return '[' + ', '.join(nums) + ']'
        raw = pattern.sub(_collapse, raw)

    return raw
