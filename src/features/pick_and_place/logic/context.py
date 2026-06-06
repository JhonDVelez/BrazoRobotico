"""
Modulo que define el contexto de datos para la secuencia Pick and Place.

Encapsula todo el estado compartido y constantes para evitar el acoplamiento
fuerte a traves de la herencia en el worker.
"""

class PickPlaceContext:
    """Contenedor de estado para la operacion de Pick and Place."""

    def __init__(self):
        # Estado de la operacion
        self.selected_color = None
        self.sphere_poses = {}
        self.place_target_coords = None
        self.ik_target = None
        
        # Estado de la pinza
        self.gripper_open = -112.0
        self.gripper_closed = 7.0
        self.gripper_max_closed = 21.0
        
        # Control de movimiento y feedback
        self.last_positions = None
        self.current_feedback = None
        self.current_target = None
        
        # Constantes de control
        self.STALL_TIMEOUT_MS = 1500
        self.MOVEMENT_TOLERANCE = 0.5
        self.SUCCESS_THRESHOLD = 2.0
        self.ERROR_THRESHOLD = 5.0

    def reset(self):
        """Limpia el estado interno para una nueva operacion."""
        self.selected_color = None
        self.place_target_coords = None
        self.ik_target = None
        self.current_target = None
        # Mantenemos sphere_poses y configuracion de pinza
