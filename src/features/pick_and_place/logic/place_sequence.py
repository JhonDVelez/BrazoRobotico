"""
Modulo que implementa la secuencia de colocacion (Place) para el PickAndPlaceWorker.
"""

import math
from src.features.pick_and_place.pick_place_states import PickPlaceState


class PlaceSequenceLogic:
    """Mixin que maneja los estados de la fase de Place."""

    def _enter_computing_ik_place_above(self):
        """Solicita IK para una posicion elevada sobre el destino."""
        if not self._place_target_coords:
            self._fail('No se definieron coordenadas de destino')
            return

        x = self._place_target_coords['x']
        y = self._place_target_coords['y']
        z = self._place_target_coords['z']

        r = 23
        angle = math.atan(x / (y + 100))
        x_comp = x + r * math.sin(1.5708 - angle)
        y_comp = y - r * math.cos(1.5708 - angle)

        # Posicion elevada de seguridad
        self.action_request.emit({
            'type': 'compute_ik',
            'coords': {'x': y_comp, 'y': x_comp, 'z': 100},
            'gripper_degrees': self._gripper_closed,
            'description': f'Calculando posicion elevada para destino'
        })

    def _enter_approaching_place_above(self):
        """Mueve el brazo a la posicion elevada sobre el destino."""
        if self._ik_target is None:
            self._fail('No hay objetivo IK para destino elevado')
            return
        self._current_target = self._ik_target
        self._start_stall_timer()
        self.action_request.emit({
            'type': 'move',
            'target': self._ik_target,
            'description': 'Aproximando a destino (elevado)'
        })

    def _enter_computing_ik_place(self):
        """Solicita cinematica inversa para el punto de destino final."""
        if not self._place_target_coords:
            self._fail('No se definieron coordenadas de destino')
            return

        x = self._place_target_coords['x']
        y = self._place_target_coords['y']
        z = self._place_target_coords['z']

        r = 23
        angle = math.atan(x / (y + 100))
        x_comp = x + r * math.sin(1.5708 - angle)
        y_comp = y - r * math.cos(1.5708 - angle)

        self.action_request.emit({
            'type': 'compute_ik',
            'coords': {'x': y_comp, 'y': x_comp, 'z': z + 30},
            'gripper_degrees': self._gripper_closed,
            'description': f'Calculando IK para posicion final de destino'
        })

    def _enter_approaching_place(self):
        """Mueve el brazo hacia el punto de destino con pinza cerrada."""
        if self._ik_target is None:
            self._fail('No hay objetivo IK para destino')
            return
        self._current_target = self._ik_target
        self._start_stall_timer()
        self.action_request.emit({
            'type': 'move',
            'target': self._ik_target,
            'description': 'Descendiendo a posicion de destino'
        })

    def _enter_releasing(self):
        """Abre la pinza para soltar la esfera en el destino."""
        if self._ik_target is None:
            self._fail('No hay objetivo IK para soltar')
            return
        target = self._with_gripper(self._ik_target, self._gripper_open)
        self._current_target = target
        self._start_stall_timer()
        self.action_request.emit({
            'type': 'move',
            'target': target,
            'description': 'Liberando objeto'
        })

    def _enter_returning_home(self):
        """Regresa a posicion neutral cerrando la pinza."""
        # Al regresar a home cerramos la pinza a su posicion neutral (0 en relativo)
        target = self._relative_to_servo([0, 0, 0, 0, 90, 0])
        self._current_target = target
        self._start_stall_timer()
        self.action_request.emit({
            'type': 'move',
            'target': target,
            'description': 'Finalizado: Regresando a neutral'
        })
