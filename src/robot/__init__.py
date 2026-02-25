""" En este paquete se encuentra lo relacionado al control del robot openbotv v1 físico, como su
    conexión a la interfaz, envió y recepción de datos y procesamientos necesarios para realizarlos
    adecuadamente, asi como filtrado y verificación de datos para evitar errores.
    
    Este módulo abstrae la complejidad de la comunicación serial o de red para que el resto
    del programa solo vea un 'Worker' de control.
"""

# Importación de la clase principal que gestiona el hilo de ejecución para el hardware real
from .openbotv_worker import RobotWorker

# Definición de la interfaz pública del paquete 'robot'.
# Al incluir RobotWorker en __all__, se permite realizar una importación limpia:
# 'from robot import RobotWorker'
__all__ = [
    "RobotWorker"
]