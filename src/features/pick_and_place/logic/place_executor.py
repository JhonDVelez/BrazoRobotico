"""
Módulo que implementa la lógica de la secuencia de colocación (Place).
"""

import math
from src.features.pick_and_place.logic.base_executor import BaseExecutor
from src.services.data.signals import ConfigSignalManager

class PlaceExecutor(BaseExecutor):
    """Ejecutor especializado en la fase de Place."""

    def enter_computing_ik_place_above(self):
        """        Solicita IK para posición elevada sobre el destino."""
        if not self.context.place_target_coords:
            self.worker._fail('No se definieron coordenadas de destino')
            return

        x = self.context.place_target_coords['x']
        y = self.context.place_target_coords['y']
        z = self.context.place_target_coords['z']

        radius = ConfigSignalManager.get_instance().get_param(
            "camera.json", "sphere_radius", default=20.0)
        r = radius + 3.0
        angle = math.atan(x / (y + 100))
        x_comp = x + r * math.sin(1.5708 - angle)
        y_comp = y - r * math.cos(1.5708 - angle)

        self.worker.action_request.emit({
            'type': 'compute_ik',
            'coords': {'x': y_comp, 'y': x_comp, 'z': 100},
            'gripper_degrees': self.context.gripper_closed,
            'description': f'Calculando posición elevada para destino'
        })

    def enter_approaching_place_above(self):
        """        Mueve el brazo a la posición elevada sobre el destino."""
        if self.context.ik_target is None:
            self.worker._fail('No hay objetivo IK para destino elevado')
            return
        self.context.current_target = self.context.ik_target
        self.worker._start_stall_timer()
        self.worker.action_request.emit({
            'type': 'move',
            'target': self.context.ik_target,
            'description': 'Aproximando a destino (elevado)'
        })

    def enter_computing_ik_place(self):
        """Solicita IK para el punto de destino final."""
        if not self.context.place_target_coords:
            self.worker._fail('No se definieron coordenadas de destino')
            return

        x = self.context.place_target_coords['x']
        y = self.context.place_target_coords['y']
        z = self.context.place_target_coords['z']

        radius = ConfigSignalManager.get_instance().get_param(
            "camera.json", "sphere_radius", default=20.0)
        r = radius + 3.0
        angle = math.atan(x / (y + 100))
        x_comp = x + r * math.sin(1.5708 - angle)
        y_comp = y - r * math.cos(1.5708 - angle)

        self.worker.action_request.emit({
            'type': 'compute_ik',
            'coords': {'x': y_comp, 'y': x_comp, 'z': z + 30},
            'gripper_degrees': self.context.gripper_closed,
            'description': f'Calculando IK para posición final de destino'
        })

    def enter_approaching_place(self):
        """Mueve el brazo hacia el punto de destino."""
        if self.context.ik_target is None:
            self.worker._fail('No hay objetivo IK para destino')
            return
        self.context.current_target = self.context.ik_target
        self.worker._start_stall_timer()
        self.worker.action_request.emit({
            'type': 'move',
            'target': self.context.ik_target,
            'description': 'Descendiendo a posicion de destino'
        })

    def enter_releasing(self):
        """Abre la pinza para soltar."""
        if self.context.ik_target is None:
            self.worker._fail('No hay objetivo IK para soltar')
            return
        target = self._with_gripper(self.context.ik_target, self.context.gripper_open)
        self.context.current_target = target
        self.worker._start_stall_timer()
        self.worker.action_request.emit({
            'type': 'move',
            'target': target,
            'description': 'Liberando objeto'
        })

    def enter_returning_home(self):
        """        Regresa a posición neutral."""
        target = self._relative_to_servo([0, 0, 0, 0, 90, 0])
        self.context.current_target = target
        self.worker._start_stall_timer()
        self.worker.action_request.emit({
            'type': 'move',
            'target': target,
            'description': 'Finalizado: Regresando a neutral'
        })
