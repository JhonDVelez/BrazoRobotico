""" Modulo donde se implementa el hilo de procesamiento para la captura y el procesamiento de las 
    imágenes provenientes de la cámara
"""
import threading
import traceback
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal, QRunnable, QThreadPool, pyqtSlot
from vision.camera_chessboard import CameraChessBoard
from vision.pose_estimation import PoseEstimation
from data import SearchSignalManager
from data import config_manager as cfg


class FrameProcessRunnable(QRunnable):
    """Runnable para procesar un frame en un thread pool y devolver resultado vía callback."""

    def __init__(self, frame: np.ndarray, camera_chess_board: CameraChessBoard, pose_estimation: PoseEstimation, callback, error_callback):
        super().__init__()
        self.frame = frame
        self.camera_chess_board = camera_chess_board
        self.pose_estimation = pose_estimation
        self.callback = callback
        self.error_callback = error_callback
        self.state = SearchSignalManager().get_instance()
        self.charuco_activated, self.sphere_activated = self.state.get()

    def run(self):
        try:
            result = self.frame
            if self.charuco_activated:
                drawn_image, processed_image, search_results, mask_corners = \
                    self.camera_chess_board.get_coordinates(self.frame)

                result = drawn_image if drawn_image is not None else self.frame

                if self.sphere_activated:
                    circles_find = self.pose_estimation.get_sphere_pose(
                        original_frame=self.frame,
                        drawn_frame=drawn_image,
                        processed_frame=processed_image,
                        charuco_results=search_results,
                        search_mask_corners=mask_corners,
                    )
                    if circles_find is not None:
                        result = circles_find

            elif self.sphere_activated:
                circles_find = self.pose_estimation.get_sphere_pose(self.frame)
                if circles_find is not None:
                    result = circles_find

            self.callback(result)

        except Exception:
            self.error_callback(
                f"Error procesando frame (FrameProcessRunnable): {traceback.print_exc()}")


class CameraWorker(QThread):
    """ Worker thread para manejar la captura y procesamiento de video.

    Captura en un hilo dedicado y usa un QThreadPool para procesar cada frame sin bloquear
    el bucle de captura.
    """

    frame_ready = pyqtSignal(object)  # numpy BGR frame
    error_occurred = pyqtSignal(str)

    def __init__(self, camera_index: int = 0, is_calibration: bool = False):
        super().__init__()
        data = cfg.get("camera.json", "chessboard")
        x = data["x"]
        y = data["y"]
        self.camera_chess_board = CameraChessBoard((y, x))
        self.camera_chess_board.set_camera_index(camera_index)
        self.pose_estimation = PoseEstimation(
            self.camera_chess_board.charuco_board)

        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(16)

        self._running = True
        self._paused = False
        self._busy = False
        self._lock = threading.Lock()

        self.is_calibration = is_calibration

    def set_camera_index(self, index: int):
        if hasattr(self, "camera_chess_board"):
            self.camera_chess_board.set_camera_index(index)

    def run(self):
        try:
            if not self.camera_chess_board.camera_on():
                self.error_occurred.emit(
                    "No se pudo inicializar la cámara (CameraWorker)")
                return

            while self._running:
                if self._paused:
                    continue

                frame = self.camera_chess_board.get_video_frame()
                if frame is None:
                    continue

                if self.thread_pool.activeThreadCount() >= 1:
                    continue

                if self.is_calibration:
                    self._emit_frame_ready(frame)
                else:
                    runnable = FrameProcessRunnable(
                        frame,
                        self.camera_chess_board,
                        self.pose_estimation,
                        self._emit_frame_ready,
                        self._emit_error,
                    )
                    self.thread_pool.start(runnable)

        except (OSError, RuntimeError) as e:
            self._emit_error(f"Error en worker thread (CameraWorker): {e}")

        finally:
            self.camera_chess_board.camera_off()

    def _emit_frame_ready(self, frame: np.ndarray):
        with self._lock:
            self._busy = False
        if frame is not None:
            self.frame_ready.emit(frame)

    def _emit_error(self, msg: str):
        with self._lock:
            self._busy = False
        self.error_occurred.emit(msg)

    def stop(self):
        self._running = False
        self._paused = False

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
            self.camera_chess_board.camera_off()
        except Exception:
            pass

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False
