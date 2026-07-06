"""
Módulo de control de la cámara para captura de video.

Proporciona CameraControl, que gestiona la apertura, configuración,
captura y liberación de la cámara. Optimizado para uso con OpenCL (UMat)
y aceleracion por hardware en Windows (D3D11).

Conexiones:
    - Utiliza config_manager para cargar la configuración de resolución,
      FPS y datos de calibración de la cámara seleccionada.
"""

import os
import sys
from cv2.typing import NumPyArrayNumeric
import numpy as np
from typing import Any, Optional
import cv2

os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"

try:
    cv2.ocl.setUseOpenCL(True)
except cv2.error:
    # OpenCL no disponible en este sistema — continuar sin aceleración GPU
    pass


class CameraConnection:
    """Gestiona una cámara y sus operaciones básicas de captura.

    Optimizada para usar UMat (OpenCL) en preprocesado. Configura
    la cámara con la resolución, FPS y aceleración por hardware
        especificados en la configuración.

    Args:
        camera_index (int): Índice de la cámara a utilizar.
        camera_config (dict): Configuración con resolución, matriz
            y coeficientes de distorsion.
        is_calibration (bool): Si True, la cámara se usa para calibración.
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
        """Enciende la cámara con configuración optimizada.

        Selecciona la API de captura según la plataforma (DShow en
        Windows, V4L2 en Linux) y configura resolucion, FPS y
        aceleracion por hardware.

        Returns:
            bool: True si la cámara se inicializó correctamente.
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
            print(f"[DEBUG] IOError al inicializar cámara (índice {self.camera_index}): {e}")
            self.__release_camera()
            return False
        except RuntimeError as e:
            print(f"[DEBUG] RuntimeError al inicializar cámara (índice {self.camera_index}): {e}")
            self.__release_camera()
            return False

    def camera_off(self):
        """Apaga la cámara y libera los recursos asociados."""
        self.camera_ready = False
        self.__release_camera()
        cv2.destroyAllWindows()

    def camera_is_on(self):
        """Verifica si la cámara está activa y operativa.

        Returns:
            bool: True si la cámara está abierta y lista para capturar.
        """
        return self.cap is not None and self.cap.isOpened() and self.camera_ready

    def take_frame(self) -> None | cv2.typing.MatLike:
        """Captura un frame de la cámara en formato BGR.

        Returns:
            np.ndarray or None: Frame capturado o None si falla.
        """
        if not self.camera_ready or not self.cap:
            return None
        ret, frame = self.cap.read()
        if ret:
            return frame
        return None

    def __release_camera(self) -> None:
        """Libera los recursos de la cámara de forma segura."""
        if self.cap:
            try:
                self.cap.release()
            except (cv2.error, OSError):
                # Error al liberar cámara — ignorar en cierre
                pass
            self.cap = None
