""" Paquete donde se maneja la simulación en pybullet asi como el ambiente para el modelo 3D 
    mostrado en la interfaz, se tienen los parameters de pybullet, envío y recepción de datos de 
    este, tratamiento de los datos objetivos y obtenidos, mallas y texturas del modelo visible,
    urdf y mallas del modelo usado en pybullet, son diferentes debido al formato requerido.

    Nota: El paquete separa la representación visual (QtQuick) de la representación 
    matemática/física (PyBullet) para optimizar el rendimiento.
"""

# Importación de la clase PhysicsWorker, que es el núcleo de la simulación física
from .physics_worker import PhysicsWorker

# Definición de la interfaz pública del paquete 'simulation'.
# Permite que otros módulos utilicen 'from simulation import PhysicsWorker' 
# de manera directa y limpia.
__all__ = [
    "PhysicsWorker"
]