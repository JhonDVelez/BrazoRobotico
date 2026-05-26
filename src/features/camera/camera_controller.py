"""
Modulo que controla el flujo de trabajo de la camara y su interaccion con la UI.

Este modulo define la clase CameraController, la cual gestiona la inicializacion
del video, el cambio de camaras disponibles, y el control de visibilidad de
capas de vision (grid y geometria).

Conexiones:
    - Escucha eventos de `CameraWidget` (toggle video, grid, etc.).
    - Gestiona el ciclo de vida del `CameraWorker`.
    - Sincroniza estados de dibujo con `DrawViewSignalManager`.
    - Actualiza el estado de conexion en el componente padre.
"""

from PyQt6.QtCore import pyqtSlot, pyqtSignal, QObject
from src.features.camera.camera_widget import CameraWidget
from src.features.camera.camera_worker import CameraWorker
from src.services.data.signals import ThemeSignalManager, DrawViewSignalManager, CameraSignalManager, ConfigSignalManager


class CameraController(QObject):
    """
    Controlador central para el modulo de camara.

    Administra la logica de negocio relacionada con la captura de video,
    la seleccion de dispositivos y el dibujo de overlays en la interfaz.

    Attributes:
        status_changed (pyqtSignal): Emite el nombre de la camara o estado (str).
        active_state_changed (pyqtSignal): Emite True si la camara esta encendida.
        worker_created (pyqtSignal): Emite la instancia del nuevo CameraWorker.
    """
    status_changed = pyqtSignal(str)
    active_state_changed = pyqtSignal(bool)
    worker_created = pyqtSignal(object)

    def __init__(self, parent, is_calibration=False):
        """
        Inicializa el controlador de camara.

        Args:
            parent (QWidget): Widget padre para UI y estados.
            is_calibration (bool): Indica si se debe operar en modo calibracion.
        """
        super().__init__()
        self.parent = parent
        self.is_calibration = is_calibration
        self.camera_index = None
        self.worker = None

        self.config_manager = ConfigSignalManager.get_instance()
        self.camera_config = self.config_manager.get_param("camera.json", default={})
        init_view_config = self.camera_config.get("view", {})
        self.theme_manager = ThemeSignalManager.get_instance()
        self.draw_manager = DrawViewSignalManager.get_instance()
        self.camera_manager = CameraSignalManager.get_instance()

        self.view = CameraWidget(parent, init_view_config)
        self._setup_connections()

    def _setup_connections(self):
        """
        Configura las conexiones reactivas entre la vista y el controlador.
        """
        self.view.video_toggled.connect(self.toggle_video)
        self.view.grid_toggled.connect(self.toggle_grid)
        self.view.geometry_toggled.connect(self.toggle_geometry)
        self.view.camera_changed.connect(self._on_camera_changed)

        self.theme_manager.theme_changed.connect(
            self.view.get_image_handler().update_theme)
        self.camera_manager.available_cameras.connect(
            self.view.set_available_cameras)

    def _on_camera_changed(self, index):
        """
        Actualiza el indice de camara seleccionado desde el widget.

        Args:
            index (int): Indice de la seleccion en el QComboBox.
        """
        camera_data = self.view.camera_selector.itemData(index)
        if camera_data:
            self.camera_index = camera_data[0]

    def toggle_grid(self):
        """
        Alterna la visibilidad de la cuadricula (grid) de calibracion.
        """
        grid_enabled = not self.draw_manager.get_state()[0]
        self.draw_manager.set_charuco(grid_enabled)
        self.view.grid_button.setIcon(
            self.view.hide_grid_icon if grid_enabled else self.view.show_grid_icon)

    def toggle_geometry(self):
        """
        Alterna la visibilidad de las geometrias (esferas) detectadas.
        """
        circle_enabled = not self.draw_manager.get_state()[1]
        self.draw_manager.set_circle(circle_enabled)
        self.view.geometry_button.setIcon(
            self.view.hide_circle_icon if circle_enabled else self.view.show_circle_icon)

    def toggle_video(self):
        """
        Invierte el estado de ejecucion del video (Start/Stop).
        """
        if self.worker and self.worker.isRunning():
            self.stop_video()
        else:
            self.start_video()

    def start_video(self):
        """
        Inicia el flujo de video creando un nuevo CameraWorker.

        Valida la seleccion de camara y conecta señales de frame y error.
        """
        if self.worker is not None:
            self.stop_video()

        if self.camera_index is None:
            self.view.toast.show_message(
                "No hay ninguna cámara seleccionada", 4000)
            self._set_camera_connection_status("Cámara no conectada")
            return

        try:
            self.camera_config = self.config_manager.get_param("camera.json", default={})
            self.worker = CameraWorker(camera_index=self.camera_index,
                                       camera_config=self.camera_config,
                                       is_calibration=self.is_calibration)

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

        except Exception as e:
            print(f"Error al iniciar video: {e}")
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
            except Exception:
                pass

            try:
                self.worker.error_occurred.disconnect()
            except Exception:
                pass

            self.worker.stop()
            self.worker.deleteLater()
            self.worker = None

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
        Maneja errores criticos durante la captura de video.

        Args:
            message (str): Descripcion del error.
        """
        print(f"Error de video: {message}")
        self.stop_video()

    def _set_camera_connection_status(self, text: str):
        """
        Actualiza el label de estado de la camara en el widget padre.

        Args:
            text (str): Texto a mostrar (e.g. 'Cámara conectada').
        """
        if hasattr(self.parent, 'camera_connected_label'):
            self.parent.camera_connected_label.setText(text)

    def get_widget(self):
        """
        Retorna el widget de interfaz de la camara.

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
