"""
Paquete raiz de la aplicacion OpenBotv Control Lab.

Expone los subpaquetes principales del sistema:
- features: Modulos funcionales (calibracion, camara, color, graficos, cinematica, etc.).
- main_window: Ventana principal y mixins de inicializacion/menu/title bar.
- resources: Recursos estaticos (iconos, imagenes, QML).
- services: Servicios transversales (datos, dispositivos, robot, simulacion, etc.).
"""

from . import features, main_window, resources, services

__all__ = [
    "features",
    "main_window",
    "resources",
    "services"
]
