"""
Paquete de mixins para la ventana principal.

Agrupa los mixins que definen el comportamiento y la estructura de la
interfaz principal, incluyendo acciones, inicializacion, menu y barra
de titulo personalizada.
"""

from src.main_window.mixins.main_actions_mixin import MainActionsMixin
from src.main_window.mixins.main_init_mixin import MainInitMixin
from src.main_window.mixins.main_menu_mixin import MainMenuMixin
from src.main_window.mixins.main_title_bar_mixin import MainTitleBarMixin

__all__ = [
    "MainActionsMixin",
    "MainInitMixin",
    "MainMenuMixin",
    "MainTitleBarMixin",
]
