""" Paquete de mixin donde se define el comportamiento y estructura de la interfaz principal asi 
    como los elementos que contiene.
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
