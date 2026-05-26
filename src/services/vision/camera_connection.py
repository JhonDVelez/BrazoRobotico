"""
Modulo de control de la camara para captura de video.

Proporciona CameraControl, que gestiona la apertura, configuracion,
captura y liberacion de la camara. Optimizado para uso con OpenCL (UMat)
y aceleracion por hardware en Windows (D3D11).

Conexiones:
    - Utiliza config_manager para cargar la configuracion de resolucion,
      FPS y datos de calibracion de la camara seleccionada.
"""

import os
import sys
import numpy as np
from typing import Optional
import cv2

os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"

try:
    cv2.ocl.setUseOpenCL(True)
except Exception:
    pass


class CameraConnection:
    """Gestiona una camara y sus operaciones basicas de captura.

    Optimizada para usar UMat (OpenCL) en preprocesado. Configura
    la camara con la resolucion, FPS y aceleracion por hardware
    especificados en la configuracion.

    Args:
        camera_index (int): Indice de la camara a utilizar.
        camera_config (dict): Configuracion con resolucion, matriz
            y coeficientes de distorsion.
        is_calibration (bool): Si True, la camara se usa para calibracion.
    """

    def __init__(self, camera_index: int = 0, camera_config: dict = None, is_calibration: bool = False):
        super().__init__()
        self.cap: Optional[cv2.VideoCapture] = None
        self.camera_ready = False

        self.default_width = camera_config.get("resolution")["width"]
        self.default_height = camera_config.get("resolution")["height"]
        self.default_fps = camera_config.get("resolution")["fps"]
        self.camera_matrix = np.array(camera_config.get("matrix"))
        self.dist_coeff = np.array(
            camera_config.get("distortion coefficients"))

        self.is_calibration = is_calibration
        self.camera_index = camera_index

    def camera_on(self) -> bool:
        """Enciende la camara con configuracion optimizada.

        Selecciona la API de captura segun la plataforma (DShow en
        Windows, V4L2 en Linux) y configura resolucion, FPS y
        aceleracion por hardware.

        Returns:
            bool: True si la camara se inicializo correctamente.
        """
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

            elif sys.platform == "linux":
                self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_V4L2)

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
        """Apaga la camara y libera los recursos asociados."""
        self.camera_ready = False
        self.__release_camera()
        cv2.destroyAllWindows()

    def camera_is_on(self):
        """Verifica si la camara esta activa y operativa.

        Returns:
            bool: True si la camara esta abierta y lista para capturar.
        """
        return self.cap is not None and self.cap.isOpened() and self.camera_ready

    def take_frame(self):
        """Captura un frame de la camara en formato BGR.

        Returns:
            np.ndarray or None: Frame capturado o None si falla.
        """
        if not self.camera_ready or not self.cap:
            return None
        ret, frame = self.cap.read()
        if ret:
            return frame
        return None

    def __release_camera(self):
        """Libera los recursos de la camara de forma segura."""
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None

    def apply_division_trick(self, img):
        """Aplica el 'truco de la division' para eliminar sombras.

        Divide la imagen por una version muy borrosa de si misma,
        eliminando zonas oscuras de sombras y conservando solo los
        bordes de alto contraste.

        Args:
            img: Imagen de entrada en BGR.

        Returns:
            Imagen procesada sin sombras.
        """
        smooth = cv2.GaussianBlur(img, (95, 95), 0)
        return cv2.divide(img, smooth, scale=255)
