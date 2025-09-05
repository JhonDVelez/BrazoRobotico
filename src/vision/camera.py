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

    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self.cap: Optional[cv2.VideoCapture] = None
        self.camera_ready = False

        # Configuraciones por defecto
        self.default_width = 640
        self.default_height = 360
        self.default_fps = 30

    def camera_on(self) -> bool:
        """Enciende la cámara con configuración optimizada"""
        try:
            self.__release_camera()

            # Usar DirectShow en Windows para mejor performance
            self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)

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
            self.cap.set(cv2.CAP_PROP_FPS, self.default_fps)
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

    def auto_gamma_correction(self, img, mid_gray=0.6):
        """
        Versión que intenta aplicar la corrección gamma usando UMat (OpenCL) cuando sea posible.
        Si no hay OpenCL disponible, cae a la versión CPU (numpy).
        Recibe BGR uint8 y devuelve BGR uint8.
        """

        if img is None:
            return img

        # Intentar versión con UMat/OpenCL
        try:
            # Subir a UMat (posible ejecución en OpenCL)
            u = cv2.UMat(img)

            # Convertir a gris para calcular intensidad media
            u_gray = cv2.cvtColor(u, cv2.COLOR_BGR2GRAY)  # UMat
            mean_val = cv2.mean(u_gray)[0]  # retorna (mean, ...)
            mean_intensity = float(mean_val) / 255.0

            if mean_intensity == 0:
                # Evitar división por cero, devolver original
                return img.astype(np.uint8)

            gamma = math.log(mid_gray) / math.log(mean_intensity)

            # Si gamma cercano a 1 o mayor que un umbral, no aplicar para ahorrar tiempo
            if gamma >= 0.6:
                return img.astype(np.uint8)

            # Normalizar a 0-1 en float
            u_norm = cv2.normalize(
                u, None, 0.0, 1.0, cv2.NORM_MINMAX, cv2.CV_32F)

            # Aplicar potencia en GPU
            u_pow = cv2.pow(u_norm, gamma)

            # Escalar a 0-255 y convertir a uint8
            u_out = cv2.convertScaleAbs(u_pow, alpha=255.0)

            return u_out.get()

        except Exception as e:
            print(f"Fallo al aplicar cambio de gamma con OpenCL: {e}")
            # Fallback CPU (como en tu versión original)
            try:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                mean_intensity = np.mean(gray) / 255.0
                if not mean_intensity:
                    return img.astype(np.uint8)
                else:
                    gamma = math.log(mid_gray) / math.log(mean_intensity)
                if gamma >= 0.6:
                    return img.astype(np.uint8)
                gamma_corrected_img = np.power(img / 255.0, gamma) * 255.0
                gamma_corrected_img = np.clip(
                    gamma_corrected_img, 0, 255).astype(np.uint8)
                return gamma_corrected_img
            except Exception as ee:
                # si todo falla, devolver original
                print(f"Error al aplicar correccion de gamma por CPU: {ee}")
                return img.astype(np.uint8)
