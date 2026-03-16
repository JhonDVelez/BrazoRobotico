import sys
from typing import Optional
import cv2
from PyQt6.QtCore import QThread
from cv2_enumerate_cameras import enumerate_cameras
from data import config_manager as cfg

# Intentar habilitar OpenCL (UMat) si está disponible
try:
    cv2.ocl.setUseOpenCL(True)
except Exception:
    pass


class CameraControl(QThread):
    """Clase que gestiona una cámara y sus operaciones básicas
       Optimizada para usar UMat (OpenCL) en preprocesado.
    """

    def __init__(self):
        super().__init__()
        self.cap: Optional[cv2.VideoCapture] = None
        self.camera_ready = False

        # Configuraciones por defecto
        camera_config = cfg.load("camera.json").get("resolution")
        self.default_width = camera_config["width"]
        self.default_height = camera_config["height"]
        self.default_fps = camera_config["fps"]
        self.clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))

    def camera_on(self) -> bool:
        """Enciende la cámara con configuración optimizada"""
        try:
            self.__release_camera()

            cameras = enumerate_cameras(apiPreference=cv2.CAP_MSMF)
            if not cameras:
                raise IOError("No hay camaras disponibles.")
            else:
                camera_index = cameras[-1].index

            # En Windows, MSMF + MJPG
            if sys.platform == "win32":
                self.cap = cv2.VideoCapture(camera_index, cv2.CAP_MSMF)
                self.cap.set(cv2.CAP_PROP_FOURCC,
                             cv2.VideoWriter_fourcc(*"MJPG"))

            # En Linux, usamos V4L2
            elif sys.platform == "linux":
                self.cap = cv2.VideoCapture(camera_index, cv2.CAP_V4L2)

            if not self.cap or not self.cap.isOpened():
                raise IOError("No se pudo abrir la cámara")

            # Ajustamos resolución y FPS preferidos.
            # La cámara puede no respetar valores exactos, pero con MJPG mejora throughput.
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,
                         min(self.default_width, 640))
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT,
                         min(self.default_height, 360))
            self.cap.set(cv2.CAP_PROP_FPS, max(self.default_fps, 30))

            self.camera_ready = True
            return True

        except IOError as e:
            print(f"Error al inicializar cámara: {e}")
            self.__release_camera()
            return False
        except RuntimeError as e:
            print(f"Error durante ejecucion: {e}")
            self.__release_camera()
            return False

    def camera_off(self):
        """Apaga la cámara y libera recursos"""
        self.camera_ready = False
        self.__release_camera()
        cv2.destroyAllWindows()

    def camera_is_on(self):
        """Verifica si la cámara está activa"""
        return self.cap is not None and self.cap.isOpened() and self.camera_ready

    def take_frame(self):
        """Captura un frame de la cámara (BGR). Devuelve None si no hay frame."""
        if not self.camera_ready or not self.cap:
            return None

        ret, frame = self.cap.read()
        if ret:
            return frame
        return None

    def __release_camera(self):
        """Libera recursos de la cámara"""
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None

    def toggle_camera(self):
        """Alterna el estado de la cámara"""
        if self.camera_is_on():
            self.camera_off()
        else:
            self.camera_on()
