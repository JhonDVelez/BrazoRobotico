""" Modulo donde se implementa el hilo de procesamiento para la captura y el procesamiento de las 
    imágenes provenientes de la cámara
"""
import threading
import numpy as np
import cv2
from PyQt6.QtCore import QThread, pyqtSignal, QRunnable, QThreadPool
from vision.camera_chessboard import CameraChessBoard


class FrameProcessRunnable(QRunnable):
    """Runnable para procesar un frame en un thread pool y devolver resultado vía callback."""

    def __init__(self, frame: np.ndarray, camera_chess_board: CameraChessBoard, callback, error_callback):
        super().__init__()
        self.frame = frame
        self.camera_chess_board = camera_chess_board
        self.callback = callback
        self.error_callback = error_callback

    def run(self):
        try:
            processed = self.camera_chess_board.get_coordinates(self.frame)
            self.callback(processed if processed is not None else self.frame)
        except Exception as e:
            self.error_callback(f"Error procesando frame: {e}")


class CameraWorker(QThread):
    """ Worker thread para manejar la captura y procesamiento de video.

    Captura en un hilo dedicado y usa un QThreadPool para procesar cada frame sin bloquear
    el bucle de captura.
    """

    frame_ready = pyqtSignal(object)  # numpy BGR frame
    error_occurred = pyqtSignal(str)

    def __init__(self, camera_index: int = 0):
        super().__init__()
        self.camera_index = camera_index
        self.camera_chess_board = CameraChessBoard()
        self.camera_chess_board.start()

        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(1)

        self._running = True
        self._paused = False
        self._busy = False
        self._lock = threading.Lock()

    def run(self):
        try:
            if not self.camera_chess_board.camera_on():
                self.error_occurred.emit("No se pudo inicializar la cámara")
                return

            while self._running:
                if self._paused:
                    self.msleep(10)
                    continue

                frame = self.camera_chess_board.camera.take_frame()
                if frame is None:
                    self.msleep(5)
                    continue

                with self._lock:
                    if self._busy:
                        self.msleep(1)
                        continue
                    self._busy = True

                runnable = FrameProcessRunnable(
                    frame,
                    self.camera_chess_board,
                    self._emit_frame_ready,
                    self._emit_error,
                )
                self.thread_pool.start(runnable)

                self.msleep(1)

        except (OSError, RuntimeError) as e:
            self._emit_error(f"Error en worker thread: {e}")

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

        self.thread_pool.waitForDone(1000)

        if not self.wait(2000):
            print("Warning: Video thread no terminó correctamente, forzando terminación")
            self.terminate()
            self.wait(1000)

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False
