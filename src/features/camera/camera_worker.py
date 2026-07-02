"""
Módulo donde se implementa el hilo de procesamiento para la captura de video.

Este módulo contiene la clase CameraWorker, la cual gestiona la captura de frames,
la delegación de tareas de visión artificial (detección de ChArUco, esferas y poses)
mediante un QThreadPool, y la emisión de resultados procesados para su visualización.

Conexiones:
    - Escucha a `FrameCounter` para determinar cuando procesar un frame semántico.
    - El estado de búsqueda (ChArUco/esferas) y de overlays lo inyecta el
      CameraController mediante slots locales; el worker no accede al bus global.
    - Emite resultados de detección mediante señales locales (`charuco_detected`)
      que el controlador puentea hacia el bus global.
    - Reporta frames procesados mediante `frame_ready` para la UI.
"""

from threading import Lock
import numpy as np
import cv2
from PyQt6.QtCore import QThread, pyqtSignal, QThreadPool, pyqtSlot
from src.services.vision import ChArUcoDetection, CircleDetection, CameraConnection, PoseEstimation, DetectionDrawer
from src.services.data.timers import FrameCounter


class CameraWorker(QThread):
    """
    Worker thread para manejar la captura y procesamiento concurrente de video.

    Orquesta la captura de imágenes y despacha tareas de visión a hilos secundarios
    del sistema, manteniendo un buffer de resultados sincronizados para evitar latencia
    en la visualización.

    Attributes:
        frame_ready (pyqtSignal): Emite el frame (np.ndarray) listo para mostrar.
        error_occurred (pyqtSignal): Emite mensajes de error (str) durante el proceso.
    """
    frame_ready = pyqtSignal(object)  # numpy BGR frame or UMat
    error_occurred = pyqtSignal(str)
    sphere_ready = pyqtSignal(dict)
    # (frame_id, data) -> bus via controller
    charuco_detected = pyqtSignal(int, object)

    def __init__(self, camera_index: int = 0, camera_config: dict = None, is_calibration: bool = False,
                 search_state: tuple = (False, False), view_state: tuple = (False, False)):
        """
        Inicializa el worker de cámara con la configuración proporcionada.

        Args:
            camera_index (int): Índice de la cámara en el sistema (0, 1, etc.).
            camera_config (dict, optional): Configuración de matriz, distorsión y colores.
            is_calibration (bool): Indica si se opera en modo calibración (sin visión pesada).
            search_state (tuple): Estado inicial (charuco, circle) de las búsquedas.
            view_state (tuple): Estado inicial (charuco, circle) de los overlays.
        """
        super().__init__()
        self.frame_id = 0
        self._running = True
        self._process_frame = False
        self.lock = Lock()
        self.is_calibration = is_calibration
        self.results = {}
        self.max_buffer = 3
        self.last_roi = None
        self.sphere_radius = camera_config.get("sphere_radius", 30.0)
        self.custom_origin = (180.0, 0.0, 0.0)

        # Inyección de configuración
        self.camera_config = camera_config or {}
        self.camera_matrix = np.array(self.camera_config.get("matrix", []))
        self.dist_coeff = np.array(
            self.camera_config.get("distortion coefficients", []))
        self.hsv_colors = self.camera_config.get("hsv_colors")
        self.frame_size = list(self.camera_config.get(
            "resolution", {"width": 1280, "height": 720}).values())[:2]

        self.thread_pool = QThreadPool().globalInstance()
        self.camera = CameraConnection(
            camera_index, self.camera_config, is_calibration)

        # Estado inyectado por el controlador (sin acceso al bus global).
        # Protegido por self.lock para lectura/escritura entre hilos.
        self._search_state = tuple(search_state)
        self._view_state = tuple(view_state)

        self.frame_counter = FrameCounter.get_instance()
        self.frame_counter.process_frame_signal.connect(self._on_process_frame)
        self.pick_place_active = False
        self.latest_circles = {}

    def run(self):
        """
        Bucle de ejecución principal del hilo.

        Captura frames continuamente y decide que tareas de visión despachar
        basándose en el estado del sistema y la cadencia de `FrameCounter`.
        """
        try:
            if not self.camera.camera_on():
                raise IOError(
                    "No se pudo inicializar la cámara, verifique la conexión de la cámara.")
            while self._running:
                frame = self.camera.take_frame()
                if frame is None:
                    raise IOError(
                        "No fue posible obtener el frame de video, verifique la conexión de la cámara.")

                frame_umat = cv2.UMat(frame.copy())

                if self.thread_pool.activeThreadCount() >= self.thread_pool.maxThreadCount():
                    continue

                if self.is_calibration:
                    self._emit_frame_ready(frame)
                    continue
                elif self._process_frame:
                    with self.lock:
                        charuco_state, circle_state = self._search_state
                    self.frame_id += 1
                    if charuco_state:
                        self.thread_pool.start(ChArUcoDetection(
                            frame_umat, self.frame_id, self.camera_matrix, self.dist_coeff,
                            self.on_charuco_done, self._emit_error))
                    if circle_state:
                        self.thread_pool.start(CircleDetection(
                            frame_umat, self.frame_id, self.last_roi, self.hsv_colors,
                            self.on_circles_done, self._emit_error))

                    self._process_frame = False

                view = self.draw_view_state()
                self.thread_pool.start(DetectionDrawer(
                    frame, self.results.get(
                        self.frame_id-1, {}), view, self.custom_origin,
                    self.frame_size[0], self._emit_frame_ready, self._emit_error))
                self.frame_counter.tick()

        except (OSError, RuntimeError) as e:
            self.error_occurred.emit(str(e))
        finally:
            self.camera.camera_off()

    def _emit_frame_ready(self, frame: np.ndarray):
        """
        Emite la señal de frame listo para la UI de forma segura.

        Args:
            frame (np.ndarray): Imagen en formato BGR.
        """
        if frame is not None:
            self.frame_ready.emit(frame)

    def _emit_error(self, msg: str):
        """
        Encapsula la emisión de errores desde hilos secundarios.

        Args:
            msg (str): Mensaje de error.
        """
        self.error_occurred.emit(msg)

    def stop(self):
        """
        Detiene la ejecución del worker de forma segura, esperando a las tareas pendientes.
        """
        self._running = False
        # Esperar a que se procesen tareas pendientes en el pool
        self.thread_pool.waitForDone(2000)
        if not self.wait(3000):
            self.terminate()
            self.wait(1000)
        try:
            self.camera.camera_off()
        except (OSError, RuntimeError):
            # Falla al liberar cámara en parada forzada — ignorar
            pass

    def pause(self):
        """
        Pausa el bucle de captura estableciendo el flag de ejecución a False.
        """
        self._running = False

    def resume(self):
        """
        Reanuda el bucle de captura estableciendo el flag de ejecución a True.
        """
        self._running = True

    def _on_process_frame(self):
        """
        Slot que habilita el procesamiento de visión pesada para el siguiente frame.
        """
        self._process_frame = True

    def draw_view_state(self) -> tuple:
        """
        Obtiene el estado actual de overlays de forma thread-safe.

        Returns:
            tuple: (ChArUco_visible, circle_visible).
        """
        with self.lock:
            return self._view_state

    @pyqtSlot(bool, bool)
    def set_search_state(self, charuco: bool, circle: bool):
        """
        Actualiza el estado de búsqueda inyectado por el controlador.

        Args:
            charuco (bool): True para buscar el tablero ChArUco.
            circle (bool): True para buscar esferas de color.
        """
        with self.lock:
            self._search_state = (charuco, circle)

    @pyqtSlot(bool, bool)
    def set_view_state(self, charuco: bool, circle: bool):
        """
        Actualiza el estado de overlays inyectado por el controlador.

        Args:
            ChArUco (bool): True para dibujar la cuadrícula ChArUco.
            circle (bool): True para dibujar la geometría de esferas.
        """
        with self.lock:
            self._view_state = (charuco, circle)

    @pyqtSlot(float)
    def set_sphere_radius(self, radius: float):
        """
        Actualiza el radio de la esfera usado en la estimación de pose.

        Args:
            radius (float): Nuevo radio en milímetros.
        """
        with self.lock:
            self.sphere_radius = float(radius)

    @pyqtSlot(int, object)
    def on_charuco_done(self, fid: int, data: dict):
        """
        Callback ejecutado cuando finaliza la detección de ChArUco.

        Args:
            fid (int): ID del frame procesado.
            data (dict): Resultados de la detección (corners, ids, roi).
        """
        with self.lock:
            entry = self.results.setdefault(
                fid, {"charuco": None, "circles": None, "poses": None})
            entry["charuco"] = data
            self.charuco_detected.emit(fid, data)
            if data and data.get("roi") is not None:
                self.last_roi = data["roi"]
            else:
                self.last_roi = None
            self._try_pose_estimation(fid)
            self._trim_buffer()

    @pyqtSlot(int, object)
    def on_circles_done(self, fid: int, data: dict):
        """
        Callback ejecutado cuando finaliza la detección de esferas de color.

        Args:
            fid (int): ID del frame procesado.
            data (dict): Resultados de las esferas por color.
        """
        with self.lock:
            entry = self.results.setdefault(
                fid, {"charuco": None, "circles": None, "poses": None})
            entry["circles"] = data
            self._try_pose_estimation(fid)
            self._trim_buffer()

    def on_pose_done(self, fid: int, poses: dict):
        """
        Callback ejecutado cuando finaliza la estimación de pose 3D.

        Args:
            fid (int): ID del frame procesado.
            poses (dict): Coordenadas 3D (x, y, z) de las esferas.
        """
        with self.lock:
            entry = self.results.get(fid)
            if not entry:
                return
            entry["poses"] = poses
            circles = entry.get("circles") or {}
            for color, position in poses.items():
                if color in circles:
                    circles[color]["position"] = position
            self.sphere_ready.emit(circles)

    def _try_pose_estimation(self, fid: int):
        """
        Intenta iniciar la tarea de PoseEstimation si tiene datos de ChArUco y elipses.

        Args:
            fid (int): ID del frame a verificar.
        """
        entry = self.results.get(fid)
        if not entry:
            return
        if entry["charuco"] is not None and entry["circles"] is not None:
            self.thread_pool.start(PoseEstimation(
                entry, self.camera_matrix,
                self.dist_coeff,
                self.frame_size,
                self.sphere_radius,
                self.custom_origin,
                self._emit_error,
                frame_id=fid,
                pose_callback=self.on_pose_done))

    def _trim_buffer(self):
        """
        Limpia el buffer de resultados antiguo para limitar el uso de memoria.
        """
        if len(self.results) <= self.max_buffer:
            return
        oldest = min(self.results.keys())
        del self.results[oldest]
