""" En este modulo se define el menu que se integrara a la barra de titulo y como se comporta.
"""
import os
from PyQt6.QtGui import QAction, QKeySequence, QIcon, QPixmap, QActionGroup
from PyQt6.QtWidgets import QMenuBar, QSizePolicy, QLabel, QStatusBar
from PyQt6.QtCore import Qt
from serial.tools import list_ports
from robot.openbotv_worker import RobotWorker
from data import DataFlow
from data import config_manager as cfg


class MainMenuMixin:
    """ Mixin encargado de definir el menu, las acciones que hará y su comportamiento con estas
    """

    def __init__(self):
        self.robot_controller = None
        self.openbotv = None

    def create_main_actions(self):
        """ Define las acciones que tendrá el menu asi como sus atajos, texto de la barra de estado
            e iconos utilizados como botones.
        """
        settings = cfg.get("settings.json")

        # Mapeamos el submenu para el menu vista
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
                            "Mostrar/Ocultar controles con sliders", False),
                "kinematics": ("kinematics_action", "Cinemática",
                               "Cinemática", "Ctrl+s",
                               "Mostrar/Ocultar controles de cinematica", False),
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
            "mode": {
                "simulation": ("simulation_action", "Activar Simulación",
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

        theme = cfg.get("settings.json", "theme")
        if theme.lower() == "dark":
            self.theme_action = QAction(self.sun_icon, "", self)
        elif theme.lower() == "light":
            self.theme_action = QAction(self.moon_icon, "", self)
        self.theme_action.setShortcut(QKeySequence("Ctrl+t"))
        self.theme_action.setStatusTip("Cambiar tema")

        self.connect_action = QAction("Conectar", self)
        self.connect_action.setEnabled(False)

        # self.com_select_action = QAction()

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
        self.camera_menu.addAction(self.charuco_action)
        self.camera_menu.addAction(self.sphere_action)
        self.camera_menu.addAction(self.camera_calibration_action)

        self.mode_menu = self.menu_bar.addMenu("&Modo")
        self.mode_menu.addAction(self.sliders_action)

        self.simulation_menu = self.menu_bar.addMenu("&Simulación")
        self.simulation_menu.addAction(self.simulation_action)

        self.robot_menu = self.menu_bar.addMenu("&Robot")
        self.com_submenu = self.robot_menu.addMenu("&Puerto")
        self.com_group = QActionGroup(self)
        self.com_group.setExclusive(True)
        self.get_com_ports()
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
            self.com_connected_label.setText("No conectado")

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
        status_bar.addPermanentWidget(self.com_connected_label)
        self.setStatusBar(status_bar)
