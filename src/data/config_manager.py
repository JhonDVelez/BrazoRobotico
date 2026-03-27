# config_manager.py
import sys
import re
import json
from pathlib import Path


def get_app_dir() -> Path:
    """
    Retorna la carpeta del ejecutable, funcione como .py, .exe o .elf.
    """
    if getattr(sys, "frozen", False):
        # Compilado con PyInstaller (--onefile o --onedir)
        return Path(sys.executable).parent
    else:
        # Modo desarrollo: usa la carpeta del script de entrada
        return Path(sys.argv[0]).resolve().parent.parent


APP_DIR = get_app_dir()
CONFIG_DIR = APP_DIR / "config"
GRAPH_DIR = APP_DIR / "graphs"


# Valores por defecto de cada archivo de configuración
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
        "simulation": True,
        "camera": {
            "charuco": False,
            "sphere": False,
        },
        "mode": {
            "sliders": True,
            "kinematics": False
        },
    },
    "camera.json": {
        "resolution": {"width": 1280, "height": 720, "fps": 30},
        "matrix": [
            [545.5253380448539, 0.0, 507.8086016356526],
            [0.0, 516.6504135832704, 280.0301059137549],
            [0.0, 0.0, 1.0]
        ],
        "distortion coefficients": [
            [7.675754587138629, -11.990750827276958,
             -0.004777005936049289, 0.009067387196840113,
             5.398129685262089, 8.061549577315516,
             -12.684162075057332, 5.750972460421331,
             0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        ],
        "chessboard": {"x": 5, "y": 12},
    },
}


def _merge_defaults(defaults: dict, user_data: dict) -> dict:
    """
    Crea un nuevo diccionario basado en 'defaults', pero sobreescribe
    con los valores de 'user_data' si existen. Es recursivo.
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
        # Si la llave no está en user_data, se queda el valor de 'result' (el default)

    # También añadimos llaves que el usuario tenga y que NO estén en defaults
    # (para no borrar configuraciones extra que el usuario haya metido a mano)
    for key, value in user_data.items():
        if key not in result:
            result[key] = value

    return result


def init_config() -> None:
    """Crea CONFIG_DIR y asegura la integridad de las llaves en los JSON."""
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
    """Lee un archivo de config; si no existe lo recrea con defaults."""
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
    """Persiste data en config/<filename>."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    (CONFIG_DIR / filename).write_text(
        _compact_dumps(data),
        encoding="utf-8",
    )


def get(filename: str, *keys, default=None):
    """ Acceso rápido a valores en cualquier nivel de profundidad.
    """
    try:
        data = load(filename)
        # Navegamos por cada clave en la tupla keys
        for key in keys:
            # Si el nivel actual no es un diccionario o no tiene la clave,
            # devolvemos el valor por defecto.
            if isinstance(data, dict):
                data = data.get(key, default)
            else:
                return default
        return data
    except Exception:
        # Por si el archivo no existe o está corrupto
        return default


def set_value(filename: str, *keys: str, value) -> None:
    """ Modifica valores en cualquier nivel de profundidad.
    """
    data = load(filename)

    # Navegamos hasta el penúltimo nivel
    target = data
    for key in keys[:-1]:
        # Si la clave no existe, podrías crear un dict vacío o lanzar error
        target = target.setdefault(key, {})

    # Asignamos el valor en la última clave
    target[keys[-1]] = value

    save(filename, data)


def _compact_dumps(obj, indent: int = 2) -> str:
    """
    Serializa obj con indent normal pero colapsa en una sola línea
    cualquier lista que contenga solo números (o listas de números, etc.),
    imitando el formato legible de arrays numpy.
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
