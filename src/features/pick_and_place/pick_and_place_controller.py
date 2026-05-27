"""
Modulo que controla la logica de Pick and Place y la interaccion con la UI.

El PickAndPlaceController orquesta la deteccion de objetos a traves de la camara
y la confirmacion del usuario para iniciar las secuencias de movimiento.
"""

from PyQt6.QtCore import QObject, pyqtSlot, QEvent
from src.services.data.signals import PickPlaceSignalManager
from src.features.pick_and_place.pick_and_place_widget import PickAndPlaceWidget


class PickAndPlaceController(QObject):
    """
    Controlador para el feature de Pick and Place.

    Gestiona la interaccion del usuario sobre la vista de camara y
    coordina con el bus global de señales.
    """

    def __init__(self, camera_widget=None):
        super().__init__()
        self.signal_manager = PickPlaceSignalManager.get_instance()
        self.camera_widget = None
        self._filter_installed = False

        # Crear el overlay de interaccion (temporalmente sin parent si no hay)
        self.overlay = PickAndPlaceWidget()

        if camera_widget:
            self.set_camera_widget(camera_widget)

        self._setup_connections()

        # Estado inicial
        self._on_state_changed(self.signal_manager.get_state())

    def _setup_connections(self):
        """Configura las conexiones con el gestor de señales global."""
        self.signal_manager.state_changed.connect(self._on_state_changed)
        self.signal_manager.spheres_detected_2d.connect(
            self._on_spheres_detected_2d)

        # Conectar el overlay con el bus global
        self.overlay.sphere_selected.connect(self._request_pick)

    def set_camera_widget(self, camera_widget):
        """Asocia el controlador con el widget de camara."""
        if self.camera_widget and self._filter_installed:
            self.camera_widget.removeEventFilter(self)
            self._filter_installed = False

        self.camera_widget = camera_widget
        self.overlay.setParent(camera_widget)
        if camera_widget:
            self.overlay.update_config(
                camera_widget.orig_w, camera_widget.orig_h)
            self.overlay.resize(camera_widget.size())
            self._sync_overlay_stack()
            if self.signal_manager.get_state():
                self._install_filter()

    @pyqtSlot(bool)
    def _on_state_changed(self, active: bool):
        """Maneja la activacion/desactivacion del modo Pick and Place."""
        if active:
            if self.camera_widget:
                self.overlay.resize(self.camera_widget.size())
            self.overlay.show()
            self._sync_overlay_stack()
            self._install_filter()
        else:
            self.overlay.hide()
            if self.camera_widget and self._filter_installed:
                self.camera_widget.removeEventFilter(self)
                self._filter_installed = False

    def _install_filter(self):
        """Instala el filtro usado solo para sincronizar el redimensionamiento."""
        if self.camera_widget and not self._filter_installed:
            self.camera_widget.installEventFilter(self)
            self._filter_installed = True

    def _sync_overlay_stack(self):
        """Mantiene el overlay sobre la imagen y los controles de camara al frente."""
        self.overlay.raise_()
        if self.camera_widget:
            self.camera_widget.buttons_widget.raise_()
            self.camera_widget.toast.raise_()

    @pyqtSlot(dict)
    def _on_spheres_detected_2d(self, circles_2d: dict):
        """Actualiza el estado del overlay con nuevas detecciones."""
        if self.overlay.isVisible():
            self.overlay.update_detected_circles(circles_2d)

    @pyqtSlot(str)
    def _request_pick(self, color: str):
        """
        Publica la intencion de tomar una esfera en el bus global.

        El DataController escucha esta solicitud y orquesta la secuencia.
        """
        self.signal_manager.sphere_selected.emit(color)
        self.signal_manager.pick_requested.emit(color)

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
