from typing import Optional
import math
import numpy as np
import cv2


class CameraControl:
    """Clase que gestiona una cámara y sus operaciones básicas"""

    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self.cap: Optional[cv2.VideoCapture] = None
        self.camera_ready = False

        # Configuraciones por defecto
        self.default_width = 1280
        self.default_height = 720
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
            print(f"Error durate ejecucion: {e}")
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
        """Captura un frame de la cámara"""
        if not self.camera_ready or not self.cap:
            return None

        ret, frame = self.cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # Convertir a RGB
            return frame
        return None

    def __configure_camera(self):
        """Configura propiedades de la cámara para optimizar performance"""
        if not self.cap:
            return

    def __release_camera(self):
        """Libera recursos de la cámara"""
        if self.cap:
            self.cap.release()
            self.cap = None

    def toggle_camera(self):
        """Alterna el estado de la cámara"""
        if self.camera_is_on():
            self.camera_off()
        else:
            self.camera_on()

    @staticmethod
    def auto_gamma_correction(img, mid_gray=0.5):
        """
        Performs automatic gamma correction on an image.

        Args:
            image_path (str): Path to the input image.
            mid_gray (float): Desired mid-gray value (0.0 to 1.0).

        Returns:
            numpy.ndarray: The gamma-corrected image.
        """

        # Convert to grayscale for mean intensity calculation
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Calculate mean intensity (normalized to 0-1 range)
        mean_intensity = np.mean(gray) / 255.0

        # Calculate gamma
        if mean_intensity > 0:  # Avoid division by zero
            gamma = math.log(mid_gray) / math.log(mean_intensity)
        else:
            gamma = 1.0  # Default to no correction if mean is zero

        # Apply gamma correction
        # Normalize image to 0-1, apply power, then scale back to 0-255
        gamma_corrected_img = np.power(img / 255.0, gamma) * 255.0
        gamma_corrected_img = np.clip(
            gamma_corrected_img, 0, 255).astype(np.uint8)

        return gamma_corrected_img
