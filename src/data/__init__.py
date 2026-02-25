""" Paquete encargado del control de flujo de datos donde se proporcionan clases y métodos
    para conexión, tratamiento, envió y recepción de distintos tipos de datos.
    Este archivo centraliza las herramientas de comunicación del sistema.
"""

# Importación de utilidades de control y constantes desde el módulo interno control_utils
from .control_utils import (
    SimulationSignalManager, # Gestor de señales específico para el entorno virtual
    PhysicalSignalManager,   # Gestor de señales específico para el hardware real
    Domains,                 # Enumeración para distinguir entre Simulación y Físico
    Modes,                   # Enumeración de modos de control (Sliders, Teclado, etc.)
    Units,                   # Enumeración para tipos de unidades (Radianes, Grados)
    rad_to_deg,              # Función de utilidad para conversión Rad -> Deg
    deg_to_rad)              # Función de utilidad para conversión Deg -> Rad

# Importación de la clase principal que orquesta el movimiento de datos
from .controller import DataFlow

# Definición de la interfaz pública del paquete.
# Esto controla qué elementos se exportan cuando alguien utiliza 'from data import *'
__all__ = [
    "SimulationSignalManager",
    "PhysicalSignalManager",
    "Domains",
    "Modes",
    "Units",
    "rad_to_deg",
    "deg_to_rad",
    "DataFlow",
]