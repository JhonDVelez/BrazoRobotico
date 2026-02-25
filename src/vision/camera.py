import sys
from typing import Optional
import math
import numpy as np
import cv2

# Intentar habilitar OpenCL (UMat) si está disponible en el hardware
# Esto permite que OpenCV ejecute ciertos algoritmos en la GPU automáticamente
try:
    cv2.ocl.setUseOpenCL(True)
except Exception:
    pass


class CameraControl:
    """ Clase que gestiona una cámara y sus operaciones básicas.
        Optimizada para usar UMat (OpenCL) en el preprocesado de imágenes,
        lo que mejora la velocidad en dispositivos con GPU compatible.
    """

    def __init__(self):
        self.cap: Optional[cv2.VideoCapture] = None # Objeto de captura de video
        self.camera_ready = False                  # Estado de disponibilidad de la cámara

        # Configuraciones de resolución y tasa de refresco por defecto
        self.default_width = 640
        self.default_height = 360
        self.default_fps = 30

    def camera_on(self) -> bool:
        """ Enciende la cámara con una configuración optimizada según el sistema operativo. """
        try:
            # Asegura que no haya una instancia previa abierta antes de intentar encenderla
            self.__release_camera()

            # --- OPTIMIZACIÓN POR PLATAFORMA ---
            # En Windows se usa CAP_DSHOW para una inicialización más rápida
            if sys.platform == "win32":
                self.cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
                if not self.cap or not self.cap.isOpened():
                    self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            
            # En Linux se usa CAP_V4L2 (Video for Linux 2) que es el estándar de drivers
            elif sys.platform == "linux":
                self.cap = cv2.VideoCapture(1, cv2.CAP_V4L2)
                if not self.cap or not self.cap.isOpened():
                    # Si falla el índice 1 (cámara externa), intenta con el 0 (integrada)
                    self.cap = cv2.VideoCapture(0, cv2.CAP_V4L2)

            # Verificación final de que el flujo de video se abrió correctamente
            if not self.cap or not self.cap.isOpened():
                raise IOError("No se pudo abrir la cámara")

            # Nota: La configuración de parámetros está comentada para priorizar la estabilidad del driver
            # self.__configure_camera()

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
        """ Apaga la cámara, libera los recursos del sistema y cierra ventanas de OpenCV. """
        self.camera_ready = False
        self.__release_camera()
        cv2.destroyAllWindows()

    def camera_is_on(self):
        """ Verifica si el objeto de captura existe y el flujo está activo. """
        return self.cap is not None and self.cap.isOpened() and self.camera_ready

    def take_frame(self):
        """ Captura un cuadro (frame) actual de la cámara en formato BGR. """
        if not self.camera_ready or not self.cap:
            return None

        # Lee el frame del buffer de la cámara
        ret, frame = self.cap.read()
        if ret:
            # Opción comentada: Redimensionar para reducir carga computacional si es necesario
            # frame = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_LINEAR)
            return frame  # Retorna el array de NumPy con la imagen
        return None

    def __configure_camera(self):
        """ Método privado para forzar resolución y FPS en el hardware. """
        if not self.cap:
            return
        try:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.default_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.default_height)
            self.cap.set(cv2.CAP_PROP_FPS, self.default_fps)
        except Exception:
            pass

    def __release_camera(self):
        """ Método privado para liberar el puerto de la cámara de forma segura. """
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None

    def toggle_camera(self):
        """ Cambia el estado actual de la cámara (Encendido <-> Apagado). """
        if self.camera_is_on():
            self.camera_off()
        else:
            self.camera_on()

    def auto_gamma_correction(self, img, mid_gray=0.6):
        """
        Ajusta el brillo de la imagen dinámicamente según la iluminación del entorno.
        Implementa una doble vía:
        1. Vía acelerada (OpenCL): Usa UMat para procesar en la GPU.
        2. Vía de respaldo (CPU): Usa NumPy si falla la aceleración.
        """

        if img is None:
            return img

        # --- INTENTO DE PROCESAMIENTO EN GPU (OpenCL) ---
        try:
            # Convierte la imagen a UMat para subirla a la memoria de la GPU
            u = cv2.UMat(img)

            # Calcula la intensidad media para determinar si la imagen está oscura o clara
            u_gray = cv2.cvtColor(u, cv2.COLOR_BGR2GRAY)
            mean_val = cv2.mean(u_gray)[0]
            mean_intensity = float(mean_val) / 255.0

            if mean_intensity == 0:
                return img.astype(np.uint8)

            # Calcula el factor Gamma necesario (Relación logarítmica)
            gamma = math.log(mid_gray) / math.log(mean_intensity)

            # Si la iluminación ya es aceptable (gamma >= 0.6), no se procesa para ahorrar energía
            if gamma >= 0.6:
                return img.astype(np.uint8)

            # Normalización y aplicación de la función de potencia (Gamma) en GPU
            u_norm = cv2.normalize(u, None, 0.0, 1.0, cv2.NORM_MINMAX, cv2.CV_32F)
            u_pow = cv2.pow(u_norm, gamma)

            # Regresa los valores al rango 0-255 y los descarga de la GPU
            u_out = cv2.convertScaleAbs(u_pow, alpha=255.0)
            return u_out.get()

        except Exception as e:
            # --- RESPALDO EN CPU (Fallback) ---
            # Se ejecuta si el hardware no soporta OpenCL o hay un error de drivers
            print(f"Fallo al aplicar cambio de gamma con OpenCL: {e}")
            try:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                mean_intensity = np.mean(gray) / 255.0
                if not mean_intensity:
                    return img.astype(np.uint8)
                else:
                    gamma = math.log(mid_gray) / math.log(mean_intensity)
                
                if gamma >= 0.6:
                    return img.astype(np.uint8)
                
                # Cálculo matemático manual usando NumPy
                gamma_corrected_img = np.power(img / 255.0, gamma) * 255.0
                gamma_corrected_img = np.clip(gamma_corrected_img, 0, 255).astype(np.uint8)
                return gamma_corrected_img
            except Exception as ee:
                print(f"Error al aplicar correccion de gamma por CPU: {ee}")
                return img.astype(np.uint8)