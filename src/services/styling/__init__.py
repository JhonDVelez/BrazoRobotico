"""
Paquete de gestión de temas y estilos de la interfaz.

Proporciona ThemeManager (cambio entre tema claro/oscuro) y las
hojas de estilo QSS personalizadas para cada tema.

Señales:
    - ThemeSignalManager: Gestiona el cambio de tema y notifica
      a las ventanas hijas cuando el tema del sistema cambia.
"""

from .theme_manger import ThemeManager

__all__ = [
    "ThemeManager"
]
