import os
import sys
import numpy as np
from typing import Optional
import cv2
from cv2_enumerate_cameras import enumerate_cameras
from data import config_manager as cfg

os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"

# Intentar habilitar OpenCL (UMat) si está disponible
try:
    cv2.ocl.setUseOpenCL(True)
except Exception:
    pass


class CameraControl:
    """Clase que gestiona una cámara y sus operaciones básicas
       Optimizada para usar UMat (OpenCL) en preprocesado.
    """

    def __init__(self, is_calibration: bool = False):
        super().__init__()
        self.cap: Optional[cv2.VideoCapture] = None
        self.camera_ready = False

        # Configuraciones por defecto
        camera_config = cfg.load("camera.json")
        # Configuraciones básicas de la cámara
        self.default_width = camera_config.get("resolution")["width"]
        self.default_height = camera_config.get("resolution")["height"]
        self.default_fps = camera_config.get("resolution")["fps"]
        # Datos de calibración de la cámara
        self.camera_matrix = np.array(camera_config.get("matrix"))
        self.dist_coeff = np.array(
            camera_config.get("distortion coefficients"))

        self.is_calibration = is_calibration
        self.camera_index = 0

    def set_camera_index(self, index: int):
        self.camera_index = index

    def camera_on(self) -> bool:
        """Enciende la cámara con configuración optimizada"""
        try:
            self.__release_camera()

            if sys.platform == "win32":
                self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW,
                                            params=(cv2.CAP_PROP_FRAME_WIDTH, self.default_width,
                                                    cv2.CAP_PROP_FRAME_HEIGHT, self.default_height,
                                                    cv2.CAP_PROP_FPS, self.default_fps,
                                                    cv2.CAP_PROP_AUTO_WB, 1,
                                                    cv2.CAP_PROP_BITRATE, 18500,
                                                    cv2.CAP_PROP_HW_ACCELERATION, cv2.VIDEO_ACCELERATION_D3D11,
                                                    cv2.CAP_PROP_HW_ACCELERATION_USE_OPENCL, 1,
                                                    cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG")))

            # En Linux, usamos V4L2
            elif sys.platform == "linux":
                self.cap = cv2.VideoCapture(camera_index, cv2.CAP_V4L2)

            if not self.cap or not self.cap.isOpened():
                raise IOError("No se pudo abrir la cámara")

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
        # Captura frame de la cámara
        ret, frame = self.cap.read()
        if ret:
            if self.is_calibration:
                return frame
            # Obtiene la nueva matriz de calibración
            h,  w = frame.shape[:2]
            new_cam_matrix, roi = cv2.getOptimalNewCameraMatrix(
                self.camera_matrix, self.dist_coeff, (w, h), 1, (w, h))
            dst = cv2.undistort(frame, self.camera_matrix,
                                self.dist_coeff, None, new_cam_matrix)

            x, y, w, h = roi
            dst = dst[y:y+h, x:x+w]
            return dst
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

    def apply_division_trick(self, img):
        """ El truco de la división: Esta es la forma más agresiva de "ignorar" una sombra.
            Al dividir la imagen por una versión muy borrosa de sí misma, se elimina la zona
            oscura de la sombra y solo quedan los bordes de alto contraste de las casillas
            del tablero de ajedrez.
        """
        smooth = cv2.GaussianBlur(img, (95, 95), 0)
        return cv2.divide(img, smooth, scale=255)
