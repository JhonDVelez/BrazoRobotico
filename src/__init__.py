"""
Paquete raíz de la aplicación OpenBotv Control Lab.

Expone los subpaquetes principales del sistema:
- features: Módulos funcionales (calibración, cámara, color, gráficos, cinemática, etc.).
- main_window: Ventana principal y mixins de inicialización/menú/title bar.
- resources: Recursos estáticos (iconos, imágenes, QML).
- services: Servicios transversales (datos, dispositivos, robot, simulación, etc.).
"""

from . import features, main_window, resources, services

__all__ = [
    "features",
    "main_window",
    "resources",
    "services"
]
