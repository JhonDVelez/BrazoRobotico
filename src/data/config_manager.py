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
        "theme.json": {"name": "dark"},
    },
    "camera.json": {
        "resolution": {"width": 1280, "height": 720, "fps": 30},
        "matrix": [[2508.585084877413, 0.0, 549.6703652888866],
                   [0.0, 1930.136835739443, 313.33439561862957],
                   [0.0, 0.0, 1.0]],
        "distortion coefficients": [[-0.3291138248842348, 19.447590579083318,
                                     0.30719832291783716, -0.076422775409491,
                                     -432.1376103325584]],
    },

}


def init_config() -> None:
    """Crea CONFIG_DIR y los archivos que falten con sus valores por defecto."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    for filename, defaults in DEFAULTS.items():
        path = CONFIG_DIR / filename
        if not path.exists():
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


def get(filename: str, key: str, default=None):
    """Acceso rápido a una sola clave."""
    return load(filename).get(key, default)


def set_value(filename: str, key: str, value) -> None:
    """Modifica una sola clave y guarda."""
    data = load(filename)
    data[key] = value
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
