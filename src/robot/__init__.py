""" En este paquete se encuentra lo relacionado al control del robot openbotv v1 físico, como su
    conexión a la interfaz, envió y recepción de datos y procesamientos necesarios para realizarlos
    adecuadamente, asi como filtrado y verificación de datos para evitar errores.
"""

from .openbotv_worker import RobotWriterWorker, RobotReaderWorker

__all__ = [
    "RobotWriterWorker",
    "RobotReaderWorker"
]
