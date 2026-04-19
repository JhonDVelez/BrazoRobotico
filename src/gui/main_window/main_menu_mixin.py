""" En este modulo se define el menu que se integrara a la barra de titulo y como se comporta.
"""
import os
from collections import Counter
from PyQt6.QtGui import QAction, QKeySequence, QIcon, QPixmap, QActionGroup
from PyQt6.QtWidgets import QMenuBar, QSizePolicy, QLabel, QStatusBar, QFrame
from PyQt6.QtCore import Qt
from serial.tools import list_ports
from robot.openbotv_worker import RobotWorker
from data import DataFlow, FrameCounter
from data import config_manager as cfg
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
        settings = cfg.get("settings.json")

        # Mapeamos el submenu para el menu vista
        # id_key, json_key, (attr_name, label_show, label_hide, shortcut, status, is_checkable)
        mapping_vista = {
            "content":
            {
                "camera": ("camera_action", "Cámara", "Cámara",
                           "Ctrl+h", "Mostrar/Ocultar la cámara", True),
                "model": ("model_action", "Simulación", "Simulación",
                          "Ctrl+j", "Mostrar/Ocultar el modelo 3D de la simulación", True),
                "graphs": ("graphs_action", "Gráficas", "Gráficas",
                           "Ctrl+k", "Mostrar/Ocultar las gráficas", True),
                "controls": ("controls_action", "Controles", "Controles",
                             "Ctrl+l", "Mostrar/Ocultar los controles", True),
            }
        }

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

        mapping_all = (mapping_vista, mapping_mode,
                       mapping_camera, mapping_simulation)

        for mapping in mapping_all:
            for main_key, (creation_data) in mapping.items():
                saved_config = settings.get(main_key)
                for key, (attr_name, label_show, label_hide, shortcut, status, is_checkable) in creation_data.items():
                    action = None
                    if key in saved_config:
                        if saved_config.get(key):
                            action = QAction(label_hide, self)
                        else:
                            action = QAction(label_show, self)
                        action.setChecked(saved_config.get(key))
                    else:
                        action = QAction(label_hide, self)
                    if action is not None:
                        action.setCheckable(is_checkable)
                        action.setShortcut(QKeySequence(shortcut))
                        action.setStatusTip(status)
                        setattr(self, attr_name, action)

        self.sun_icon = QIcon(os.path.join(
            os.path.dirname(__file__), "..", "icons", "sun.png"))
        self.moon_icon = QIcon(os.path.join(
            os.path.dirname(__file__), "..", "icons", "moon.png"))

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
        self.laser_w = QPixmap(os.path.join(
            os.path.dirname(__file__), "..",
            "img", "laser_w.png")).scaledToHeight(20, Qt.TransformationMode.SmoothTransformation)
        self.laser_b = QPixmap(os.path.join(
            os.path.dirname(__file__), "..",
            "img", "laser_b.png")).scaledToHeight(20, Qt.TransformationMode.SmoothTransformation)
        self.logo_label.setPixmap(self.laser_w)
        self.logo_label.setContentsMargins(8, 0, 5, 0)

        self.menu_bar.setCornerWidget(self.logo_label, Qt.Corner.TopLeftCorner)

        # Menús normales
        self.vista_menu = self.menu_bar.addMenu("&Vista")
        self.vista_menu.addAction(self.camera_action)
        self.vista_menu.addAction(self.model_action)
        self.vista_menu.addAction(self.graphs_action)
        self.vista_menu.addAction(self.controls_action)

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

    def get_cameras(self):
        available_cameras = enumerate_cameras(apiPreference=1400)
        available_cams = [(cam.name)
                          for cam in available_cameras]

        if self.last_cameras is not None and Counter(self.last_cameras) == Counter(available_cams) and self.cameras_submenu.actions():
            return

        self.last_cameras = available_cams

        self.cameras_submenu.clear()
        for action in list(self.cameras_submenu.actions()):
            self.cameras_submenu.removeAction(action)

        if available_cameras:
            self.cameras_submenu.setEnabled(True)
            for cam in available_cameras:
                cam_action = self.cameras_submenu.addAction(cam.name)
                cam_action.setCheckable(True)
                cam_action.setData([cam.index, cam.name])
                cam_action.setStatusTip(f"Conectar a camara {cam.name}")
                self.cameras_group.addAction(cam_action)
                cam_action.triggered.connect(self.camera_checkable_change)

                if self.last_camera_name == cam.name:
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
