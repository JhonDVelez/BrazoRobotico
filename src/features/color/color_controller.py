"""
Modulo que orquesta el proceso de calibracion de colores HSV.

Este modulo define el ColorController, el cual gestiona la interaccion entre
el flujo de video (CameraController), la logica de filtrado (ColorWorker)
y los controles deslizantes de la interfaz (ColorWidget).

Conexiones:
    - Escucha cambios en los sliders de `ColorWidget` para actualizar el worker.
    - Sincroniza el estado de la camara con la visualizacion de mascaras.
    - Carga y guarda perfiles de color (e.g., 'rojo', 'verde') en `camera.json`.
"""

import numpy as np
from PyQt6.QtCore import QObject, pyqtSlot
from src.features.camera import CameraController
from src.features.color.color_worker import ColorWorker
from src.features.color.color_widget import ColorWidget
from src.services.data.signals import ConfigSignalManager


class ColorController(QObject):
    """
    Orquestador del feature de calibracion de color.

    Maneja la intercepcion del feed de camara y la actualizacion de las vistas
    de mascara y resultado, permitiendo al usuario ajustar los umbrales de
    deteccion de forma interactiva.
    """

    def __init__(self, parent):
        """
        Inicializa el controlador de color y sus sub-componentes.

        Args:
            parent (QWidget): Widget padre para la gestion de UI.
        """
        super().__init__()
        self._parent = parent

        # 1. Componentes de UI y Logica
        self._widget = ColorWidget(parent)
        self._logic_worker = ColorWorker()

        # 2. Controlador de Cámara (modo calibración para interceptar feed)
        self._camera_controller = CameraController(self._widget, is_calibration=True)
        self._widget.get_camera_layout().addWidget(self._camera_controller.get_widget())

        # 3. Cargar configuración inicial desde disco
        self._load_config()

        # 4. Configurar conexiones reactivas
        self.__setup_connections()

    def _load_config(self):
        """
        Carga los valores HSV iniciales desde el archivo de configuracion camera.json.
        """
        config_manager = ConfigSignalManager.get_instance()
        hsv_config = config_manager.get_param("camera.json", "hsv_colors", default={})
        if hsv_config:
            # Usar el primer color disponible como default para inicializar sliders
            color = self._widget.get_selected_color()
            if color in hsv_config:
                values = hsv_config[color]
                # Mapeo: [h_min, s_min, v_min, h_max, s_max, v_max]
                order = ["h_min", "s_min", "v_min", "h_max", "s_max", "v_max"]
                ranges = {key: values[i] for i, key in enumerate(order)}
                self._widget.set_hsv_values(ranges)
                self._logic_worker.set_hsv_ranges(ranges)

    def __setup_connections(self):
        """
        Establece el flujo de datos entre los hilos de procesamiento y la interfaz.
        """
        # Feed Cámara -> Lógica (Conectar señales cuando se cree el worker)
        self._camera_controller.worker_created.connect(self._on_camera_worker_created)

        # Sincronización de estado de encendido/apagado de cámara
        self._camera_controller.active_state_changed.connect(self._on_camera_active_state_changed)

        # Lógica -> UI (Actualizacion de frames procesados)
        self._logic_worker.processing_finished.connect(self._on_processing_finished)

        # UI -> Lógica/Controlador (Acciones del usuario)
        self._widget.camera_toggled.connect(self._on_camera_toggle)
        self._widget.hsv_changed.connect(self._logic_worker.set_hsv_ranges)
        self._widget.save_clicked.connect(self._save_config)
        self._widget.color_selector.currentTextChanged.connect(self._on_color_selection_changed)

    def _on_camera_active_state_changed(self, active):
        """
        Sincroniza el boton del panel con el estado real de la camara.

        Args:
            active (bool): True si la camara esta capturando video.
        """
        self._widget.camera_button.blockSignals(True)
        self._widget.camera_button.setChecked(active)
        self._widget.camera_button.setText("Cámara ON" if active else "Cámara OFF")
        self._widget.camera_button.blockSignals(False)

        # Sincronizar estado de procesamiento en el widget (placeholders vs video)
        self._widget.set_process_running(active)

        if not active:
            self._widget.clear_views()

    def _on_camera_worker_created(self, worker):
        """
        Vincula el nuevo worker de camara con el procesador de color.

        Args:
            worker (CameraWorker): Instancia del worker recien creado.
        """
        if worker:
            worker.frame_ready.connect(self._logic_worker.process_frame)

    def _on_camera_toggle(self, checked):
        """
        Inicia o detiene el flujo de video al presionar el boton.

        Args:
            checked (bool): Estado del boton (Start/Stop).
        """
        if checked:
            self._camera_controller.start_video()
        else:
            self._camera_controller.stop_video()
            self._widget.clear_views()

    @pyqtSlot(np.ndarray, np.ndarray, np.ndarray)
    def _on_processing_finished(self, original, mask, result):
        """
        Actualiza la vista original y las procesadas con los nuevos datos.

        Args:
            original (np.ndarray): Frame sin filtrar.
            mask (np.ndarray): Mascara binaria generada.
            result (np.ndarray): Imagen filtrada final.
        """
        self._camera_controller.get_widget().update_frame(original)
        self._widget.update_views(mask, result)

    def _on_color_selection_changed(self, color):
        """
        Actualiza los sliders cuando el usuario elige un color diferente en el combo.

        Args:
            color (str): Nombre del color seleccionado (e.g. 'azul').
        """
        config_manager = ConfigSignalManager.get_instance()
        hsv_config = config_manager.get_param("camera.json", "hsv_colors", default={})
        if color in hsv_config:
            values = hsv_config[color]
            order = ["h_min", "s_min", "v_min", "h_max", "s_max", "v_max"]
            ranges = {key: values[i] for i, key in enumerate(order)}
            self._widget.set_hsv_values(ranges)
            self._logic_worker.set_hsv_ranges(ranges)

    def _save_config(self):
        """
        Persiste los rangos HSV actuales en el archivo settings/camera.json.
        """
        color = self._widget.get_selected_color()
        ranges = self._widget.get_hsv_values()
        order = ["h_min", "s_min", "v_min", "h_max", "s_max", "v_max"]
        values = [ranges[key] for key in order]

        ConfigSignalManager.get_instance().request_change("camera.json", "hsv_colors", color, value=values)
        print(f"Configuración guardada para {color}: {values}")

    def cleanup(self):
        """
        Detiene los servicios de video y limpia recursos.
        """
        self._camera_controller.stop_video()

    # Getters explicitos
    def get_widget(self):
        """
        Retorna el widget de interfaz de calibracion de color.

        Returns:
            ColorWidget: Instancia del widget.
        """
        return self._widget
