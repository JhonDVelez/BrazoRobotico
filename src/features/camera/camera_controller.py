"""
Módulo que controla el flujo de trabajo de la cámara y su interacción con la UI.

Este módulo define la clase CameraController, la cual gestiona la inicialización
del video, el cambio de cámaras disponibles, y el control de visibilidad de
capas de visión (grid y geometría).

Conexiones:
    - Escucha eventos de `CameraWidget` (toggle video, grid, etc.).
    - Gestiona el ciclo de vida del `CameraWorker`.
    - Sincroniza estados de dibujo con `DrawViewSignalManager`.
    - Envía datos de posición de las esferas al sistema de pick and place
    - Actualiza el estado de conexión en el componente padre.
"""

from PyQt6.QtCore import pyqtSlot, pyqtSignal, QObject
from src.features.camera.camera_widget import CameraWidget
from src.features.camera.camera_worker import CameraWorker
from src.services.data.signals import (
    ThemeSignalManager, DrawViewSignalManager,
    CameraSignalManager, ConfigSignalManager,
    SearchSignalManager
)
from src.services.ui.notification_manager import NotificationManager
from src.services.data.enums.types import NotificationType


class CameraController(QObject):
    """
    Controlador central para el modulo de cámara.

    Administra la lógica de negocio relacionada con la captura de video,
    la selección de dispositivos y el dibujo de overlays en la interfaz.

    Attributes:
        status_changed (pyqtSignal): Emite el nombre de la cámara o estado (str).
        active_state_changed (pyqtSignal): Emite True si la cámara esta encendida.
        worker_created (pyqtSignal): Emite la instancia del nuevo CameraWorker.
    """
    status_changed = pyqtSignal(str)
    active_state_changed = pyqtSignal(bool)
    worker_created = pyqtSignal(object)

    def __init__(self, parent, is_calibration=False) -> None:
        """
        Inicializa el controlador de cámara.

        Args:
            parent (QWidget): Widget padre para UI y estados.
            is_calibration (bool): Indica si se debe operar en modo calibración.
        """
        super().__init__()
        self.parent = parent
        self.is_calibration = is_calibration
        self.camera_index = None
        self.worker = None

        self.config_manager = ConfigSignalManager.get_instance()
        self.camera_config: dict = self.config_manager.get_param(
            "camera.json", default={})
        init_view_config = self.config_manager.get_param(
            "settings.json", "camera", "view", default={})
        self.theme_signal_manager = ThemeSignalManager.get_instance()
        self.draw_signal_manager = DrawViewSignalManager.get_instance()
        self.camera_signal_manager = CameraSignalManager.get_instance()
        self.search_signal_manager = SearchSignalManager.get_instance()

        self.view = CameraWidget(parent, self.camera_config, init_view_config)
        self._setup_connections()

        self.noti_manager = NotificationManager.get_instance()

    def _setup_connections(self):
        """
        Configura las conexiones reactivas entre la vista y el controlador.
        """
        self.view.video_toggled.connect(self.toggle_video)
        self.view.grid_toggled.connect(self.toggle_grid)
        self.view.geometry_toggled.connect(self.toggle_geometry)
        self.view.camera_changed.connect(self._on_camera_changed)

        self.theme_signal_manager.theme_changed.connect(
            self.view.get_image_handler().update_theme)
        self.camera_signal_manager.available_cameras.connect(
            self.view.set_available_cameras)

        # Puente estado global -> worker activo (búsqueda, overlays y radio de
        # esfera). Conectado una sola vez; los slots verifican que exista worker.
        self.search_signal_manager.charuco_search_changed.connect(
            self._on_search_state_changed)
        self.search_signal_manager.circle_search_changed.connect(
            self._on_search_state_changed)
        self.config_manager.config_updated.connect(
            self._on_config_updated)

    def _on_camera_changed(self, index):
        """
        Actualiza el índice de cámara seleccionado desde el widget.

        Args:
            index (int): Índice de la selección en el QComboBox.
        """
        camera_data = self.view.camera_selector.itemData(index)
        if camera_data:
            self.camera_index = camera_data[0]

    def toggle_grid(self):
        """
        Alterna la visibilidad de la cuadrícula (grid) de calibración.
        """
        grid_enabled = not self.draw_signal_manager.get_state()[0]
        self.draw_signal_manager.set_charuco(grid_enabled)
        self.view.grid_button.setIcon(
            self.view.hide_grid_icon if grid_enabled else self.view.show_grid_icon)
        self._push_view_state()

    def toggle_geometry(self):
        """
        Alterna la visibilidad de las geometrías (esferas) detectadas.
        """
        circle_enabled = not self.draw_signal_manager.get_state()[1]
        self.draw_signal_manager.set_circle(circle_enabled)
        self.view.geometry_button.setIcon(
            self.view.hide_circle_icon if circle_enabled else self.view.show_circle_icon)
        self._push_view_state()

    def _push_view_state(self):
        """
        Empuja el estado de overlays al worker activo (si existe).
        """
        if self.worker is not None:
            charuco, circle = self.draw_signal_manager.get_state()
            self.worker.set_view_state(charuco, circle)

    @pyqtSlot(bool)
    def _on_search_state_changed(self, _checked: bool):
        """
        Reenvía el estado de búsqueda actual al worker activo.

        Args:
            _checked (bool): Valor emitido por la señal (no usado; se relee el estado completo).
        """
        if self.worker is not None:
            charuco, circle = self.search_signal_manager.get_state()
            self.worker.set_search_state(charuco, circle)

    @pyqtSlot(str, list, object)
    def _on_config_updated(self, filename: str, keys: list, value: object):
        """
        Reenvía al worker el cambio de radio de esfera desde la configuración.

        Args:
            filename (str): Archivo de configuración modificado.
            keys (list): Llaves anidadas del parametro.
            value (object): Nuevo valor.
        """
        if self.worker is not None and filename == "camera.json" and "sphere_radius" in keys:
            self.worker.set_sphere_radius(float(value))

    def toggle_video(self):
        """
        Invierte el estado de ejecución del video (Start/Stop).
        """
        if self.worker and self.worker.isRunning():
            self.stop_video()
        else:
            self.start_video()

    def start_video(self):
        """
        Inicia el flujo de video creando un nuevo CameraWorker.

        Valida la selección de cámara y conecta señales de frame y error.
        """
        if self.worker is not None:
            self.stop_video()

        if self.camera_index is None:
            self.view.toast.show_message(
                "No hay ninguna cámara seleccionada", 4000)
            self._set_camera_connection_status("Cámara no conectada")
            return

        try:
            self.camera_config = self.config_manager.get_param(
                "camera.json", default={})
            self.worker = CameraWorker(camera_index=self.camera_index,
                                       camera_config=self.camera_config,
                                       is_calibration=self.is_calibration,
                                       search_state=self.search_signal_manager.get_state(),
                                       view_state=self.draw_signal_manager.get_state())
            self.worker.sphere_ready.connect(self.on_sphere_ready)

            # Puente worker -> bus global (el controlador es el único que toca el bus).
            self.worker.charuco_detected.connect(
                self.camera_signal_manager.charuco_done.emit)

            # Solo conectar feed directo si no es modo calibración
            if not self.is_calibration:
                self.worker.frame_ready.connect(self.view.update_frame)

            self.worker.error_occurred.connect(self._on_video_error)

            # Notificar que se ha creado un nuevo worker
            self.worker_created.emit(self.worker)

            self.worker.start()
            self.view.get_image_handler().set_process_running(True)
            self.view.set_ui_running_state(True)

            camera_name = self.view.camera_selector.currentText()
            self._set_camera_connection_status(
                camera_name or "Cámara conectada")
            self.status_changed.emit(camera_name or "Cámara conectada")
            self.active_state_changed.emit(True)

        except (OSError, RuntimeError, ValueError) as e:
            print(f"[DEBUG] Error al iniciar video ({type(e).__name__}): {e}")
            self.noti_manager.notify(
                f"Error al iniciar video: {e}", NotificationType.DIALOG_ERROR, self.view)
            self._on_video_error(str(e))

    def stop_video(self):
        """
        Detiene el flujo de video y libera el worker de forma segura.

        Restaura la imagen estatica de placeholder en la vista.
        """
        if self.worker is not None:
            try:
                # Desconectar todas las conexiones de las señales (seguro y limpio)
                self.worker.frame_ready.disconnect()
                self.worker.sphere_ready.disconnect()
            except RuntimeError:
                # Señal ya desconectada o worker destruido — esperado en algunos flujos
                pass

            try:
                self.worker.error_occurred.disconnect()
            except RuntimeError:
                # Señal ya desconectada — esperado en algunos flujos
                pass

            self.worker.stop()
            self.worker.deleteLater()
            self.worker = None
            self.camera_signal_manager.clear_spheres_request.emit()

        self.view.get_image_handler().set_process_running(False)
        self.view.set_ui_running_state(False)
        self.view.get_image_handler().set_static_image()

        self._set_camera_connection_status("Cámara no conectada")
        self.status_changed.emit("Cámara no conectada")
        self.active_state_changed.emit(False)

    def pause_video(self):
        """
        Pausa temporalmente el procesamiento de frames en el worker.
        """
        if self.worker:
            self.worker.pause()

    def resume_video(self):
        """
        Reanuda el procesamiento de frames en el worker.
        """
        if self.worker:
            self.worker.resume()

    def show_controls(self):
        """
        Asegura que el panel de botones de control sea visible y este al frente.
        """
        self.view.buttons_widget.show()
        self.view.buttons_widget.raise_()

    def _on_video_error(self, message):
        """
        Maneja errores críticos durante la captura de video.

        Args:
            message (str): Descripción del error.
        """
        self.noti_manager.notify(
            f"Error de video: {message}", NotificationType.TOAST_ERROR)
        self.stop_video()

    def _set_camera_connection_status(self, text: str):
        """
        Actualiza el label de estado de la cámara en el widget padre.

        Args:
            text (str): Texto a mostrar (e.g. 'Cámara conectada').
        """
        if hasattr(self.parent, 'camera_connected_label'):
            self.parent.camera_connected_label.setText(text)

    def get_widget(self):
        """
        Retorna el widget de interfaz de la cámara.

        Returns:
            CameraWidget: Instancia del widget visual.
        """
        return self.view

    def get_worker(self):
        """
        Retorna la instancia del worker de captura actual.

        Returns:
            CameraWorker: Instancia del hilo de procesamiento.
        """
        return self.worker

    @pyqtSlot(dict)
    def on_sphere_ready(self, circles: dict):
        poses = {}
        for color, data in circles.items():
            # .pop() elimina 'position' de 'spheres' y retorna su valor
            if 'position' in data:
                poses[color] = {
                    'position': data.pop('position')}

        # Notificar detecciones 2D al bus propio de la camara.
        # El DataController las re-publica hacia pick and place y simulación.
        self.camera_signal_manager.spheres_detected_2d.emit(circles)
        self.camera_signal_manager.poses_from_camera.emit(poses)
