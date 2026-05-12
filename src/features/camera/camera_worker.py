""" Modulo donde se implementa el hilo de procesamiento para la captura y el procesamiento de las
    imágenes provenientes de la cámara
"""
from threading import Lock
import numpy as np
import cv2
from PyQt6.QtCore import QThread, pyqtSignal, QThreadPool, pyqtSlot
from src.services.vision import ChArUcoDetection, EllipseDetection, CameraControl, PoseEstimation, DetectionDrawer
from src.services.data.signals import SearchSignalManager, DrawViewSignalManager, SimulationSignalManager
from src.services.data.timers import FrameCounter


class CameraWorker(QThread):
    """ Worker thread para manejar la captura y procesamiento de video.
    """
    frame_ready = pyqtSignal(object)  # numpy BGR frame or UMat
    error_occurred = pyqtSignal(str)

    def __init__(self, camera_index: int = 0, camera_config: dict = None, is_calibration: bool = False):
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

        self.thread_pool = QThreadPool().globalInstance()
        self.camera = CameraControl(
            camera_index, self.camera_config, is_calibration)

        self.search_manager = SearchSignalManager().get_instance()
        self.draw_view_manager = DrawViewSignalManager.get_instance()
        self.frame_counter = FrameCounter.get_instance()
        self.frame_counter.process_frame_signal.connect(self._on_process_frame)
        self.sim_signal_manager = SimulationSignalManager.get_instance()

    def run(self):
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
                    charuco_state, ellipse_state = self.search_manager.get_state()
                    self.frame_id += 1
                    if charuco_state:
                        self.thread_pool.start(ChArUcoDetection(
                            frame_umat, self.frame_id, self.on_charuco_done, self._emit_error))
                    if ellipse_state:
                        self.thread_pool.start(EllipseDetection(
                            frame_umat, self.frame_id, self.last_roi,
                            self.on_ellipses_done, self._emit_error))

                    self._process_frame = False

                view = self.draw_view_manager.get_state()
                self.thread_pool.start(DetectionDrawer(frame, self.results.get(
                    self.frame_id-1), view, self.custom_origin, self._emit_frame_ready, self._emit_error))
                self.frame_counter.tick()

        except (OSError, RuntimeError) as e:
            self.error_occurred.emit(
                f"Error en worker thread (CameraWorker): {e}")
        finally:
            self.camera.camera_off()

    def _emit_frame_ready(self, frame: np.ndarray):
        if frame is not None:
            self.frame_ready.emit(frame)

    def _emit_error(self, msg: str):
        self.error_occurred.emit(msg)

    def stop(self):
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
        self._running = False

    def resume(self):
        self._running = True

    def _on_process_frame(self):
        """Slot conectado a FrameCounter.process_frame_signal.

        Ejecuta la detección usando el frame recibido y actualiza el caché interno.
        """
        self._process_frame = True

    @pyqtSlot(int, object)
    def on_charuco_done(self, fid: int, data: dict):
        with self.lock:
            entry = self.results.setdefault(
                fid, {"charuco": None, "ellipses": None, "poses": None})
            entry["charuco"] = data
            if data and data.get("roi") is not None:
                self.last_roi = data["roi"]
            else:
                self.last_roi = None
            self._try_pose_estimation(fid)
            self._trim_buffer()

    @pyqtSlot(int, object)
    def on_ellipses_done(self, fid: int, data: dict):
        with self.lock:
            entry = self.results.setdefault(
                fid, {"charuco": None, "ellipses": None, "poses": None})
            entry["ellipses"] = data
            self._try_pose_estimation(fid)
            self._trim_buffer()

    def on_pose_done(self, fid: int, poses: dict):
        with self.lock:
            self.sim_signal_manager.sphere_pos.emit(poses)
            entry = self.results.get(fid)
            if not entry:
                return
            entry["poses"] = poses
            ellipses = entry.get("ellipses") or {}
            for color, position in poses.items():
                if color in ellipses:
                    ellipses[color]["position"] = position

    def _try_pose_estimation(self, fid: int):
        entry = self.results.get(fid)
        last_entry = self.results.get(fid - 1)
        if last_entry and last_entry.get("poses") is None:
            has_charuco_or_ellipses = (last_entry.get("charuco") is not None or
                                       last_entry.get("ellipses") is not None)
            if has_charuco_or_ellipses:
                self.sim_signal_manager.sphere_pos.emit({})
        if not entry:
            return
        if entry["charuco"] is not None and entry["ellipses"] is not None:
            self.thread_pool.start(PoseEstimation(
                entry, self.camera_matrix,
                self.dist_coeff, self.sphere_radius,
                self.custom_origin,
                self._emit_error,
                frame_id=fid,
                pose_callback=self.on_pose_done))

    def _trim_buffer(self):
        if len(self.results) <= self.max_buffer:
            return
        oldest = min(self.results.keys())
        del self.results[oldest]
