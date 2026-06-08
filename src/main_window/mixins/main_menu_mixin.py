"""
Modulo que define el menu superior integrado en la barra de titulo.

Contiene el mixin MainMenuMixin, responsable de crear las acciones del menu,
la barra de menu con sus submenus (Camara, Modo, Simulacion, Robot) y la
barra de estado con indicadores de conexion.
"""

import os
from collections import Counter
from PyQt6.QtGui import QAction, QKeySequence, QIcon, QPixmap, QActionGroup
from PyQt6.QtWidgets import QMenuBar, QSizePolicy, QLabel, QStatusBar, QFrame, QInputDialog
from PyQt6.QtCore import Qt
from serial.tools import list_ports
from src.services.robot import RobotController
from src.services.data import DataController
from src.services.data.timers import FrameCounter
from src.services.data.signals import ThemeSignalManager, ConfigSignalManager


class MainMenuMixin:
    """
    Mixin encargado de definir el menu superior de la aplicacion.

    Gestiona la creacion de acciones, submenus de camara, modo de control,
    simulacion y puertos COM, asi como la barra de estado inferior.
    """

    def __init__(self):
        self.robot_controller = None
        self.robot_service = None
        self.last_cameras = None
        self.last_com = None
        self.last_camera_name = None

    def create_main_actions(self):
        """
        Define las acciones del menu con atajos, textos de estado e iconos.

        Lee la configuracion guardada en settings.json para inicializar
        el estado de las acciones checkables.
        """
        config_manager = ConfigSignalManager.get_instance()
        settings = config_manager.get_param("settings.json", default={})

        # nombre_menu, nombre_opcion, nombre_objeto, nombre_interfaz_1, nombre_interfaz_2, shortcut,
        # descripcion para barra de estado y si esta o no el dato almacenado en config_manager
        mapping_mode = {
            "mode": {
                "sliders": ("sliders_action", "Sliders",
                            "Sliders", "Ctrl+a",
                            "Mostrar/Ocultar controles con sliders", True),
                "kinematics": ("kinematics_action", "Cinemática",
                               "Cinemática", "Ctrl+s",
                               "Mostrar/Ocultar controles de cinematica", True),
                "pick_place": ("pick_place_action", "Pick and Place",
                               "Pick and Place", "Ctrl+d",
                               "Mostrar/Ocultar controles de pick and place", True),
            }
        }

        mapping_camera = {
            "camera": {
                "calibrate": ("camera_calibration_action", "Calibrar Cámara", "Calibrar Cámara",
                              "", "Abrir ventana de calibracion de cámara", False),
                "color_calibrate": ("color_calibration_action", "Calibrar Color", "Calibrar Color",
                                    "", "Abrir ventana de calibracion de colores", False),
            }
        }

        mapping_simulation = {
            "simulation": {
                "activated": ("simulation_action", "Activar Simulación",
                              "Activar Simulación", "Ctrl+y",
                              "Activar/Desactivar simulación", True),
                "shadows": ("shadows_action", "Sombras",
                            "Sombras", "Ctrl+h",
                            "Activar/Desactivar sombras en la escena", True),
                "grid": ("grid_action", "Malla Infinita",
                         "Malla Infinita", "Ctrl+g",
                         "Mostrar/Ocultar malla infinita", True),
                "axes": ("axes_action", "Ejes de Coordenadas",
                         "Ejes de Coordenadas", "Ctrl+j",
                         "Mostrar/Ocultar ejes de coordenadas", True),
                "labels": ("labels_action", "Etiquetas de Juntas",
                           "Etiquetas de Juntas", "Ctrl+k",
                           "Mostrar/Ocultar angulos de las articulaciones", True),
                "aa": ("aa_action", "Antialiasing (MSAA)",
                       "Antialiasing (MSAA)", "Ctrl+l",
                       "Activar/Desactivar suavizado de bordes", True),
            }
        }

        mapping_all = (mapping_mode, mapping_camera, mapping_simulation)

        for mapping in mapping_all:
            for main_key, creation_data in mapping.items():
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

        self.sun_icon = QIcon(os.path.join("icons:sun.png"))
        self.moon_icon = QIcon(os.path.join("icons:moon.png"))

        self.theme_action = QAction("", self)
        self.theme_action.setShortcut(QKeySequence("Ctrl+t"))
        self.theme_action.setStatusTip("Cambiar tema")

        self.connect_action = QAction("Conectar", self)
        self.connect_action.setEnabled(False)

        self.theme_signal_manager = ThemeSignalManager.get_instance()
        self.theme_signal_manager.theme_changed.connect(self.change_theme)

    def create_main_menu(self):
        """
        Define la estructura del menu y los submenus de la aplicacion.

        Crea la barra de menu con las secciones de Camara, Modo,
        Simulacion y Robot, integrando el logo de la aplicacion.
        """
        self.create_main_actions()
        self.menu_bar = QMenuBar()
        self.menu_bar.setFixedHeight(32)
        self.menu_bar.setContentsMargins(0, 0, 0, 0)
        self.menu_bar.adjustSize()

        self.logo_label = QLabel()
        self.laser_w = QPixmap("img:laser_w.png").scaledToHeight(
            20, Qt.TransformationMode.SmoothTransformation)
        self.laser_b = QPixmap("img:laser_b.png").scaledToHeight(
            20, Qt.TransformationMode.SmoothTransformation)
        self.logo_label.setPixmap(self.laser_w)
        self.logo_label.setContentsMargins(8, 0, 5, 0)

        self.menu_bar.setCornerWidget(self.logo_label, Qt.Corner.TopLeftCorner)

        self.camera_menu = self.menu_bar.addMenu("&Cámara")
        self.camera_menu.addAction(self.camera_calibration_action)

        self.sphere_menu = self.menu_bar.addMenu("&Esfera")
        self.sphere_menu.addAction(self.color_calibration_action)
        self.sphere_size_submenu = self.sphere_menu.addMenu("&Tamaño")
        self.sphere_size_group = QActionGroup(self)
        self.sphere_size_group.setExclusive(True)

        presets_size = [20.0, 30.0]
        current_size = ConfigSignalManager.get_instance().get_param(
            "camera.json", "sphere_radius", default=20.0)

        size_found = False
        for size in presets_size:
            action = self.sphere_size_submenu.addAction(f"{int(size)}mm")
            action.setCheckable(True)
            self.sphere_size_group.addAction(action)
            if abs(size - current_size) < 0.1:
                action.setChecked(True)
                size_found = True
            action.triggered.connect(
                lambda checked, s=size: self.sphere_size_selection_change(s))

        self.custom_size_action = self.sphere_size_submenu.addAction(
            "Personalizado...")
        self.custom_size_action.setCheckable(True)
        self.sphere_size_group.addAction(self.custom_size_action)
        if not size_found:
            self.custom_size_action.setChecked(True)
            self.custom_size_action.setText(
                f"Personalizado ({current_size}mm)")
        self.custom_size_action.triggered.connect(self.custom_sphere_size)

        self.camera_interval_submenu = self.camera_menu.addMenu(
            "&Intervalo")
        self.camera_interval_group = QActionGroup(self)
        self.camera_interval_group.setExclusive(True)
        presets_interval = [1, 2, 4, 10]

        pre_interval = ConfigSignalManager.get_instance().get_param(
            "settings.json", "camera", "view", "interval", default=4)

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
        self.mode_group = QActionGroup(self.mode_menu)
        self.mode_menu.addAction(self.sliders_action)
        self.mode_menu.addAction(self.kinematics_action)
        self.mode_menu.addAction(self.pick_place_action)
        self.mode_group.addAction(self.sliders_action)
        self.mode_group.addAction(self.kinematics_action)
        self.mode_group.addAction(self.pick_place_action)
        self.mode_group.setExclusive(True)

        self.simulation_menu = self.menu_bar.addMenu("&Simulación")
        self.simulation_menu.addAction(self.simulation_action)
        self.simulation_menu.addSeparator()
        self.simulation_menu.addAction(self.shadows_action)
        self.simulation_menu.addAction(self.aa_action)
        self.simulation_menu.addAction(self.grid_action)
        self.simulation_menu.addAction(self.axes_action)
        self.simulation_menu.addAction(self.labels_action)

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
        """
        Escanea los puertos serie disponibles y actualiza el submenu.

        Expone los puertos COM encontrados como acciones seleccionables
        en el submenu de Robot.
        """
        available_ports = list_ports.comports()
        available_com = [(port.device, port.description)
                         for port in available_ports]

        if self.last_com is not None and Counter(self.last_com) == Counter(available_com):
            return

        self.last_com = available_com

        self.com_submenu.clear()
        for action in list(self.com_group.actions()):
            self.com_group.removeAction(action)

        if available_ports:
            if self.stopped:
                self.com_submenu.setEnabled(False)
            else:
                self.com_submenu.setEnabled(True)
            for port in available_ports:
                com_action = self.com_submenu.addAction(port.description)
                com_action.setCheckable(True)
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
        """
        Maneja la seleccion de un puerto COM en el submenu.

        Si se selecciona un nuevo puerto, detiene la conexion anterior
        y habilita el boton de conectar.

        Args:
            checked (bool): Indica si la accion esta seleccionada.
        """
        action = self.sender()
        if not self.com:
            self._stop_threads()
        if action and checked:
            self.com = action.data()
            if (not getattr(self, "robot_service", None) and
                not getattr(self, "robot_controller", None) and
                    not self.stopped):
                self.connect_action.setEnabled(True)

    def interval_selection_change(self, interval):
        """
        Aplica el intervalo de captura de camara seleccionado.

        Args:
            interval (int): Nuevo intervalo en ticks de frame.
        """
        FrameCounter().get_instance().set_interval(interval)

    def sphere_size_selection_change(self, size):
        """
        Actualiza el radio de la esfera en la configuracion.

        Args:
            size (float): Nuevo radio en mm.
        """
        ConfigSignalManager.get_instance().request_change(
            "camera.json", "sphere_radius", value=float(size))
        self.custom_size_action.setText("Personalizado...")

    def custom_sphere_size(self):
        """
        Abre un dialogo para ingresar un tamaño de esfera personalizado.
        """
        current = ConfigSignalManager.get_instance().get_param(
            "camera.json", "sphere_radius", default=20.0)

        val, ok = QInputDialog.getDouble(
            self, "Tamaño de Esfera", "Radio en mm:",
            current, 1.0, 500.0, 1
        )

        if ok:
            self.sphere_size_selection_change(val)
            self.custom_size_action.setChecked(True)
            self.custom_size_action.setText(f"Personalizado ({val}mm)")
        else:
            # Re-check the previous action if cancelled
            # This is tricky because we don't know which one was checked.
            # But the QActionGroup should handle the exclusivity.
            # If we cancelled, we should probably restore the check on the current size.
            pass

    def _stop_threads(self):
        """
        Detiene y libera los hilos del robot de forma segura.
        """
        if getattr(self, "robot_controller", None):
            try:
                if hasattr(self.robot_controller, 'stop'):
                    self.robot_controller.stop()
                self.robot_controller.deleteLater()
            except RuntimeError:
                pass
            finally:
                self.robot_controller = None

        if getattr(self, "robot_service", None):
            try:
                self.robot_service.stop_service()
                self.robot_service.deleteLater()
            except RuntimeError:
                pass
            finally:
                self.robot_service = None

    def create_status_bar(self):
        """
        Crea la barra de estado con indicadores de conexion de camara y COM.
        """
        status_bar = QStatusBar(self)
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        status_bar.addPermanentWidget(self.camera_connected_label)
        status_bar.addPermanentWidget(separator)
        status_bar.addPermanentWidget(self.com_connected_label)
        self.setStatusBar(status_bar)

    def change_theme(self, dark_t: bool):
        """
        Actualiza el icono del boton de tema segun el modo actual.

        Args:
            dark_t (bool): True si el tema es oscuro.
        """
        if dark_t:
            self.theme_action.setIcon(self.sun_icon)
        else:
            self.theme_action.setIcon(self.moon_icon)
