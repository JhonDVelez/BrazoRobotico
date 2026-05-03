""" En este modulo se define el menu que se integrara a la barra de titulo y como se comporta.
"""
import os
import subprocess
import sys
from collections import Counter
from PyQt6.QtGui import QAction, QKeySequence, QIcon, QPixmap, QActionGroup
from PyQt6.QtWidgets import QMenuBar, QSizePolicy, QLabel, QStatusBar, QFrame
from PyQt6.QtCore import Qt
from serial.tools import list_ports
from robot.openbotv_worker import RobotWorker
from data import DataFlow, FrameCounter
from data import config_manager as cfg
import cv2
from cv2_enumerate_cameras import enumerate_cameras
from .main_theme_mixin import ThemeManager


class MainMenuMixin:
    """ Mixin encargado de definir el menu, las acciones que hará y su comportamiento con estas
    """

    def __init__(self):
        self.robot_controller = None
        self.openbotv = None
        self.last_cameras = None
        self.last_com = None
        self.last_camera_name = None

    def create_main_actions(self):
        """ Define las acciones que tendrá el menu asi como sus atajos, texto de la barra de estado
            e iconos utilizados como botones.
        """
        # Carga del archivo de configuraciones
        settings = cfg.get("settings.json")

        # Se define un formato de diccionario para crear las acciones del menu
        # primary_key, secondary_key, (attr_name, label_show, label_hide, shortcut, status, is_checkable)
        mapping_mode = {
            "mode": {
                "sliders": ("sliders_action", "Sliders",
                            "Sliders", "Ctrl+a",
                            "Mostrar/Ocultar controles con sliders", True),
                "kinematics": ("kinematics_action", "Cinemática",
                               "Cinemática", "Ctrl+s",
                               "Mostrar/Ocultar controles de cinematica", True),
            }
        }

        mapping_camera = {
            "camera": {
                "charuco": ("charuco_action", "Tablero ChArUco", "Tablero ChArUco",
                            "Ctrl+q", "Activa/Desactiva la deteccion del tablero", True),
                "sphere": ("sphere_action", "Activar Objetos", "Activar Objetos",
                           "Ctrl+w", "Activa/Desactiva la deteccion de las esferas de colores", True),
                "calibrate": ("camera_calibration_action", "Calibrar Cámara", "Calibrar Cámara",
                              "", "Abrir ventana de calibracion de cámara", False),
            }
        }

        mapping_simulation = {
            "simulation": {
                "activated": ("simulation_action", "Activar Simulación",
                              "Activar Simulación", "Ctrl+y",
                              "Activar/Desactivar simulación", True),
            }
        }

        # Crea una tupla para iterar las distintas acciones
        mapping_all = (mapping_mode, mapping_camera, mapping_simulation)

        for mapping in mapping_all:
            # Obtiene la llave principal y el diccionario que contiene
            for main_key, creation_data in mapping.items():
                # Carga los datos guardados con la llave principal
                saved_config = settings.get(main_key)
                # Obtiene los datos de creación
                for key, (attr_name, label_show, label_hide, shortcut, status, is_checkable) in creation_data.items():
                    action = None
                    if key in saved_config:
                        # Define el label basado en la configuración guardada
                        if saved_config.get(key):
                            action = QAction(label_hide, self)
                        else:
                            action = QAction(label_show, self)
                        action.setChecked(saved_config.get(key))
                    else:
                        # Si no se tiene el dato guardado en el json se usa el label por defecto
                        action = QAction(label_hide, self)
                    if action is not None:
                        # Si la accion fue creada se configura el comportamiento y el status
                        # de la barra de estado
                        action.setCheckable(is_checkable)
                        action.setShortcut(QKeySequence(shortcut))
                        action.setStatusTip(status)
                        # Se crea el objeto en esta clase usando self, el nombre del atributo y la
                        # acción creada
                        setattr(self, attr_name, action)

        self.sun_icon = QIcon(os.path.join("icons:sun.png"))
        self.moon_icon = QIcon(os.path.join("icons:moon.png"))

        self.theme_action = QAction("", self)
        self.theme_action.setShortcut(QKeySequence("Ctrl+t"))
        self.theme_action.setStatusTip("Cambiar tema")

        self.connect_action = QAction("Conectar", self)
        self.connect_action.setEnabled(False)

        self.theme_manager = ThemeManager().get_instance()
        self.theme_manager.theme_changed.connect(self.change_theme)

    def create_main_menu(self):
        """ Define la estructura del menu y submenus basado en las acciones definidas.
        """
        self.create_main_actions()
        self.menu_bar = QMenuBar()
        self.menu_bar.setFixedHeight(32)
        self.menu_bar.setContentsMargins(0, 0, 0, 0)
        self.menu_bar.adjustSize()

        # Logo en la equina izquierda
        self.logo_label = QLabel()
        self.laser_w = QPixmap("img:laser_w.png").scaledToHeight(
            20, Qt.TransformationMode.SmoothTransformation)
        self.laser_b = QPixmap("img:laser_b.png").scaledToHeight(
            20, Qt.TransformationMode.SmoothTransformation)
        self.logo_label.setPixmap(self.laser_w)
        self.logo_label.setContentsMargins(8, 0, 5, 0)

        self.menu_bar.setCornerWidget(self.logo_label, Qt.Corner.TopLeftCorner)

        self.camera_menu = self.menu_bar.addMenu("&Cámara")
        self.cameras_submenu = self.camera_menu.addMenu(
            "&Entradas de video")
        self.cameras_group = QActionGroup(self)
        self.cameras_group.setExclusive(True)
        self.camera_menu.addAction(self.charuco_action)
        self.camera_menu.addAction(self.sphere_action)
        self.camera_menu.addAction(self.camera_calibration_action)

        self.camera_interval_submenu = self.camera_menu.addMenu(
            "&Intervalo")
        self.camera_interval_group = QActionGroup(self)
        self.camera_interval_group.setExclusive(True)
        presets_interval = [1, 2, 4, 10]
        pre_interval = cfg.get("settings.json", "camera", "view", "interval")
        for preset in presets_interval:
            action = self.camera_interval_submenu.addAction(f"{preset}")
            action.setCheckable(True)
            self.camera_interval_group.addAction(action)
            if preset == pre_interval:
                action.setChecked(True)
            action.triggered.connect(
                lambda checked, i=preset: self.interval_selection_change(i))
        self.camera_interval_submenu.setEnabled(False)

        self.mode_menu = self.menu_bar.addMenu("&Modo")
        self.mode_menu.addAction(self.sliders_action)
        self.mode_menu.addAction(self.kinematics_action)

        self.simulation_menu = self.menu_bar.addMenu("&Simulación")
        self.simulation_menu.addAction(self.simulation_action)

        self.robot_menu = self.menu_bar.addMenu("&Robot")
        self.com_submenu = self.robot_menu.addMenu("&Puerto")
        self.com_group = QActionGroup(self)
        self.com_group.setExclusive(True)
        self.get_com_ports()
        self.get_cameras()
        self.robot_menu.addAction(self.connect_action)

        self.menu_bar.setSizePolicy(
            QSizePolicy(QSizePolicy.Policy.Preferred,
                        QSizePolicy.Policy.Preferred)
        )

    def get_com_ports(self):
        """ Escanea el sistema en busca de puertos de comunicación serial y los expone como un
            submenu para que el usuario seleccione el puerto del microcontrolador del robot
        """
        available_ports = list_ports.comports()
        available_com = [(port.device, port.description)
                         for port in available_ports]

        if self.last_com is not None and Counter(self.last_com) == Counter(available_com):
            return

        self.last_com = available_com

        # limpiar menú y grupo
        self.com_submenu.clear()
        for action in list(self.com_group.actions()):
            self.com_group.removeAction(action)

        if available_ports:
            if self.stopped:
                self.com_submenu.setEnabled(False)
            else:
                self.com_submenu.setEnabled(True)
            # Agrega los puertos seriales disponibles al submenu
            for port in available_ports:
                com_action = self.com_submenu.addAction(port.description)
                com_action.setCheckable(True)
                # Define el dato que se envía con la señal de qt
                com_action.setData(port.device)
                com_action.setStatusTip(f"Conectar al puerto {port.device}")
                self.com_group.addAction(com_action)
                com_action.triggered.connect(self.com_checkable_change)

                if self.com == port.device:
                    com_action.setChecked(True)
        else:
            self.connect_action.setEnabled(False)
            self.com_submenu.setEnabled(False)
            self.com = None
            self._stop_threads()
            self.com_connected_label.setText("Micro no conectado")

    def com_checkable_change(self, checked):
        """ Detecta cuando se selecciona un puerto de comunicación serial COM y en caso de que este
            seleccionado uno previamente detiene la conexión
            Si el controlador y el hilo de proceso del robot no están inicializados se activa la
            opción de realizar la conexión con ese puerto.

        Args:
            checked (bool): permite saber si al menos un puerto mostrado en la interfaz esta
                            seleccionado
        """
        action = self.sender()
        if not self.com:
            self._stop_threads()
        if action and checked:  # Solo cuando queda seleccionado
            self.com = action.data()
            if (not getattr(self, "openbotv", None) and
                not getattr(self, "robot_controller", None) and
                    not self.stopped):
                self.connect_action.setEnabled(True)

    def _read_sysfs_value(self, path):
        try:
            with open(path, encoding='utf-8', errors='replace') as f:
                return f.readline().strip()
        except OSError:
            return None

    def _get_udev_camera_name(self, sysfs_device_path):
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

    def _is_host_controller_name(self, product_name, manufacturer_name):
        if not product_name and not manufacturer_name:
            return False
        if product_name and 'Host Controller' in product_name:
            return True
        if manufacturer_name and manufacturer_name.startswith('Linux ') and 'xhci' in manufacturer_name.lower():
            return True
        return False

    def _get_camera_product_name(self, camera_path):
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

    def _get_camera_display_name(self, cam):
        if cam.name and "UVC Camera" not in cam.name:
            return cam.name

        product_name = self._get_camera_product_name(cam.path)
        if product_name:
            return product_name

        if cam.vid is not None and cam.pid is not None:
            return f"{cam.name} ({cam.vid:04X}:{cam.pid:04X})"

        return cam.name

    def _get_camera_sysfs_device(self, cam):
        device_name = os.path.basename(cam.path) if cam.path else None
        if not device_name:
            return None
        video_device_path = os.path.join(
            '/sys/class/video4linux', device_name, 'device')
        if not os.path.exists(video_device_path):
            return None
        return os.path.realpath(video_device_path)

    def _get_unique_camera_menu_name(self, cam, existing_names):
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

    def get_cameras(self):
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

        if self.last_cameras is not None and Counter(self.last_cameras) == Counter(camera_names) and self.cameras_submenu.actions():
            return

        self.last_cameras = camera_names

        self.cameras_submenu.clear()
        for action in list(self.cameras_submenu.actions()):
            self.cameras_submenu.removeAction(action)

        if unique_cameras:
            self.cameras_submenu.setEnabled(True)
            for cam, display_name in zip(unique_cameras, camera_names):
                cam_action = self.cameras_submenu.addAction(display_name)
                cam_action.setCheckable(True)
                cam_action.setData([cam.index, display_name])
                cam_action.setStatusTip(f"Conectar a camara {display_name}")
                self.cameras_group.addAction(cam_action)
                cam_action.triggered.connect(self.camera_checkable_change)

                if self.last_camera_name == display_name:
                    cam_action.setChecked(True)
        else:
            self.cameras_submenu.setEnabled(False)
            interface = getattr(self, 'camera_interface', None) or getattr(
                self, 'calibration_interface', None)
            if interface:
                interface.stop_video()

        if not self.cameras_group.checkedAction():
            interface = getattr(self, 'camera_interface', None) or getattr(
                self, 'calibration_interface', None)
            if interface:
                interface.set_camera_index(None)

    def camera_checkable_change(self, checked):
        action = self.sender()
        if action and checked:
            interface = getattr(self, 'camera_interface', None) or getattr(
                self, 'calibration_interface', None)
            if interface:
                interface.set_camera_index(action.data()[0])
            self.last_camera_name = action.data()[1]

    def clear_camera_selection(self):
        self.last_camera_name = None
        for action in self.cameras_group.actions():
            action.setChecked(False)

        interface = getattr(self, 'camera_interface', None) or getattr(
            self, 'calibration_interface', None)
        if interface:
            interface.stop_video()
            interface.set_camera_index(None)

    def interval_selection_change(self, interval):
        FrameCounter().get_instance().set_interval(interval)

    def _stop_threads(self):
        """ Detiene y elimina los hilos activos de forma segura
        """
        if getattr(self, "robot_controller", None):
            try:
                if isinstance(self.robot_controller, DataFlow):
                    self.robot_controller.exit()
                    self.robot_controller.wait()
                    self.robot_controller.deleteLater()
            except RuntimeError:
                pass
            finally:
                self.robot_controller = None

        if getattr(self, "openbotv", None):
            try:
                if isinstance(self.openbotv, RobotWorker):
                    self.openbotv.exit()
                    self.openbotv.wait()
                    self.openbotv.deleteLater()
            except RuntimeError:
                pass
            finally:
                self.openbotv = None

    def create_status_bar(self):
        """ Crea la barra de estado y conecta la visualization del estado de conexión del puerto
            serial
        """
        status_bar = QStatusBar(self)
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        status_bar.addPermanentWidget(self.camera_connected_label)
        status_bar.addPermanentWidget(separator)
        status_bar.addPermanentWidget(self.com_connected_label)
        self.setStatusBar(status_bar)

    def change_theme(self, dark_t: bool):
        if dark_t:
            self.theme_action.setIcon(self.sun_icon)
        else:
            self.theme_action.setIcon(self.moon_icon)
