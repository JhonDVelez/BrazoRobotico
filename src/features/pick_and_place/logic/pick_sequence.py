"""
Modulo que implementa la secuencia de captura (Pick) para el PickAndPlaceWorker.
"""

import math
from src.features.pick_and_place.pick_place_states import PickPlaceState


class PickSequenceLogic:
    """Mixin que maneja los estados de la fase de Pick."""

    def _enter_homing(self):
        """Envia el brazo a posicion neutral con pinza en estado medio."""
        target = self._relative_to_servo([0, 0, 0, 0, 90, 0])
        self._current_target = target
        self._start_stall_timer()
        self.action_request.emit({
            'type': 'move',
            'target': target,
            'description': 'Moviendo a posicion neutral'
        })

    def _enter_computing_ik_above(self):
        """Solicita IK para una posicion elevada sobre la esfera."""
        sphere_pose = self._sphere_poses.get(self._selected_color)
        if not sphere_pose or 'position' not in sphere_pose:
            self._fail('No se encontro pose para la esfera seleccionada')
            return

        x, y, z = sphere_pose['position']
        r = 23
        angle = math.atan(x/(y+100))
        x_comp = x + r*math.sin(1.5708 - angle)
        y_comp = y - r*math.cos(1.5708 - angle)

        # Altura intermedia de seguridad
        above_z = 100

        self.action_request.emit({
            'type': 'compute_ik',
            'color': self._selected_color,
            'coords': {'x': y_comp, 'y': x_comp, 'z': above_z},
            'gripper_degrees': self._gripper_closed,
            'description': f'Calculando posicion elevada para {self._selected_color}'
        })

    def _enter_approaching_above(self):
        """Mueve el brazo a la posicion elevada con pinza cerrada."""
        if self._ik_target is None:
            self._fail('No hay objetivo IK para posicion elevada')
            return
        self._current_target = self._ik_target
        self._start_stall_timer()
        self.action_request.emit({
            'type': 'move',
            'target': self._ik_target,
            'description': 'Aproximando a posicion elevada'
        })

    def _enter_opening_gripper(self):
        """Abre la pinza en la posicion elevada actual."""
        if self._current_feedback is None:
            target = list(self._ik_target)
        else:
            target = self._current_feedback.tolist() if hasattr(
                self._current_feedback, 'tolist') else list(self._current_feedback)

        target = self._with_gripper(target, self._gripper_open)
        self._current_target = target
        self._start_stall_timer()
        self.action_request.emit({
            'type': 'move',
            'target': target,
            'description': 'Abriendo pinza sobre el objetivo'
        })

    def _enter_computing_ik(self):
        """Solicita calculo de cinematica inversa para la esfera."""
        sphere_pose = self._sphere_poses.get(self._selected_color)
        if not sphere_pose or 'position' not in sphere_pose:
            self._fail('No se encontro pose para la esfera seleccionada')
            return

        x, y, z = sphere_pose['position']
        r = 23
        angle = math.atan(x/(y+100))
        x_comp = x + r*math.sin(1.5708 - angle)
        y_comp = y - r*math.cos(1.5708 - angle)

        self.action_request.emit({
            'type': 'compute_ik',
            'color': self._selected_color,
            'coords': {'x': y_comp, 'y': x_comp, 'z': z/2},
            'gripper_degrees': self._gripper_open,
            'description': f'Calculando IK para esfera {self._selected_color}'
        })

    def _enter_approaching(self):
        """Mueve el brazo hacia la esfera con pinza abierta."""
        if self._ik_target is None:
            self._fail('No hay objetivo IK calculado')
            return
        self._current_target = self._ik_target
        self._start_stall_timer()
        self.action_request.emit({
            'type': 'move',
            'target': self._ik_target,
            'description': 'Descendiendo hacia la esfera'
        })

    def _enter_grasping(self):
        """Cierra la pinza para sujetar la esfera."""
        if self._ik_target is None:
            self._fail('No hay objetivo IK para cerrar pinza')
            return
        # Usamos el angulo maximo de cierre para detectar el objeto por stall
        target = self._with_gripper(self._ik_target, self._GRIPPER_MAX_CLOSED)
        self._current_target = target
        self._start_stall_timer()
        self.action_request.emit({
            'type': 'move',
            'target': target,
            'description': 'Cerrando pinza (detectando objeto)'
        })

    def _enter_lifting(self):
        """Regresa a posicion neutral con la esfera sujetada."""
        target = self._relative_to_servo(
            [0, 0, 0, 0, 90, self._gripper_closed])
        self._current_target = target
        self._start_stall_timer()
        self.action_request.emit({
            'type': 'move',
            'target': target,
            'description': 'Levantando objeto'
        })
