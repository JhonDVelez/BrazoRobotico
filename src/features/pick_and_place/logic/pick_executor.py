"""
Modulo que implementa la logica de la secuencia de captura (Pick).
"""

import math
from src.features.pick_and_place.logic.base_executor import BaseExecutor

class PickExecutor(BaseExecutor):
    """Ejecutor especializado en la fase de Pick."""

    def enter_homing(self):
        """Envia el brazo a posicion neutral."""
        target = self._relative_to_servo([0, 0, 0, 0, 90, 0])
        self.context.current_target = target
        self.worker._start_stall_timer()
        self.worker.action_request.emit({
            'type': 'move',
            'target': target,
            'description': 'Moviendo a posicion neutral'
        })

    def enter_computing_ik_above(self):
        """Solicita IK para posicion elevada sobre la esfera."""
        sphere_pose = self.context.sphere_poses.get(self.context.selected_color)
        if not sphere_pose or 'position' not in sphere_pose:
            self.worker._fail('No se encontro pose para la esfera seleccionada')
            return

        x, y, z = sphere_pose['position']
        r = 23
        angle = math.atan(x/(y+100))
        x_comp = x + r*math.sin(1.5708 - angle)
        y_comp = y - r*math.cos(1.5708 - angle)
        above_z = 100

        self.worker.action_request.emit({
            'type': 'compute_ik',
            'color': self.context.selected_color,
            'coords': {'x': y_comp, 'y': x_comp, 'z': above_z},
            'gripper_degrees': self.context.gripper_closed,
            'description': f'Calculando posicion elevada para {self.context.selected_color}'
        })

    def enter_approaching_above(self):
        """Mueve el brazo a la posicion elevada."""
        if self.context.ik_target is None:
            self.worker._fail('No hay objetivo IK para posicion elevada')
            return
        self.context.current_target = self.context.ik_target
        self.worker._start_stall_timer()
        self.worker.action_request.emit({
            'type': 'move',
            'target': self.context.ik_target,
            'description': 'Aproximando a posicion elevada'
        })

    def enter_opening_gripper(self):
        """Abre la pinza."""
        if self.context.current_feedback is None:
            target = list(self.context.ik_target)
        else:
            fb = self.context.current_feedback
            target = fb.tolist() if hasattr(fb, 'tolist') else list(fb)

        target = self._with_gripper(target, self.context.gripper_open)
        self.context.current_target = target
        self.worker._start_stall_timer()
        self.worker.action_request.emit({
            'type': 'move',
            'target': target,
            'description': 'Abriendo pinza sobre el objetivo'
        })

    def enter_computing_ik(self):
        """Solicita IK para la esfera."""
        sphere_pose = self.context.sphere_poses.get(self.context.selected_color)
        if not sphere_pose or 'position' not in sphere_pose:
            self.worker._fail('No se encontro pose para la esfera seleccionada')
            return

        x, y, z = sphere_pose['position']
        r = 23
        angle = math.atan(x/(y+100))
        x_comp = x + r*math.sin(1.5708 - angle)
        y_comp = y - r*math.cos(1.5708 - angle)

        self.worker.action_request.emit({
            'type': 'compute_ik',
            'color': self.context.selected_color,
            'coords': {'x': y_comp, 'y': x_comp, 'z': z/2},
            'gripper_degrees': self.context.gripper_open,
            'description': f'Calculando IK para esfera {self.context.selected_color}'
        })

    def enter_approaching(self):
        """Mueve el brazo hacia la esfera."""
        if self.context.ik_target is None:
            self.worker._fail('No hay objetivo IK calculado')
            return
        self.context.current_target = self.context.ik_target
        self.worker._start_stall_timer()
        self.worker.action_request.emit({
            'type': 'move',
            'target': self.context.ik_target,
            'description': 'Descendiendo hacia la esfera'
        })

    def enter_grasping(self):
        """Cierra la pinza."""
        if self.context.ik_target is None:
            self.worker._fail('No hay objetivo IK para cerrar pinza')
            return
        target = self._with_gripper(self.context.ik_target, self.context.gripper_max_closed)
        self.context.current_target = target
        self.worker._start_stall_timer()
        self.worker.action_request.emit({
            'type': 'move',
            'target': target,
            'description': 'Cerrando pinza (detectando objeto)'
        })

    def enter_lifting(self):
        """Levanta la esfera."""
        target = self._relative_to_servo([0, 0, 0, 0, 90, self.context.gripper_closed])
        self.context.current_target = target
        self.worker._start_stall_timer()
        self.worker.action_request.emit({
            'type': 'move',
            'target': target,
            'description': 'Levantando objeto'
        })
