""" Paquete encargado de la gestión de la interfaz tanto la interfaz principal como los widget y
    el manejo que se le dan a estos.
"""

# Importación de la clase principal que orquesta toda la ventana
from .app_interface import MainInterface

# Importaciones de componentes relacionados con la visión y captura de video
from .camera_interface import CameraInterface
from .camera_worker import VideoWorker

# Importaciones de componentes de telemetría y graficado de datos
from .graph_interface import GraphInterface
from .graph_worker import GraphWorker

# Importaciones relacionadas con el puente entre la lógica 3D/Física y la interfaz
from .simulation_interface import SimInterface
from .simulation_worker import SimWorker

# Importación del widget encargado del control manual mediante sliders
from .sliders_interface import SlidersWidget

# Definición de la variable __all__ para controlar el acceso público del paquete.
# Esto optimiza las importaciones desde otros módulos (ej. 'from gui import *')
# y expone explícitamente la API pública del paquete de interfaz.
__all__ = [
    "MainInterface",
    "CameraInterface",
    "VideoWorker",
    "GraphInterface",
    "GraphWorker",
    "SimInterface",
    "SimWorker",
    "SlidersWidget"
]