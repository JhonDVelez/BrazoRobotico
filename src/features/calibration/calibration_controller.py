import numpy as np
from PyQt6.QtCore import QObject, pyqtSlot, pyqtSignal
from src.features.camera import CameraController
from src.features.calibration.calibration_worker import CalibrationWorker
from src.features.calibration.calibration_widget import CalibrationWidget
from src.services.ui.calibration_result_dialog import CalibrationResultDialog
from src.services.data import config_manager as cfg

class CalibrationController(QObject):
    """
    Orquestador del feature de calibración.
    Conecta la cámara con el worker de lógica y el widget de interfaz.
    """
    def __init__(self, parent):
        super().__init__()
        self._parent = parent
        
        # 1. Instanciar componentes
        self._widget = CalibrationWidget(parent)
        self._logic_worker = CalibrationWorker()
        
        # 2. Instanciar controlador de cámara en modo calibración
        self._camera_controller = CameraController(self._widget, is_calibration=True)
        
        # 3. Integrar cámara en el widget de calibración
        self._widget.get_camera_layout().addWidget(self._camera_controller.get_widget())
        
        # 4. Configurar conexiones
        self.__setup_connections()

    def __setup_connections(self):
        """
        Establece el flujo de datos entre cámara, lógica y UI.
        """
        # Feed de cámara -> Escuchar creación de nuevos workers
        self._camera_controller.worker_created.connect(self._on_camera_worker_created)

        # Lógica -> UI (Actualizar el frame con overlays de calibración)
        self._logic_worker.frame_processed.connect(self._on_frame_processed)
        
        # UI -> Lógica (Acciones de botones)
        self._widget.capture_clicked.connect(self._request_capture)
        self._widget.calibrate_clicked.connect(self._logic_worker.run_calibration)
        
        # Lógica -> Resultados
        self._logic_worker.calibration_success.connect(self._on_calibration_success)
        self._logic_worker.error_occurred.connect(self._on_error)

    def _on_camera_worker_created(self, worker):
        """ Conecta el nuevo worker de cámara con el procesamiento de calibración """
        if worker:
            worker.frame_ready.connect(self._logic_worker.process_frame)

    @pyqtSlot(np.ndarray, int, str, object)
    def _on_frame_processed(self, frame, n_corners, text, color):
        """ Actualiza la vista de cámara con el frame procesado por el worker de calibración """
        self._camera_controller.get_widget().update_frame(frame)

    def _request_capture(self):
        """ Gestiona la petición de captura de un frame """
        success = self._logic_worker.set_should_capture(True)
        if not success:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self._widget, "Error de Captura", 
                              "No se detectan suficientes corners. Posiciona el tablero correctamente.")

    @pyqtSlot(np.ndarray, np.ndarray, float)
    def _on_calibration_success(self, matrix, dist, error):
        """ Maneja el éxito de la calibración, guardando datos y mostrando el popup """
        # Guardar en configuración
        cfg.set_value("camera.json", "matrix", value=matrix.tolist())
        cfg.set_value("camera.json", "distortion coefficients", value=dist.tolist())
        
        # Mostrar diálogo de resultados
        dialog = CalibrationResultDialog(self._widget, matrix, dist, error)
        dialog.exec()

    @pyqtSlot(str)
    def _on_error(self, message):
        """ Maneja errores emitidos por el worker """
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(self._widget, "Error de Calibración", message)

    def cleanup(self):
        """ Limpieza de recursos al cerrar """
        self._camera_controller.stop_video()
        self._logic_worker.reset_data()

    # Getters explícitos
    def get_widget(self):
        return self._widget

    def get_camera_controller(self):
        return self._camera_controller
