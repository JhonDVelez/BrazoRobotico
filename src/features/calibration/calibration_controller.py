"""
Módulo que orquesta el flujo de trabajo para la calibración de cámaras.

Este módulo define el CalibrationController, el cual actúa como mediador entre
el flujo de video (CameraController), el procesamiento matemático (CalibrationWorker)
y la interfaz de usuario (CalibrationWidget).

Conexiones:
    - Escucha la creación de workers de cámara para redirigir el feed al worker de calibración.
    - Actualiza el widget de cámara con overlays de detección.
    - Persiste los resultados de la calibración (matriz y distortion) mediante `config_manager`.
"""

import numpy as np
from PyQt6.QtCore import QObject, pyqtSlot
from PyQt6.QtWidgets import QMessageBox
from src.features.camera import CameraController
from src.features.calibration.calibration_worker import CalibrationWorker
from src.features.calibration.calibration_widget import CalibrationWidget
from src.features.camera.camera_worker import CameraWorker
from src.services.ui.calibration_result_dialog import CalibrationResultDialog
from src.services.data.signals import ConfigSignalManager


class CalibrationController(QObject):
    """
    Orquestador del feature de calibración.

    Conecta la cámara con el worker de lógica y el widget de interfaz, gestionando
    el ciclo de vida del proceso de calibración ChArUco.
    """

    def __init__(self, parent) -> None:
        """
        Inicializa el controlador de calibración y sus componentes.

        Args:
            parent (QWidget): Widget padre para la gestión de memoria y UI.
        """
        super().__init__()
        self._parent = parent

        # 1. Instanciar componentes
        self._widget = CalibrationWidget(parent)
        self._logic_worker = CalibrationWorker()

        # 2. Instanciar controlador de cámara en modo calibración
        self._camera_controller = CameraController(
            self._widget, is_calibration=True)

        # 3. Integrar cámara en el widget de calibración
        self._widget.get_camera_layout().addWidget(
            self._camera_controller.get_widget())

        # 4. Configurar conexiones
        self.__setup_connections()

    def __setup_connections(self) -> None:
        """
        Establece el flujo de datos reactivo entre cámara, lógica y UI.
        """
        # Feed de cámara -> Escuchar creación de nuevos workers
        self._camera_controller.worker_created.connect(
            self._on_camera_worker_created)

        # Lógica -> UI (Actualizar el frame con overlays de calibración)
        self._logic_worker.frame_processed.connect(self._on_frame_processed)

        # UI -> Lógica (Acciones de botones)
        self._widget.capture_clicked.connect(self._request_capture)
        self._widget.calibrate_clicked.connect(
            self._logic_worker.run_calibration)

        # Lógica -> Resultados
        self._logic_worker.calibration_success.connect(
            self._on_calibration_success)
        self._logic_worker.error_occurred.connect(self._on_error)

    def _on_camera_worker_created(self, worker: CameraWorker) -> None:
        """
        Conecta el nuevo worker de cámara con el procesamiento de calibración.

        Args:
            worker (CameraWorker): Instancia del worker de cámara recién creado.
        """
        if worker:
            worker.frame_ready.connect(self._logic_worker.process_frame)

    @pyqtSlot(np.ndarray, int, str, object)
    def _on_frame_processed(self, frame, n_corners, text, color) -> None:
        """
        Actualiza la vista de cámara con el frame procesado por el worker de calibración.

        Args:
            frame (np.ndarray): Frame con overlays de corners detectados.
            n_corners (int): Numero de corners detectados.
            text (str): Texto de estado a mostrar.
            color (object): Color del texto de estado.
        """
        self._camera_controller.get_widget().update_frame(frame)

    def _request_capture(self) -> None:
        """
        Gestiona la petición de captura de un frame para el set de calibración.

        Muestra un mensaje de advertencia si no se detectan corners suficientes.
        """
        success = self._logic_worker.set_should_capture(True)
        if not success:
            QMessageBox.warning(self._widget, "Error de Captura",
                                "No se detectan suficientes corners. Posiciona el tablero correctamente.")

    @pyqtSlot(np.ndarray, np.ndarray, float)
    def _on_calibration_success(self, matrix: np.ndarray, dist: np.ndarray, error) -> None:
        """
        Maneja el éxito de la calibración, guardando datos y mostrando resultados.

        Args:
            matrix (np.ndarray): Matriz intrínseca calculada (3x3).
            dist (np.ndarray): Coeficientes de distorsión calculados.
            error (float): Error de reproducción final.
        """
        # Guardar en configuración
        config_manager = ConfigSignalManager.get_instance()
        config_manager.request_change(
            "camera.json", ["matrix"], matrix.tolist())
        config_manager.request_change(
            "camera.json", ["distortion coefficients"], dist.tolist())

        # Mostrar diálogo de resultados
        dialog = CalibrationResultDialog(self._widget, matrix, dist, error)
        dialog.exec()

    @pyqtSlot(str)
    def _on_error(self, message) -> None:
        """
        Maneja errores emitidos por el worker de calibración.

        Args:
            message (str): Mensaje de error detallado.
        """
        QMessageBox.critical(self._widget, "Error de Calibración", message)

    def cleanup(self) -> None:
        """
        Realiza la limpieza de recursos y detención de hilos al cerrar el módulo.
        """
        self._camera_controller.stop_video()
        self._logic_worker.reset_data()

    # Getters explícitos
    def get_widget(self) -> CalibrationWidget:
        """
        Obtiene el widget de interfaz de calibración.

        Returns:
            CalibrationWidget: Instancia del widget.
        """
        return self._widget

    def get_camera_controller(self) -> CameraController:
        """
        Obtiene el controlador de cámara interno.

        Returns:
            CameraController: Instancia del controlador de cámara.
        """
        return self._camera_controller
