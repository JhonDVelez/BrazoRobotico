""" Paquete donde se maneja la simulación en pybullet asi como el ambiente para el modelo 3D 
    mostrado en la interfaz, se tienen los parameters de pybullet, envío y recepción de datos de 
    este, tratamiento de los datos objetivos y obtenidos, mallas y texturas del modelo visible,
    urdf y mallas del modelo usado en pybullet, son diferentes debido al formato requerido.
"""

from .physics_worker import PhysicsWorker

__all__ = [
    "PhysicsWorker"
]
