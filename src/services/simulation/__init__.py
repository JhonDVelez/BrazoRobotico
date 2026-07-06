"""
Paquete de simulación del brazo robótico con PyBullet.

Gestiona la simulación física del modelo 3D, el entorno de PyBullet,
el envío y recepción de datos de este, las mallas y texturas del
modelo visible en la interfaz, y el archivo URDF empleado por PyBullet.

Señales:
    - SimulationSignalManager.update_pybullet_signal: Actualiza posiciones
      objetivo de la simulación.
    - GlobalTimer.update_tick: Sincroniza el paso de simulación.
    - GlobalTimer.model_tick: Actualiza la visualización 3D.
    - GlobalTimer.sync_simulation_tick: Actualiza las gráficas.
"""

from .physics_worker import PhysicsWorker

__all__ = [
    "PhysicsWorker"
]
