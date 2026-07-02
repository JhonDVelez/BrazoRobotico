"""
Módulo que define la base para los ejecutores de lógica de Pick and Place.
"""

class BaseExecutor:
    """Clase base para ejecutores de secuencias.
    
    Provee utilidades comunes y acceso al contexto compartido.
    """

    def __init__(self, worker, context):
        """
        Inicializa el ejecutor.

        Args:
            worker: Instancia del PickAndPlaceWorker (para emitir acciones).
            context (PickPlaceContext): Contexto de datos compartido.
        """
        self.worker = worker
        self.context = context

    def _relative_to_servo(self, positions):
        """        Convierte ángulos relativos a posiciones absolutas de servo."""
        return [float(value + 150.0) for value in positions]

    def _with_gripper(self, status, gripper_degrees):
        """Copia un objetivo y establece la pinza en grados relativos."""
        updated = list(status)
        updated[-1] = float(gripper_degrees + 150.0)
        return updated

    def _fail(self, reason):
        """Notifica fallo al worker."""
        self.worker._fail(reason)
