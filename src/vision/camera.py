import sys
from typing import Optional
import math
import numpy as np
import cv2

# Intentar habilitar OpenCL (UMat) si está disponible
try:
    cv2.ocl.setUseOpenCL(True)
except Exception:
    pass


class CameraControl:
    """Clase que gestiona una cámara y sus operaciones básicas
       Optimizada para usar UMat (OpenCL) en preprocesado.
    """

    def __init__(self):
        self.cap: Optional[cv2.VideoCapture] = None
        self.camera_ready = False
        self.clahe = None

        # Configuraciones por defecto
        self.default_width = 640
        self.default_height = 360
        self.default_fps = 30

        self.clahe = cv2.createCLAHE(clipLimit=5.0, tileGridSize=(12, 12))

    def camera_on(self) -> bool:
        """Enciende la cámara con configuración optimizada"""
        try:
            self.__release_camera()

            # Usar DirectShow en Windows para mejor performance
            if sys.platform == "win32":
                self.cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
                if not self.cap or not self.cap.isOpened():
                    self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            elif sys.platform == "linux":
                self.cap = cv2.VideoCapture(1, cv2.CAP_V4L2)
                if not self.cap or not self.cap.isOpened():
                    # Si falla, intenta con el índice 0
                    self.cap = cv2.VideoCapture(0, cv2.CAP_V4L2)

            if not self.cap or not self.cap.isOpened():
                raise IOError("No se pudo abrir la cámara")

            self.__configure_camera()

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
        """Captura un frame de la cámara (BGR). Reducimos resolución para aliviar CPU/GPU."""
        if not self.camera_ready or not self.cap:
            return None

        ret, frame = self.cap.read()
        if ret:
            # Redimensionamos a 640x360 para análisis más rápido (puedes cambiar)
            # frame = cv2.resize(frame, (640, 360),
            #                    interpolation=cv2.INTER_LINEAR)
            return frame  # BGR numpy array
        return None

    def __configure_camera(self):
        """Configura propiedades de la cámara para optimizar performance"""
        if not self.cap:
            return
        # Aquí puedes setear width/height/fps si tu cámara lo soporta:
        try:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.default_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.default_height)
            # self.cap.set(cv2.CAP_PROP_FPS, self.default_fps)
        except Exception:
            pass

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

    def apply_histogram_equalization(self, img):
        """ Aplica cambios de contraste usando el metodo de clahe que separa la imagen en secciones
            los cuales se analizan por separado y se realizan correcciones para mejorar la calidad
            de la imágenes en cuanto a contrastes

            CLAHE (Contrast Limited Adaptive Histogram Equalization) divide la imagen en secciones
            y toma datos de contraste para posteriormente realizar ajustes por separado a cada 
            sección obteniendo un mejor resultado que con métodos tradicionales.
        """

        if img is None:
            return img

        lab = cv2.cvtColor(img, cv2.COLOR_BGR2Lab)
        l, a, b = cv2.split(lab)
        l_clahe = self.clahe.apply(l)
        lab_clahe = cv2.merge([l_clahe, a, b])
        return cv2.cvtColor(lab_clahe, cv2.COLOR_Lab2BGR)
