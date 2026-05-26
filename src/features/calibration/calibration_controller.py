"""
Modulo que orquesta el flujo de trabajo para la calibracion de camaras.

Este modulo define el CalibrationController, el cual actua como mediador entre
el flujo de video (CameraController), el procesamiento matematico (CalibrationWorker)
y la interfaz de usuario (CalibrationWidget).

Conexiones:
    - Escucha la creacion de workers de camara para redirigir el feed al worker de calibracion.
    - Actualiza el widget de camara con overlays de deteccion.
    - Persiste los resultados de la calibracion (matriz y distorsion) mediante `config_manager`.
"""

import numpy as np
from PyQt6.QtCore import QObject, pyqtSlot
from src.features.camera import CameraController
from src.features.calibration.calibration_worker import CalibrationWorker
from src.features.calibration.calibration_widget import CalibrationWidget
from src.services.ui.calibration_result_dialog import CalibrationResultDialog
from src.services.data.signals import ConfigSignalManager


class CalibrationController(QObject):
    """
    Orquestador del feature de calibracion.

    Conecta la camara con el worker de logica y el widget de interfaz, gestionando
    el ciclo de vida del proceso de calibracion ChArUco.
    """

    def __init__(self, parent):
        """
        Inicializa el controlador de calibracion y sus componentes.

        Args:
            parent (QWidget): Widget padre para la gestion de memoria y UI.
        """
        super().__init__()
        self._parent = parent

        # 1. Instanciar componentes
        self._widget = CalibrationWidget(parent)
        self._logic_worker = CalibrationWorker()

        # 2. Instanciar controlador de camara en modo calibracion
        self._camera_controller = CameraController(self._widget, is_calibration=True)

        # 3. Integrar camara en el widget de calibracion
        self._widget.get_camera_layout().addWidget(self._camera_controller.get_widget())

        # 4. Configurar conexiones
        self.__setup_connections()

    def __setup_connections(self):
        """
        Establece el flujo de datos reactivo entre camara, logica y UI.
        """
        # Feed de camara -> Escuchar creacion de nuevos workers
        self._camera_controller.worker_created.connect(self._on_camera_worker_created)

        # Logica -> UI (Actualizar el frame con overlays de calibracion)
        self._logic_worker.frame_processed.connect(self._on_frame_processed)

        # UI -> Logica (Acciones de botones)
        self._widget.capture_clicked.connect(self._request_capture)
        self._widget.calibrate_clicked.connect(self._logic_worker.run_calibration)

        # Logica -> Resultados
        self._logic_worker.calibration_success.connect(self._on_calibration_success)
        self._logic_worker.error_occurred.connect(self._on_error)

    def _on_camera_worker_created(self, worker):
        """
        Conecta el nuevo worker de camara con el procesamiento de calibracion.

        Args:
            worker (CameraWorker): Instancia del worker de camara recien creado.
        """
        if worker:
            worker.frame_ready.connect(self._logic_worker.process_frame)

    @pyqtSlot(np.ndarray, int, str, object)
    def _on_frame_processed(self, frame, n_corners, text, color):
        """
        Actualiza la vista de camara con el frame procesado por el worker de calibracion.

        Args:
            frame (np.ndarray): Frame con overlays de corners detectados.
            n_corners (int): Numero de corners detectados.
            text (str): Texto de estado a mostrar.
            color (object): Color del texto de estado.
        """
        self._camera_controller.get_widget().update_frame(frame)

    def _request_capture(self):
        """
        Gestiona la peticion de captura de un frame para el set de calibracion.

        Muestra un mensaje de advertencia si no se detectan corners suficientes.
        """
        success = self._logic_worker.set_should_capture(True)
        if not success:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self._widget, "Error de Captura",
                              "No se detectan suficientes corners. Posiciona el tablero correctamente.")

    @pyqtSlot(np.ndarray, np.ndarray, float)
    def _on_calibration_success(self, matrix, dist, error):
        """
        Maneja el exito de la calibracion, guardando datos y mostrando resultados.

        Args:
            matrix (np.ndarray): Matriz intrinseca calculada (3x3).
            dist (np.ndarray): Coeficientes de distorsion calculados.
            error (float): Error de reproyeccion final.
        """
        # Guardar en configuracion
        config_manager = ConfigSignalManager.get_instance()
        config_manager.request_change("camera.json", "matrix", value=matrix.tolist())
        config_manager.request_change("camera.json", "distortion coefficients", value=dist.tolist())

        # Mostrar dialogo de resultados
        dialog = CalibrationResultDialog(self._widget, matrix, dist, error)
        dialog.exec()

    @pyqtSlot(str)
    def _on_error(self, message):
        """
        Maneja errores emitidos por el worker de calibracion.

        Args:
            message (str): Mensaje de error detallado.
        """
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(self._widget, "Error de Calibración", message)

    def cleanup(self):
        """
        Realiza la limpieza de recursos y detencion de hilos al cerrar el modulo.
        """
        self._camera_controller.stop_video()
        self._logic_worker.reset_data()

    # Getters explicitos
    def get_widget(self):
        """
        Obtiene el widget de interfaz de calibracion.

        Returns:
            CalibrationWidget: Instancia del widget.
        """
        return self._widget

    def get_camera_controller(self):
        """
        Obtiene el controlador de camara interno.

        Returns:
            CameraController: Instancia del controlador de camara.
        """
        return self._camera_controller
