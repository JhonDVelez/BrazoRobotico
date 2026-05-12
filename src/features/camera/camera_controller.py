from PyQt6.QtCore import pyqtSlot, pyqtSignal, QObject
from src.features.camera.camera_widget import CameraWidget
from src.features.camera.camera_worker import CameraWorker
from src.services.data.signals import ThemeSignalManager, DrawViewSignalManager, CameraSignalManager
from src.services.data import config_manager as cfg


class CameraController(QObject):
    status_changed = pyqtSignal(str)
    active_state_changed = pyqtSignal(bool)
    worker_created = pyqtSignal(object)

    def __init__(self, parent, is_calibration=False):
        super().__init__()
        self.parent = parent
        self.is_calibration = is_calibration
        self.camera_index = None
        self.worker = None

        self.camera_config = cfg.load("camera.json")
        init_view_config = self.camera_config.get("view", {})
        self.theme_manager = ThemeSignalManager.get_instance()
        self.draw_manager = DrawViewSignalManager.get_instance()
        self.camera_manager = CameraSignalManager.get_instance()

        self.view = CameraWidget(parent, init_view_config)
        self._setup_connections()

    def _setup_connections(self):
        self.view.video_toggled.connect(self.toggle_video)
        self.view.grid_toggled.connect(self.toggle_grid)
        self.view.geometry_toggled.connect(self.toggle_geometry)
        self.view.camera_changed.connect(self._on_camera_changed)

        self.theme_manager.theme_changed.connect(
            self.view.get_image_handler().update_theme)
        self.camera_manager.available_cameras.connect(
            self.view.set_available_cameras)

    def _on_camera_changed(self, index):
        camera_data = self.view.camera_selector.itemData(index)
        if camera_data:
            self.camera_index = camera_data[0]

    def toggle_grid(self):
        grid_enabled = not self.draw_manager.get_state()[0]
        self.draw_manager.set_charuco(grid_enabled)
        self.view.grid_button.setIcon(
            self.view.hide_grid_icon if grid_enabled else self.view.show_grid_icon)

    def toggle_geometry(self):
        ellipse_enabled = not self.draw_manager.get_state()[1]
        self.draw_manager.set_ellipse(ellipse_enabled)
        self.view.geometry_button.setIcon(
            self.view.hide_ellipse_icon if ellipse_enabled else self.view.show_ellipse_icon)

    def toggle_video(self):
        if self.worker and self.worker.isRunning():
            self.stop_video()
        else:
            self.start_video()

    def start_video(self):
        if self.worker is not None:
            self.stop_video()

        if self.camera_index is None:
            self.view.toast.show_message(
                "No hay ninguna cámara seleccionada", 4000)
            self._set_camera_connection_status("Cámara no conectada")
            return

        try:
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
        if self.worker:
            self.worker.pause()

    def resume_video(self):
        if self.worker:
            self.worker.resume()

    def show_controls(self):
        self.view.buttons_widget.show()
        self.view.buttons_widget.raise_()

    def _on_video_error(self, message):
        print(f"Error de video: {message}")
        self.stop_video()

    def _set_camera_connection_status(self, text: str):
        if hasattr(self.parent, 'camera_connected_label'):
            self.parent.camera_connected_label.setText(text)

    def get_widget(self):
        return self.view

    def get_worker(self):
        """ Retorna la instancia del worker actual """
        return self.worker
