"""_summary_
Este paquete organiza la lógica de la ventana principal utilizando el patrón de diseño Mixin.
Cada módulo importado aporta una funcionalidad específica a la clase de la interfaz principal,
permitiendo una separación clara de responsabilidades (UI, Temas, Acciones, etc.).
"""

# Mixin encargado del procesamiento y manejo de recursos de imagen (iconos, pixmaps, etc.)
from .image_utils_mixin import ImageUtilsMixin

# Mixin que contiene los slots y funciones de respuesta a eventos (acciones de botones, lógica de control)
from .main_actions_mixin import MainActionsMixin

# Mixin que gestiona la inicialización de componentes, layouts y configuración inicial de la ventana
from .main_init_mixin import MainInitMixin

# Mixin dedicado a la creación y gestión de la barra de menús y opciones desplegables
from .main_menu_mixin import MainMenuMixin

# Mixin y clase gestora para el control de la apariencia visual (Modo oscuro/claro, estilos QSS)
from .main_theme_mixin import MainThemeMixin, ThemeManager

# Mixin especializado en la personalización de la barra de título (botones de cerrar, minimizar y arrastre)
from .main_title_bar_mixin import MainTitleBarMixin