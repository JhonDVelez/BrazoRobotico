"""
Modulo para la deteccion y enumeracion de camaras conectadas.

Proporciona la clase CameraDevices que descubre las camaras disponibles
en el sistema utilizando la libreria cv2-enumerate-cameras, con soporte
multiplataforma para Windows y Linux.
"""

import os
import subprocess
import sys
import cv2
from cv2_enumerate_cameras import enumerate_cameras
from src.services.data.signals import CameraSignalManager


class CameraDevices:
    """
    Descubridor de camaras conectadas al sistema.

    Proporciona metodos para enumerar, filtrar y obtener nombres
    descriptivos de las camaras disponibles en la plataforma actual.
    """

    def get_cameras(self):
        """
        Escanea las camaras disponibles y emite la lista via CameraSignalManager.

        Filtra camaras duplicadas y genera nombres unicos para cada
        dispositivo detectado.
        """
        if sys.platform == "win32":
            available_cameras = enumerate_cameras(cv2.CAP_DSHOW)
        elif sys.platform == "linux":
            available_cameras = enumerate_cameras(cv2.CAP_V4L2)
        else:
            available_cameras = enumerate_cameras()

        unique_cameras = []
        seen_devices = set()
        for cam in available_cameras:
            sysfs_device = self._get_camera_sysfs_device(cam)
            unique_key = sysfs_device or cam.path or str(cam.index)
            if unique_key in seen_devices:
                continue
            seen_devices.add(unique_key)
            unique_cameras.append(cam)

        camera_names = []
        used_names = set()
        for cam in unique_cameras:
            camera_names.append(
                self._get_unique_camera_menu_name(cam, used_names))

        results = [
            (cam.index, display_name)
            for cam, display_name in zip(unique_cameras, camera_names)
        ]
        CameraSignalManager.get_instance().available_cameras.emit(results)

    def _get_camera_sysfs_device(self, cam):
        """
        Obtiene la ruta sysfs real del dispositivo de video.

        Args:
            cam: Objeto de camara de cv2-enumerate-cameras.

        Returns:
            str or None: Ruta real del dispositivo en /sys/class/video4linux.
        """
        device_name = os.path.basename(cam.path) if cam.path else None
        if not device_name:
            return None
        video_device_path = os.path.join(
            '/sys/class/video4linux', device_name, 'device')
        if not os.path.exists(video_device_path):
            return None
        return os.path.realpath(video_device_path)

    def _get_unique_camera_menu_name(self, cam, existing_names):
        """
        Genera un nombre unico para mostrar en el menu de seleccion.

        Args:
            cam: Objeto de camara.
            existing_names (set): Nombres ya utilizados.

        Returns:
            str: Nombre unico para el menu.
        """
        display_name = self._get_camera_display_name(cam)
        if display_name in existing_names:
            suffix = os.path.basename(cam.path) if cam.path else str(cam.index)
            if suffix:
                display_name = f"{display_name} ({suffix})"
            else:
                display_name = f"{display_name} ({cam.index})"
            index = 1
            while display_name in existing_names:
                display_name = f"{self._get_camera_display_name(cam)} ({suffix}#{index})"
                index += 1
        existing_names.add(display_name)
        return display_name

    def _get_camera_display_name(self, cam):
        """
        Obtiene el nombre descriptivo de una camara.

        Args:
            cam: Objeto de camara.

        Returns:
            str: Nombre descriptivo.
        """
        if cam.name and "UVC Camera" not in cam.name:
            return cam.name

        product_name = self._get_camera_product_name(cam.path)
        if product_name:
            return product_name

        if cam.vid is not None and cam.pid is not None:
            return f"{cam.name} ({cam.vid:04X}:{cam.pid:04X})"

        return cam.name

    def _get_camera_product_name(self, camera_path):
        """
        Obtiene el nombre del producto desde sysfs.

        Args:
            camera_path (str): Ruta del dispositivo en /dev/.

        Returns:
            str or None: Nombre del producto del fabricante.
        """
        device_name = os.path.basename(camera_path)
        video_device_path = os.path.join(
            '/sys/class/video4linux', device_name, 'device')
        if not os.path.exists(video_device_path):
            return None

        udev_name = self._get_udev_camera_name(video_device_path)
        if udev_name:
            return udev_name

        current_path = os.path.realpath(video_device_path)
        while current_path and current_path.startswith('/sys'):
            product = self._read_sysfs_value(
                os.path.join(current_path, 'product'))
            manufacturer = self._read_sysfs_value(
                os.path.join(current_path, 'manufacturer'))
            if product and not self._is_host_controller_name(product, manufacturer):
                if manufacturer and manufacturer not in product:
                    return f"{manufacturer} {product}"
                return product
            parent_path = os.path.dirname(current_path)
            if parent_path == current_path:
                break
            current_path = parent_path
        return None

    def _get_udev_camera_name(self, sysfs_device_path):
        """
        Obtiene el nombre de la camara desde udev.

        Args:
            sysfs_device_path (str): Ruta sysfs del dispositivo.

        Returns:
            str or None: Nombre del modelo desde la base de datos de udev.
        """
        try:
            result = subprocess.run(
                ['udevadm', 'info', '-q', 'property', '-p', sysfs_device_path],
                text=True,
                capture_output=True,
                check=False,
            )
        except FileNotFoundError:
            return None

        if result.returncode != 0:
            return None

        vendor = None
        model = None
        for line in result.stdout.splitlines():
            if line.startswith('ID_MODEL_FROM_DATABASE='):
                model = line.split('=', 1)[1].strip()
            elif line.startswith('ID_MODEL=') and model is None:
                model = line.split('=', 1)[1].strip()
            elif line.startswith('ID_VENDOR_FROM_DATABASE='):
                vendor = line.split('=', 1)[1].strip()
            elif line.startswith('ID_VENDOR=') and vendor is None:
                vendor = line.split('=', 1)[1].strip()

        if model:
            if vendor and vendor not in model:
                return f"{vendor} {model}"
            return model
        return None

    def _read_sysfs_value(self, path):
        """
        Lee un valor desde un archivo sysfs.

        Args:
            path (str): Ruta completa al archivo sysfs.

        Returns:
            str or None: Contenido del archivo o None si falla.
        """
        try:
            with open(path, encoding='utf-8', errors='replace') as f:
                return f.readline().strip()
        except OSError:
            return None

    def _is_host_controller_name(self, product_name, manufacturer_name):
        """
        Verifica si el nombre corresponde a un controlador host (no a una camara).

        Args:
            product_name (str): Nombre del producto.
            manufacturer_name (str): Nombre del fabricante.

        Returns:
            bool: True si es un controlador host.
        """
        if not product_name and not manufacturer_name:
            return False
        if product_name and 'Host Controller' in product_name:
            return True
        if manufacturer_name and manufacturer_name.startswith('Linux ') and 'xhci' in manufacturer_name.lower():
            return True
        return False
