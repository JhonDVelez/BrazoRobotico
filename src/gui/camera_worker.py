""" Modulo donde se implementa el hilo de procesamiento para la captura y el procesamiento de las 
    imágenes provenientes de la cámara
"""
from threading import Lock
import numpy as np
import cv2
from PyQt6.QtCore import QThread, pyqtSignal, QThreadPool, pyqtSlot
from vision.charuco_detection import ChArUcoDetection
from vision.ellipse_detection import EllipseDetection
from vision.camera_control import CameraControl
from vision.pose_estimation import PoseEstimation
from vision.detection_drawer import DetectionDrawer
from data import SearchSignalManager, DrawViewSignalManager
from data.control_utils import FrameCounter


class CameraWorker(QThread):
    """ Worker thread para manejar la captura y procesamiento de video.

    Captura en un hilo dedicado y usa un QThreadPool para procesar cada frame sin bloquear
    el bucle de captura.
    """

    frame_ready = pyqtSignal(object)  # numpy BGR frame
    error_occurred = pyqtSignal(str)

    def __init__(self, camera_index: int = 0, is_calibration: bool = False):
        super().__init__()
        self.frame_id = 0
        self._running = True
        self._process_frame = False
        self.lock = Lock()
        self.is_calibration = is_calibration
        self.results = {}  # {fid: {"charuco":..., "ellipses":...}}
        self.max_buffer = 3
        self.last_roi = None  # Region de interes

        self.thread_pool = QThreadPool().globalInstance()
        self.thread_pool.setMaxThreadCount(4)
        self.camera = CameraControl(camera_index, is_calibration)
        self.search_manager = SearchSignalManager().get_instance()
        self.draw_view_manager = DrawViewSignalManager.get_instance()
        self.frame_counter = FrameCounter.get_instance()
        self.frame_counter.process_frame_signal.connect(
            self._on_process_frame)

    def run(self):
        try:
            if not self.camera.camera_on():
                self.error_occurred.emit(
                    "No se pudo inicializar la cámara (CameraWorker)")
                return
            while self._running:
                frame = self.camera.take_frame()
                frame_umat = cv2.UMat(frame)
                if frame is None:
                    raise IOError("No se pudo obtener frame de la cámara")

                if self.thread_pool.activeThreadCount() >= 1:
                    continue

                if self.is_calibration:
                    self._emit_frame_ready(frame)
                elif self._process_frame:
                    charuco_state, ellipse_state = self.search_manager.get_state()
                    self.frame_id += 1
                    if charuco_state:
                        self.thread_pool.start(ChArUcoDetection(
                            frame_umat, self.frame_id, self.on_charuco_done, self._emit_error))
                    if ellipse_state:
                        self.thread_pool.start(EllipseDetection(
                            frame_umat, self.frame_id, self.last_roi, self.on_ellipses_done, self._emit_error))

                    self._process_frame = False

                view = self.draw_view_manager.get_state()
                self.thread_pool.start(DetectionDrawer(frame_umat, self.results.get(
                    self.frame_id-1), view, self._emit_frame_ready, self._emit_error))
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

        # Esperar que el hilo termine su ejecución
        if not self.wait(3000):
            print(
                "Warning: Video thread no terminó correctamente, forzando terminación: CameraWorker")
            self.terminate()
            self.wait(1000)

        # Asegurarse que la cámara se apague
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
                fid, {"charuco": None, "ellipses": None})
            entry["charuco"] = data

            # actualizar ROI para el siguiente frame (fuera del join)
            if data and data.get("roi") is not None:
                self.last_roi = data["roi"]
            else:
                self.last_roi = None

            # self._try_launch_fusion(fid)
            self._trim_buffer()

    @pyqtSlot(int, object)
    def on_ellipses_done(self, fid: int, data: dict):
        with self.lock:
            entry = self.results.setdefault(
                fid, {"charuco": None, "ellipses": None})
            entry["ellipses"] = data

            # self._try_launch_fusion(fid)
            self._trim_buffer()

    def _try_launch_fusion(self, fid: int):
        entry = self.results.get(fid)
        if not entry:
            return
        if entry["charuco"] is not None and entry["ellipses"] is not None:
            # Lanzar C SOLO cuando ambos existen para el mismo fid
            # self.pool.start(FusionWorker(
            #     fid, entry["charuco"], entry["ellipses"], self.signals))
            # limpiar ese fid para no reprocesar
            del self.results[fid]

    def _trim_buffer(self):
        # Evitar backlog en tiempo real
        if len(self.results) <= self.max_buffer:
            return
        # eliminar el más antiguo
        oldest = min(self.results.keys())
        del self.results[oldest]
