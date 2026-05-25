"""
Modulo que define la ventana independiente para la calibracion de color.

Este modulo contiene la clase ColorWindow, la cual proporciona un entorno
frameless dedicado para ajustar los parametros de vision (HSV), integrando
la arquitectura de controladores y servicios de la aplicacion.
"""

import os
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt6.QtCore import QCoreApplication, Qt
from PyQt6.QtGui import QIcon
from qframelesswindow import FramelessMainWindow
from src.main_window.mixins import MainTitleBarMixin
from src.services.styling import ThemeManager
from src.services.data.signals import ThemeSignalManager
from src.features.color.mixins import ColorMenuMixin
from src.features.color.color_controller import ColorController
from src.services.devices import CameraDevices
from src.services.devices.device_monitor import get_device_monitor


class ColorWindow(FramelessMainWindow, ColorMenuMixin):
    """
    Ventana para la calibracion de colores HSV.

    Mantiene la paridad visual y estructural con el resto de la suite de
    calibracion, delegando la logica de negocio al ColorController.
    """

    def __init__(self):
        """
        Inicializa la ventana de color y sus servicios asociados.
        """
        super().__init__()
        self.setWindowTitle("Calibración De Colores")

        # 1. Managers y Atributos de estilo
        self._theme_signal_manager = ThemeSignalManager.get_instance()
        self.sun_icon = QIcon(os.path.join("icons:sun.png"))
        self.moon_icon = QIcon(os.path.join("icons:moon.png"))

        # 2. Configuracion de la UI Base
        self.__setup_base_ui()

        # 3. Inicializar Controlador (Arquitectura W-W-C)
        self._controller = ColorController(self)
        self._main_layout.addWidget(self._controller.get_widget())

        # 4. Inicializacion de Servicios y Conexiones
        self.__setup_services()
        self.__setup_connections()

    def __setup_base_ui(self):
        """
        Configura los contenedores, menus y barra de titulo de la ventana.
        """
        self._root_container = QWidget()
        self._root_layout = QVBoxLayout(self._root_container)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(0)

        # Menus y Barra de Titulo personalizada
        self.create_calibration_menu()
        self.create_status_bar()
        self.title_bar = MainTitleBarMixin(self, "Calibración De Colores")
        self.setTitleBar(self.title_bar)
        self._root_layout.addWidget(self.title_bar)

        # Area de contenido central para el controlador
        self._central_content = QWidget()
        self._main_layout = QVBoxLayout(self._central_content)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.addWidget(self._central_content)

        self.setCentralWidget(self._root_container)

        # Dimensionamiento relativo a la pantalla
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        self.resize(int(screen_geometry.width() * 0.75), int(screen_geometry.height() * 0.75))
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)

    def __setup_services(self):
        """
        Inicializa los servicios de tema y monitoreo de dispositivos.
        """
        self.theme_manager = ThemeManager(self)
        self.theme_manager._load_current_theme()

        self._camera_devices = CameraDevices()
        self._device_monitor = get_device_monitor(
            camera_callback=self._camera_devices.get_cameras, camera_only=True)
        self._device_monitor.install_filter(QCoreApplication.instance())
        self._camera_devices.get_cameras()

    def __setup_connections(self):
        """
        Establece las conexiones para el cambio de tema y eventos de UI.
        """
        if hasattr(self, 'theme_action'):
            self.theme_action.triggered.connect(self.theme_manager.toggle_theme_event)
        self._theme_signal_manager.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, is_dark: bool):
        """
        Slot para manejar la actualizacion sincronizada del tema.

        Args:
            is_dark (bool): True si el tema es oscuro.
        """
        self.theme_manager._apply_theme_from_signal(is_dark)

    def closeEvent(self, event):
        """
        Limpia recursos y desinstala filtros de eventos al cerrar.

        Args:
            event (QCloseEvent): Evento de cierre de Qt.
        """
        self._controller.cleanup()
        if hasattr(self, "_device_monitor"):
            self._device_monitor.uninstall_filter()
        event.accept()

    # Getters explicitos
    def get_controller(self):
        """
        Retorna el controlador asociado a la ventana.

        Returns:
            ColorController: Instancia del controlador.
        """
        return self._controller
