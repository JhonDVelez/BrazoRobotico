"""
Módulo que controla la lógica de Pick and Place y la interacción con la UI.

El PickAndPlaceController orquesta la detección de objetos a través de la cámara,
la confirmación del usuario, y coordina el PickAndPlaceWorker con el bus global
de señales para ejecutar la secuencia de pickup y colocación.

Conexiones:
    - Overlay -> Controller: sphere_selected(str) cuando el usuario elige una esfera.
    - Bus Global -> Worker: poses_from_camera, target_reached, inverse_kinematics_ready.
    - Worker -> Bus Global: action_request(dict) ruteado a Simulation/Physical/Kinematics.
"""

from PyQt6.QtCore import QObject, pyqtSlot, QEvent
import numpy as np
from src.services.data.signals import (
    PickPlaceSignalManager, SimulationSignalManager,
    PhysicalSignalManager, CameraSignalManager
)
from src.features.pick_and_place.pick_and_place_widget import PickAndPlaceWidget
from src.features.pick_and_place.pick_and_place_worker import PickAndPlaceWorker
from src.services.data.enums import Modes
from src.services.ui.notification_manager import NotificationManager
from src.services.data.enums.types import NotificationType


class PickAndPlaceController(QObject):
    """Controlador para el feature de Pick and Place.

    Gestiona la interaccion del usuario sobre la vista de camara,
    instancia y coordina el PickAndPlaceWorker, y rutea las acciones
    del worker hacia el bus global de señales.

    Attributes:
        overlay: Widget transparente para seleccion de esferas.
        worker: Worker con maquina de estados para la secuencia.
    """

    def __init__(self, camera_widget=None):
        """Inicializa el controlador, worker y overlay.

        Args:
            camera_widget: Widget de camara donde se superpone el overlay.
        """
        super().__init__()
        self.signal_manager = PickPlaceSignalManager.get_instance()
        self.sim_signals = SimulationSignalManager.get_instance()
        self.camera_widget = None
        self._filter_installed = False

        self.overlay = PickAndPlaceWidget()
        self.worker = PickAndPlaceWorker()
        self._current_color = None

        if camera_widget:
            self.set_camera_widget(camera_widget)

        self._setup_connections()
        self._on_state_changed(self.signal_manager.get_state())

        self.noti_manager = NotificationManager.get_instance()

    def _setup_connections(self):
        """        Configura conexiones entre señales globales, worker y overlay."""
        self.signal_manager.state_changed.connect(self._on_state_changed)
        self.signal_manager.spheres_detected_2d.connect(
            self._on_spheres_detected_2d)

        # Conectar resultados de charuco para modo Place
        CameraSignalManager.get_instance().charuco_done.connect(self._on_charuco_done)

        self.overlay.sphere_selected.connect(self._request_pick)
        self.overlay.place_requested.connect(self._request_place)

        self.signal_manager.poses_from_camera.connect(
            self.worker.on_poses_from_camera)
        self.signal_manager.target_reached.connect(
            self.worker.on_target_reached)
        self.signal_manager.inverse_kinematics_ready.connect(
            self.worker.on_ik_ready)

        self.worker.action_request.connect(self._route_action)
        self.worker.sequence_completed.connect(self._on_sequence_completed)
        self.worker.sequence_failed.connect(self._on_sequence_failed)

        sim_signals = SimulationSignalManager.get_instance()
        phys_signals = PhysicalSignalManager.get_instance()
        sim_signals.update_graph_signal.connect(
            self.worker.on_feedback_update)
        phys_signals.update_graph_signal.connect(
            self.worker.on_feedback_update)

    def set_camera_widget(self, camera_widget):
        """        Asocia el controlador con el widget de cámara."""
        if self.camera_widget and self._filter_installed:
            self.camera_widget.removeEventFilter(self)
            self._filter_installed = False

        self.camera_widget = camera_widget
        self.overlay.setParent(camera_widget)
        if camera_widget:
            # Obtener configuración de cámara para el widget (matriz, distorsión)
            config = camera_widget.camera_config
            matrix = config.get("matrix")
            dist = config.get("distortion coefficients")

            self.overlay.update_config(
                camera_widget.orig_w,
                camera_widget.orig_h
            )

            # Pasar parámetros de cámara al pose_data del widget asegurando tipos numpy
            if self.overlay._charuco_pose is None:
                self.overlay._charuco_pose = {}

            self.overlay._charuco_pose.update({
                'camera_matrix': np.array(matrix, dtype=np.float64) if matrix else None,
                'dist_coeffs': np.array(dist, dtype=np.float64) if dist else None
            })

            self.overlay.resize(camera_widget.size())
            self._sync_overlay_stack()
            if self.signal_manager.get_state():
                self._install_filter()

    @pyqtSlot(bool)
    def _on_state_changed(self, active):
        """Maneja la activacion/desactivacion del modo Pick and Place."""
        if active:
            if self.camera_widget:
                self.overlay.resize(self.camera_widget.size())
            self.overlay.show()
            self._sync_overlay_stack()
            self._install_filter()
        else:
            self.overlay.hide()
            self.worker.abort()
            if self.camera_widget and self._filter_installed:
                self.camera_widget.removeEventFilter(self)
                self._filter_installed = False

    def _install_filter(self):
        """Instala el filtro para sincronizar el redimensionamiento."""
        if self.camera_widget and not self._filter_installed:
            self.camera_widget.installEventFilter(self)
            self._filter_installed = True

    def _sync_overlay_stack(self):
        """Mantiene el overlay sobre la imagen y los controles al frente."""
        self.overlay.raise_()
        if self.camera_widget:
            self.camera_widget.buttons_widget.raise_()
            self.camera_widget.toast.raise_()

    @pyqtSlot(dict)
    def _on_spheres_detected_2d(self, circles_2d):
        """Actualiza el estado del overlay con nuevas detecciones."""
        if self.overlay.isVisible():
            self.overlay.update_detected_circles(circles_2d)

    @pyqtSlot(int, object)
    def _on_charuco_done(self, frame_id, data):
        """Actualiza la pose del tablero en el overlay."""
        if self.overlay.isVisible() and data:
            if self.overlay._charuco_pose is None:
                self.overlay._charuco_pose = {}

            self.overlay._charuco_pose.update({
                'rvec': data.get('rvec'),
                'tvec': data.get('tvec')
            })
            self.overlay.update()

    @pyqtSlot(str)
    def _request_pick(self, color):
        """Inicia la secuencia de pick para la esfera del color indicado.

        Args:
            color (str): Color de la esfera seleccionada por el usuario.
        """
        self._current_color = color
        self.signal_manager.sphere_selected.emit(color)
        self.sim_signals.change_mode_signal.emit(Modes.KINEMATIC)
        self.signal_manager.release_sphere_request.emit(color)
        self.signal_manager.set_pick_place_running(True)
        # Desactivar búsqueda de esferas durante el movimiento para evitar ruido.
        # Ruteado por el DataController hacia SearchSignalManager.
        self.signal_manager.search_circle_request.emit(False)
        self.worker.pick(color)

    @pyqtSlot(dict)
    def _request_place(self, coords):
        """Inicia la secuencia de place para las coordenadas indicadas.

        Args:
            coords (dict): Coordenadas {x, y, z} seleccionadas en el tablero.
        """
        self.signal_manager.place_requested.emit(coords)
        self.signal_manager.set_pick_place_running(True)
        # Desactivar búsqueda de esferas durante el movimiento.
        # Ruteado por el DataController hacia SearchSignalManager.
        self.signal_manager.search_circle_request.emit(False)
        self.worker.place(coords)

    @pyqtSlot(dict)
    def _route_action(self, action):
        """Rutea las acciones del worker hacia el bus global de señales.

        Args:
            action (dict): Acción emitida por el worker con claves
                'type' y datos específicos del tipo de acción.
        """
        action_type = action.get('type')
        if action_type == 'move':
            self.sim_signals.update_target_signal.emit(action['target'])
        elif action_type == 'compute_ik':
            self.signal_manager.inverse_kinematics_requested.emit(action)

    @pyqtSlot()
    def _on_sequence_completed(self):
        """Maneja la finalización exitosa de la secuencia."""
        # Primero desactivamos el flag de ejecucion para permitir actualizaciones de posicion
        self.signal_manager.set_pick_place_running(False)

        # Si terminamos un Pick, pasar a modo Place
        if self.worker.current_state_value == 'idle':
            # Determinar si venimos de un Pick o de un Place
            if self.overlay._mode == 'pick':
                # Terminamos Pick, pasamos a Place. NO reactivamos camara aun.
                self.overlay.set_mode('place')
            else:
                # Terminamos Place, regresamos a Pick. Reactivamos camara y reasociamos esfera.
                if self._current_color:
                    self.signal_manager.reattach_sphere_request.emit(
                        self._current_color)
                    self._current_color = None

                self.signal_manager.search_circle_request.emit(True)
                self.overlay.set_mode('pick')

        self.sim_signals.change_mode_signal.emit(Modes.KINEMATIC)

    @pyqtSlot(str)
    def _on_sequence_failed(self, reason):
        """Maneja el fallo de la secuencia.

        Args:
            reason (str): Descripción del error.
        """
        # Desactivamos flag antes de reactivar camara
        self.signal_manager.set_pick_place_running(False)

        # Reactivar búsqueda de esferas y reasociar esfera en caso de fallo
        if self._current_color:
            self.signal_manager.reattach_sphere_request.emit(
                self._current_color)
            self._current_color = None

        self.signal_manager.search_circle_request.emit(True)

        self.noti_manager.notify(
            f'Secuencia fallida de PickAndPlace: {reason}', NotificationType.DIALOG_WARNING)

    def eventFilter(self, watched, event):
        """Captura eventos del CameraWidget para el overlay."""
        if watched == self.camera_widget:
            if event.type() == QEvent.Type.Resize:
                self.overlay.resize(event.size())
                self._sync_overlay_stack()
        return super().eventFilter(watched, event)

    def get_widget(self):
        """Retorna el widget overlay."""
        return self.overlay
