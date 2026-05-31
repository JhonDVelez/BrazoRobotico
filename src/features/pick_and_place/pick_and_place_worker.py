"""
Modulo que define el PickAndPlaceWorker con maquina de estados.

Implementa la logica secuencial de pickup y colocacion de esferas
usando la libreria python-statemachine para coordinar las transiciones
entre estados, realimentado con datos de la simulacion o el robot fisico.

Conexiones (via PickAndPlaceController):
    - Escucha: pick_requested, inverse_kinematics_ready, target_reached
    - Emite: action_request(dict), sequence_completed(), sequence_failed(str)

Arquitectura:
    - El Worker NO importa SignalManagers directamente.
    - Recibe triggers a traves de slots conectados por su Controller.
    - Emite acciones a traves de signal local, ruteadas por el Controller.
    - Usa composicion: contiene un StateMachine internamente.
"""

import math
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer
from statemachine import StateMachine, State
from src.features.pick_and_place.pick_place_states import PickPlaceState
from src.services.data.utils import rad_to_deg


class _PickPlaceStateMachine(StateMachine):
    """Maquina de estados interna para la secuencia Pick and Place.

    Gestiona las transiciones entre fases de la secuencia. Cada estado
    tiene un callback ``on_enter_*`` que notifica al worker para emitir
    la accion correspondiente.

    Transiciones:
        start_pick:        idle -> homing
        homing_done:       homing -> opening_gripper
        gripper_opened:    opening_gripper -> computing_ik
        ik_computed:       computing_ik -> approaching
        close_gripper:     approaching -> grasping
        grasp_done:        grasping -> lifting
        lift_complete:     lifting -> idle
        reset:             cualquier estado -> idle (cancelacion/error)
    """

    idle = State(PickPlaceState.IDLE.value, initial=True)
    homing = State(PickPlaceState.HOMING.value)
    opening_gripper = State(PickPlaceState.OPENING_GRIPPER.value)
    computing_ik = State(PickPlaceState.COMPUTING_IK.value)
    approaching = State(PickPlaceState.APPROACHING.value)
    grasping = State(PickPlaceState.GRASPING.value)
    lifting = State(PickPlaceState.LIFTING.value)
    computing_ik_place = State(PickPlaceState.COMPUTING_IK_PLACE.value)
    approaching_place = State(PickPlaceState.APPROACHING_PLACE.value)
    releasing = State(PickPlaceState.RELEASING.value)
    returning_home = State(PickPlaceState.RETURNING_HOME.value)

    # Transiciones normales de la secuencia
    start_pick = idle.to(homing)
    homing_done = homing.to(opening_gripper)
    gripper_opened = opening_gripper.to(computing_ik)
    ik_computed = computing_ik.to(approaching)
    close_gripper = approaching.to(grasping)
    grasp_done = grasping.to(lifting)
    lift_complete = lifting.to(idle)

    # Transiciones para la secuencia de colocación (Place)
    start_place = idle.to(computing_ik_place)
    ik_computed_place = computing_ik_place.to(approaching_place)
    place_reached = approaching_place.to(releasing)
    gripper_released = releasing.to(returning_home)
    home_reached = returning_home.to(idle)

    # Transicion de reset/cancelacion desde cualquier estado no-idle
    reset = (
        homing.to(idle)
        | opening_gripper.to(idle)
        | computing_ik.to(idle)
        | approaching.to(idle)
        | grasping.to(idle)
        | lifting.to(idle)
        | computing_ik_place.to(idle)
        | approaching_place.to(idle)
        | releasing.to(idle)
        | returning_home.to(idle)
    )

    def __init__(self, on_state_change=None):
        """Inicializa la maquina de estados.

        Args:
            on_state_change: Callable invoked(name: str) en cada
                ``on_enter_*`` para notificar al worker.
        """
        super().__init__()
        self._on_state_change = on_state_change

    def on_enter_homing(self):
        if self._on_state_change:
            self._on_state_change(PickPlaceState.HOMING.value)

    def on_enter_opening_gripper(self):
        if self._on_state_change:
            self._on_state_change(PickPlaceState.OPENING_GRIPPER.value)

    def on_enter_computing_ik(self):
        if self._on_state_change:
            self._on_state_change(PickPlaceState.COMPUTING_IK.value)

    def on_enter_approaching(self):
        if self._on_state_change:
            self._on_state_change(PickPlaceState.APPROACHING.value)

    def on_enter_grasping(self):
        if self._on_state_change:
            self._on_state_change(PickPlaceState.GRASPING.value)

    def on_enter_lifting(self):
        if self._on_state_change:
            self._on_state_change(PickPlaceState.LIFTING.value)

    def on_enter_computing_ik_place(self):
        if self._on_state_change:
            self._on_state_change(PickPlaceState.COMPUTING_IK_PLACE.value)

    def on_enter_approaching_place(self):
        if self._on_state_change:
            self._on_state_change(PickPlaceState.APPROACHING_PLACE.value)

    def on_enter_releasing(self):
        if self._on_state_change:
            self._on_state_change(PickPlaceState.RELEASING.value)

    def on_enter_returning_home(self):
        if self._on_state_change:
            self._on_state_change(PickPlaceState.RETURNING_HOME.value)


class PickAndPlaceWorker(QObject):
    """Worker que orquesta la secuencia Pick and Place con maquina de estados.

    Utiliza python-statemachine para gestionar las transiciones entre
    fases de la secuencia. Cada estado emite una accion que el
    PickAndPlaceController rutea al bus global de senales.

    Attributes:
        action_request: Senal que emite una accion dict con claves
            'type' (str) y datos especificos del tipo de accion.
        sequence_completed: Senal emitida al finalizar la secuencia.
        sequence_failed: Senal emitida cuando la secuencia falla.
    """

    action_request = pyqtSignal(dict)
    sequence_completed = pyqtSignal()
    sequence_failed = pyqtSignal(str)

    def __init__(self):
        """Inicializa la maquina de estados y el estado interno."""
        super().__init__()
        self._sm = _PickPlaceStateMachine(
            on_state_change=self._on_state_change)
        self._selected_color = None
        self._sphere_poses = {}
        self._place_target_coords = None
        self._ik_target = None
        self._gripper_open = -112
        self._gripper_closed = 7

        self._state_stall_timer = QTimer()
        self._state_stall_timer.setSingleShot(True)
        self._state_stall_timer.timeout.connect(
            self._on_state_timeout)
        self._last_positions = None
        self._current_feedback = None
        self._current_target = None
        self._STALL_TIMEOUT_MS = 1500
        self._MOVEMENT_TOLERANCE = 0.5
        self._ERROR_THRESHOLD = 10.0

    @property
    def current_state_value(self):
        """Obtiene el valor del estado actual de la maquina.

        Returns:
            str: Valor del estado actual (e.g. 'idle', 'homing').
        """
        return self._sm.current_state_value

    def _on_state_change(self, state_name):
        """Callback invocado por la maquina de estados al entrar a un estado.

        Args:
            state_name (str): Nombre del estado que se esta ingresando.
        """
        handlers = {
            PickPlaceState.HOMING.value: self._enter_homing,
            PickPlaceState.OPENING_GRIPPER.value: self._enter_opening_gripper,
            PickPlaceState.COMPUTING_IK.value: self._enter_computing_ik,
            PickPlaceState.APPROACHING.value: self._enter_approaching,
            PickPlaceState.GRASPING.value: self._enter_grasping,
            PickPlaceState.LIFTING.value: self._enter_lifting,
            PickPlaceState.COMPUTING_IK_PLACE.value: self._enter_computing_ik_place,
            PickPlaceState.APPROACHING_PLACE.value: self._enter_approaching_place,
            PickPlaceState.RELEASING.value: self._enter_releasing,
            PickPlaceState.RETURNING_HOME.value: self._enter_returning_home,
        }
        handler = handlers.get(state_name)
        if handler:
            handler()

    # --- Acciones de entrada a estados ---

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

    def _enter_opening_gripper(self):
        """Abre la pinza en posicion neutral."""
        home = self._relative_to_servo([0, 0, 0, 0, 90, 0])
        target = self._with_gripper(home, self._gripper_open)
        self._current_target = target
        self._start_stall_timer()
        self.action_request.emit({
            'type': 'move',
            'target': target,
            'description': 'Abriendo pinza'
        })

    def _enter_computing_ik(self):
        """Solicita calculo de cinematica inversa para la esfera."""
        sphere_pose = self._sphere_poses.get(self._selected_color)
        if not sphere_pose or 'position' not in sphere_pose:
            self._fail('No se encontro pose para la esfera seleccionada')
            return

        x, y, z = sphere_pose['position']
        r = 23
        print(x, y, z)
        angle = math.atan(x/(y+100))
        x += r*math.sin(1.5708 - angle)
        y -= r*math.cos(1.5708 - angle)
        print(x, y, z)
        self.action_request.emit({
            'type': 'compute_ik',
            'color': self._selected_color,
            'coords': {'x': y, 'y': x, 'z': z/2},
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
            'description': 'Acercando a esfera'
        })

    def _enter_grasping(self):
        """Cierra la pinza para sujetar la esfera."""
        if self._ik_target is None:
            self._fail('No hay objetivo IK para cerrar pinza')
            return
        target = self._with_gripper(self._ik_target, self._gripper_closed)
        self._current_target = target
        self._start_stall_timer()
        self.action_request.emit({
            'type': 'move',
            'target': target,
            'description': 'Cerrando pinza (sujetando)'
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
            'description': 'Regresando a neutral con esfera'
        })

    def _enter_computing_ik_place(self):
        """Solicita cinematica inversa para el punto de destino."""
        if not self._place_target_coords:
            self._fail('No se definieron coordenadas de destino')
            return

        x = self._place_target_coords['x']
        y = self._place_target_coords['y']
        z = self._place_target_coords['z']
        
        # Compensacion r=23 similar al pick
        r = 23
        angle = math.atan(x / (y + 100))
        x_comp = x + r * math.sin(1.5708 - angle)
        y_comp = y - r * math.cos(1.5708 - angle)
        
        self.action_request.emit({
            'type': 'compute_ik',
            'coords': {'x': y_comp, 'y': x_comp, 'z': z + 30},
            'gripper_degrees': self._gripper_closed,
            'description': f'Calculando IK para posicion de destino'
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
            'description': 'Moviendo a posicion de destino'
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
            'description': 'Abriendo pinza (soltando)'
        })


    def _enter_returning_home(self):
        """Regresa a posicion neutral despues de soltar."""
        target = self._relative_to_servo([0, 0, 0, 0, 90, self._gripper_open])
        self._current_target = target
        self._start_stall_timer()
        self.action_request.emit({
            'type': 'move',
            'target': target,
            'description': 'Regresando a neutral'
        })

    # --- Triggers externos (slots conectados por el Controller) ---

    @pyqtSlot(str)
    def pick(self, color):
        """Inicia la secuencia de pick para una esfera del color indicado.

        Args:
            color (str): Color de la esfera a recoger (e.g. 'red', 'blue').
        """
        if self._sm.idle not in self._sm.configuration:
            return
        self._selected_color = color
        self._sm.start_pick()

    @pyqtSlot(dict)
    def place(self, coords):
        """Inicia la secuencia de place para las coordenadas indicadas.

        Args:
            coords (dict): Diccionario con claves 'x', 'y', 'z'.
        """
        if self._sm.idle not in self._sm.configuration:
            return
        self._place_target_coords = coords
        self._sm.start_place()

    @pyqtSlot(list)
    def on_target_reached(self, _positions):
        """Notifica que el robot alcanzo la posicion objetivo actual.

        Realimenta la maquina de estados con datos del robot o la
        simulacion para avanzar al siguiente estado.

        Args:
            _positions (list): Posiciones actuales del robot (servo 0-300).
        """
        self._state_stall_timer.stop()
        current = self.current_state_value
        transitions = {
            PickPlaceState.HOMING.value: self._sm.homing_done,
            PickPlaceState.OPENING_GRIPPER.value: self._sm.gripper_opened,
            PickPlaceState.APPROACHING.value: self._sm.close_gripper,
            PickPlaceState.GRASPING.value: self._sm.grasp_done,
            PickPlaceState.LIFTING.value: self._on_lift_complete,
            PickPlaceState.APPROACHING_PLACE.value: self._sm.place_reached,
            PickPlaceState.RELEASING.value: self._sm.gripper_released,
            PickPlaceState.RETURNING_HOME.value: self._on_home_reached,
        }
        transition = transitions.get(current)
        if transition:
            transition()

    def _on_lift_complete(self):
        """Maneja la completacion del estado LIFTING."""
        self._sm.lift_complete()
        self.sequence_completed.emit()

    def _on_home_reached(self):
        """Maneja la completacion del estado RETURNING_HOME."""
        self._sm.home_reached()
        self.sequence_completed.emit()

    @pyqtSlot(dict)
    def on_ik_ready(self, result):
        """Recibe el resultado de cinematica inversa.

        Args:
            result (dict): Debe contener 'target' con la lista de posiciones
                de servo calculadas por KinematicsController.
        """
        if self.current_state_value not in (PickPlaceState.COMPUTING_IK.value, PickPlaceState.COMPUTING_IK_PLACE.value):
            return
        target = result.get('target')
        if not target:
            self._fail('IK no encontro solucion valida')
            return
        self._ik_target = target
        self._sm.ik_computed() if self.current_state_value == PickPlaceState.COMPUTING_IK.value else self._sm.ik_computed_place()

    @pyqtSlot(dict)
    def on_poses_from_camera(self, poses):
        """Actualiza las poses 3D detectadas por la camara.

        Args:
            poses (dict): Diccionario {color: {'position': [x, y, z], ...}}.
        """
        self._sphere_poses.update(poses)

    @pyqtSlot()
    def abort(self):
        """Cancela la secuencia en curso y regresa a IDLE."""
        if self.current_state_value == PickPlaceState.IDLE.value:
            return
        self._clear_state()
        self._sm.reset()
        self.sequence_failed.emit('Secuencia cancelada')

    @pyqtSlot(list)
    def on_feedback_update(self, positions):
        """Recibe feedback de posiciones para stall detection.

        Monitorea el movimiento del robot. Si hay movimiento significativo,
        reinicia el timer de estancamiento.

        Args:
            positions (list): Posiciones actuales del robot.
        """
        if len(positions) < 6:
            return

        # Normalizar posiciones a unidades de servo (0-300) si es necesario.
        # Si el valor maximo es pequeno (ej. < 10 rad o deg relativos), asumimos relativo.
        # En la simulacion los valores son deg relativos [-150, 150].
        # En fisico son deg absolutos [0, 300].
        # La forma mas segura de distinguir es por el rango o por el origen.

        # Mapeo similar al del DataController para comparacion con target
        # Si el primer valor esta cerca de 0, es probable que sea relativo (simulacion)
        # Si esta cerca de 150, es probable que sea absoluto (fisico)
        if abs(positions[0]) < 140:  # Umbral para detectar simulacion (relativo)
            mapped = [-x+150 if i in (4, 5) else x+150 for i,
                      x in enumerate(positions)]
        else:
            mapped = positions

        self._current_feedback = mapped

        # Si el motor se esta moviendo, reiniciar el timer
        if self._last_positions is not None:
            max_delta = max(abs(p - lp)
                            for p, lp in zip(mapped, self._last_positions))
            if max_delta > self._MOVEMENT_TOLERANCE:
                if self._state_stall_timer.isActive():
                    self._state_stall_timer.start(self._STALL_TIMEOUT_MS)

        self._last_positions = mapped

    # --- Deteccion de estancamiento (Stall) ---

    def _start_stall_timer(self):
        """Inicia el timer de deteccion de estancamiento para el estado actual."""
        self._last_positions = None
        self._state_stall_timer.start(self._STALL_TIMEOUT_MS)

    def _on_state_timeout(self):
        """Callback del timer cuando el robot deja de moverse.

        Si al expirar el tiempo el error es aceptable (<10), avanza.
        De lo contrario, aborta a home por seguridad.
        """
        current = self.current_state_value
        # No aplicar stall logic a estados que no son de movimiento
        if current in (PickPlaceState.IDLE.value, PickPlaceState.COMPUTING_IK.value):
            return

        if self._current_feedback is None or self._current_target is None:
            return

        # Asegurar que feedback sea lista para evitar problemas con truth value de arrays
        feedback = self._current_feedback.tolist() if hasattr(
            self._current_feedback, 'tolist') else self._current_feedback

        # Calcular el error maximo actual
        max_error = max(abs(f - t)
                        for f, t in zip(feedback, self._current_target))

        if max_error < self._ERROR_THRESHOLD:
            # Error aceptable, forzar avance
            self._advance_state()
        else:
            # Error critico, abortar a home
            print(
                f"[PickPlace] Stall critico en {current} (Error: {max_error:.2f} deg)")
            self._abort_to_home()

    def _advance_state(self):
        """Fuerza la transicion al siguiente estado de la secuencia."""
        self._state_stall_timer.stop()
        current = self.current_state_value

        transitions = {
            PickPlaceState.HOMING.value: self._sm.homing_done,
            PickPlaceState.OPENING_GRIPPER.value: self._sm.gripper_opened,
            PickPlaceState.APPROACHING.value: self._sm.close_gripper,
            PickPlaceState.GRASPING.value: self._sm.grasp_done,
            PickPlaceState.LIFTING.value: self._on_lift_complete,
            PickPlaceState.APPROACHING_PLACE.value: self._sm.place_reached,
            PickPlaceState.RELEASING.value: self._sm.gripper_released,
            PickPlaceState.RETURNING_HOME.value: self._on_home_reached,
        }
        transition = transitions.get(current)
        if transition:
            transition()

    def _abort_to_home(self):
        """Aborta la secuencia regresando el brazo a posicion neutral."""
        self._state_stall_timer.stop()

        # Mover a home con la pinza en su posicion actual
        feedback = self._current_feedback.tolist() if hasattr(
            self._current_feedback, 'tolist') else self._current_feedback
        current_gripper = feedback[5] if feedback is not None else 150
        home_target = self._relative_to_servo([0, 0, 0, 0, 90, 0])
        home_target[5] = current_gripper

        self.action_request.emit({
            'type': 'move',
            'target': home_target,
            'description': 'Abortando: Regresando a neutral por error critico'
        })

        self._clear_state()
        self._sm.reset()
        self.sequence_failed.emit(
            "Error critico: Movimiento bloqueado o incompleto")

    # --- Metodos internos ---

    def _fail(self, reason):
        """Termina la secuencia con error.

        Args:
            reason (str): Descripcion del error ocurrido.
        """
        self._clear_state()
        self._sm.reset()
        self.sequence_failed.emit(reason)

    def _clear_state(self):
        """Limpia el estado interno sin alterar la maquina."""
        self._selected_color = None
        self._place_target_coords = None
        self._ik_target = None
        self._state_stall_timer.stop()
        self._last_gripper_pos = None

    @staticmethod
    def _relative_to_servo(positions):
        """Convierte angulos relativos a posiciones absolutas de servo.

        Args:
            positions (list): Lista de angulos relativos [-150, 150].

        Returns:
            list: Posiciones de servo [0, 300].
        """
        return [float(value + 150.0) for value in positions]

    @staticmethod
    def _with_gripper(status, gripper_degrees):
        """Copia un objetivo y establece la pinza en grados relativos.

        Args:
            status (list): Posiciones de servo actuales.
            gripper_degrees (float): Angulo de pinza en grados relativos.

        Returns:
            list: Nueva lista con la pinza actualizada.
        """
        updated = list(status)
        updated[-1] = float(gripper_degrees + 150.0)
        return updated
