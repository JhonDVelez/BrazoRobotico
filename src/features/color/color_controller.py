import numpy as np
from PyQt6.QtCore import QObject, pyqtSlot
from src.features.camera import CameraController
from src.features.color.color_worker import ColorWorker
from src.features.color.color_widget import ColorWidget
from src.services.data import config_manager as cfg

class ColorController(QObject):
    """
    Orquestador del feature de calibración de color.
    Maneja la intercepción del feed de cámara y la actualización de vistas HSV.
    """
    def __init__(self, parent):
        super().__init__()
        self._parent = parent
        
        # 1. Componentes
        self._widget = ColorWidget(parent)
        self._logic_worker = ColorWorker()
        
        # 2. Controlador de Cámara (modo calibración para interceptar feed)
        self._camera_controller = CameraController(self._widget, is_calibration=True)
        self._widget.get_camera_layout().addWidget(self._camera_controller.get_widget())
        
        # 3. Cargar configuración inicial
        self._load_config()
        
        # 4. Conexiones
        self.__setup_connections()

    def _load_config(self):
        """ Carga los valores HSV iniciales desde camera.json """
        hsv_config = cfg.get("camera.json", "hsv_colors", default={})
        if hsv_config:
            # Usar el primer color disponible como default
            color = self._widget.get_selected_color()
            if color in hsv_config:
                values = hsv_config[color]
                # Mapeo: [h_min, s_min, v_min, h_max, s_max, v_max]
                order = ["h_min", "s_min", "v_min", "h_max", "s_max", "v_max"]
                ranges = {key: values[i] for i, key in enumerate(order)}
                self._widget.set_hsv_values(ranges)
                self._logic_worker.set_hsv_ranges(ranges)

    def __setup_connections(self):
        # Feed Cámara -> Lógica
        self._camera_controller.worker_created.connect(self._on_camera_worker_created)
        
        # Sincronización de estado de cámara
        self._camera_controller.active_state_changed.connect(self._on_camera_active_state_changed)
        
        # Lógica -> UI
        self._logic_worker.processing_finished.connect(self._on_processing_finished)
        
        # UI -> Lógica/Controlador
        self._widget.camera_toggled.connect(self._on_camera_toggle)
        self._widget.hsv_changed.connect(self._logic_worker.set_hsv_ranges)
        self._widget.save_clicked.connect(self._save_config)
        self._widget.color_selector.currentTextChanged.connect(self._on_color_selection_changed)

    def _on_camera_active_state_changed(self, active):
        """ Sincroniza el botón del panel con el estado real de la cámara """
        self._widget.camera_button.blockSignals(True)
        self._widget.camera_button.setChecked(active)
        self._widget.camera_button.setText("Cámara ON" if active else "Cámara OFF")
        self._widget.camera_button.blockSignals(False)
        
        # Sincronizar estado de procesamiento en el widget
        self._widget.set_process_running(active)
        
        if not active:
            self._widget.clear_views()

    def _on_camera_worker_created(self, worker):
        if worker:
            worker.frame_ready.connect(self._logic_worker.process_frame)

    def _on_camera_toggle(self, checked):
        if checked:
            self._camera_controller.start_video()
        else:
            self._camera_controller.stop_video()
            self._widget.clear_views()

    @pyqtSlot(np.ndarray, np.ndarray, np.ndarray)
    def _on_processing_finished(self, original, mask, result):
        """ Actualiza la vista original (limpia) y las procesadas """
        # print("[ColorController] Received processed frames")
        self._camera_controller.get_widget().update_frame(original)
        self._widget.update_views(mask, result)

    def _on_color_selection_changed(self, color):
        """ Recarga los sliders al cambiar de color si existe configuración """
        hsv_config = cfg.get("camera.json", "hsv_colors", default={})
        if color in hsv_config:
            values = hsv_config[color]
            order = ["h_min", "s_min", "v_min", "h_max", "s_max", "v_max"]
            ranges = {key: values[i] for i, key in enumerate(order)}
            self._widget.set_hsv_values(ranges)
            self._logic_worker.set_hsv_ranges(ranges)

    def _save_config(self):
        """ Guarda los valores actuales en camera.json """
        color = self._widget.get_selected_color()
        ranges = self._widget.get_hsv_values()
        order = ["h_min", "s_min", "v_min", "h_max", "s_max", "v_max"]
        values = [ranges[key] for key in order]
        
        cfg.set_value("camera.json", "hsv_colors", color, value=values)
        print(f"Configuración guardada para {color}: {values}")

    def cleanup(self):
        self._camera_controller.stop_video()

    # Getters explícitos
    def get_widget(self):
        return self._widget
