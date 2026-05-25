"""
Paquete de simulacion del brazo robotico con PyBullet.

Gestiona la simulacion fisica del modelo 3D, el entorno de PyBullet,
el envio y recepcion de datos de este, las mallas y texturas del
modelo visible en la interfaz, y el archivo URDF empleado por PyBullet.

Señales:
    - SimulationSignalManager.update_pybullet_signal: Actualiza posiciones
      objetivo de la simulacion.
    - GlobalTimer.update_tick: Sincroniza el paso de simulacion.
    - GlobalTimer.model_tick: Actualiza la visualizacion 3D.
    - GlobalTimer.sync_simulation_tick: Actualiza las graficas.
"""

from .physics_worker import PhysicsWorker

__all__ = [
    "PhysicsWorker"
]
