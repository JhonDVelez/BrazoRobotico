""" Paquete que almacena las hojas de estilos de los temas claro y oscuro de la interfaz en 
    variables llamadas STYLE_SHEET
"""

from pathlib import Path

from .dark import STYLE_SHEET as dark_style
from .dark import ADS_STYLE_SHEET as _ads_dark_raw
from .light import STYLE_SHEET as light_style
from .light import ADS_STYLE_SHEET as _ads_light_raw

# Los estilos ADS referencian los iconos con rutas relativas
# (src/resources/icons/...) que Qt resuelve contra el directorio de trabajo.
# Se reemplazan por rutas absolutas para que funcionen también en el
# ejecutable empaquetado, donde el CWD no es el directorio del proyecto.
_ICONS_PATH = (Path(__file__).resolve().parents[3]
               / "resources" / "icons").as_posix()

ADS_DARK_STYLE = _ads_dark_raw.replace("src/resources/icons", _ICONS_PATH)
ADS_LIGHT_STYLE = _ads_light_raw.replace("src/resources/icons", _ICONS_PATH)
