"""
Modulo donde se implementa el hilo de procesamiento para la captura de video.

Este modulo contiene la clase CameraWorker, la cual gestiona la captura de frames,
la delegacion de tareas de vision artificial (deteccion de ChArUco, esferas y poses)
mediante un QThreadPool, y la emision de resultados procesados para su visualizacion.

Conexiones:
    - Escucha a `FrameCounter` para determinar cuando procesar un frame semantico.
    - Utiliza `SearchSignalManager` para conocer que detecciones realizar.
    - Emite posiciones 3D a traves de `SimulationSignalManager`.
    - Reporta frames procesados mediante `frame_ready` para la UI.
"""

from threading import Lock
import numpy as np
import cv2
from PyQt6.QtCore import QThread, pyqtSignal, QThreadPool, pyqtSlot
from src.services.vision import ChArUcoDetection, CircleDetection, CameraConnection, PoseEstimation, DetectionDrawer
from src.services.data.signals import CameraSignalManager, SearchSignalManager, DrawViewSignalManager
from src.services.data.timers import FrameCounter


class CameraWorker(QThread):
    """
    Worker thread para manejar la captura y procesamiento concurrente de video.

    Orquesta la captura de imagenes y despacha tareas de vision a hilos secundarios
    del sistema, manteniendo un buffer de resultados sincronizados para evitar latencia
    en la visualizacion.

    Attributes:
        frame_ready (pyqtSignal): Emite el frame (np.ndarray) listo para mostrar.
        error_occurred (pyqtSignal): Emite mensajes de error (str) durante el proceso.
    """
    frame_ready = pyqtSignal(object)  # numpy BGR frame or UMat
    error_occurred = pyqtSignal(str)
    sphere_ready = pyqtSignal(dict)

    def __init__(self, camera_index: int = 0, camera_config: dict = None, is_calibration: bool = False):
        """
        Inicializa el worker de camara con la configuracion proporcionada.

        Args:
            camera_index (int): Indice de la camara en el sistema (0, 1, etc.).
            camera_config (dict, optional): Configuracion de matriz, distorsion y colores.
            is_calibration (bool): Indica si se opera en modo calibracion (sin vision pesada).
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
        self.sphere_radius = 20.0
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

        self.camera_signal_manager = CameraSignalManager().get_instance()
        self.search_signal_manager = SearchSignalManager().get_instance()
        self.draw_view_signal_manager = DrawViewSignalManager.get_instance()
        self.frame_counter = FrameCounter.get_instance()
        self.frame_counter.process_frame_signal.connect(self._on_process_frame)
        self.pick_place_active = False
        self.latest_circles = {}

    def run(self):
        """
        Bucle de ejecucion principal del hilo.

        Captura frames continuamente y decide que tareas de vision despachar
        basandose en el estado del sistema y la cadencia de `FrameCounter`.
        """
        try:
            if not self.camera.camera_on():
                self.error_occurred.emit(
                    "No se pudo inicializar la cámara (CameraWorker)")
                return
            while self._running:
                frame = self.camera.take_frame()
                if frame is None:
                    raise IOError("No se pudo obtener frame de la cámara")

                frame_umat = cv2.UMat(frame.copy())

                if self.thread_pool.activeThreadCount() >= self.thread_pool.maxThreadCount():
                    continue

                if self.is_calibration:
                    self._emit_frame_ready(frame)
                    continue
                elif self._process_frame:
                    charuco_state, circle_state = self.search_signal_manager.get_state()
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

                view = self.draw_view_signal_manager.get_state()
                self.thread_pool.start(DetectionDrawer(
                    frame, self.results.get(
                        self.frame_id-1), view, self.custom_origin,
                    self.frame_size[0], self._emit_frame_ready, self._emit_error))
                self.frame_counter.tick()

        except (OSError, RuntimeError) as e:
            self.error_occurred.emit(
                f"Error en worker thread (CameraWorker): {e}")
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
        Encapsula la emision de errores desde hilos secundarios.

        Args:
            msg (str): Mensaje de error.
        """
        self.error_occurred.emit(msg)

    def stop(self):
        """
        Detiene la ejecucion del worker de forma segura, esperando a las tareas pendientes.
        """
        self._running = False
        # Esperar a que se procesen tareas pendientes en el pool
        self.thread_pool.waitForDone(2000)
        if not self.wait(3000):
            self.terminate()
            self.wait(1000)
        try:
            self.camera.camera_off()
        except Exception:
            pass

    def pause(self):
        """
        Pausa el bucle de captura estableciendo el flag de ejecucion a False.
        """
        self._running = False

    def resume(self):
        """
        Reanuda el bucle de captura estableciendo el flag de ejecucion a True.
        """
        self._running = True

    def _on_process_frame(self):
        """
        Slot que habilita el procesamiento de vision pesada para el siguiente frame.
        """
        self._process_frame = True

    @pyqtSlot(int, object)
    def on_charuco_done(self, fid: int, data: dict):
        """
        Callback ejecutado cuando finaliza la deteccion de ChArUco.

        Args:
            fid (int): ID del frame procesado.
            data (dict): Resultados de la deteccion (corners, ids, roi).
        """
        with self.lock:
            entry = self.results.setdefault(
                fid, {"charuco": None, "circles": None, "poses": None})
            entry["charuco"] = data
            if data and data.get("roi") is not None:
                self.last_roi = data["roi"]
            else:
                self.last_roi = None
            self._try_pose_estimation(fid)
            self._trim_buffer()

    @pyqtSlot(int, object)
    def on_circles_done(self, fid: int, data: dict):
        """
        Callback ejecutado cuando finaliza la deteccion de esferas de color.

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
        Callback ejecutado cuando finaliza la estimacion de pose 3D.

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
