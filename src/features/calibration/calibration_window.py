"""
Modulo que define la ventana principal independiente para la calibracion.

Este modulo contiene la clase CameraCalibrationWindow, la cual proporciona un
entorno dedicado (ventana sin bordes) para ejecutar el proceso de calibracion
de camaras, integrando menus, barra de titulo personalizada y servicios de tema.
"""

import os
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt6.QtCore import QCoreApplication, Qt
from PyQt6.QtGui import QIcon
from qframelesswindow import FramelessMainWindow
from src.services.data.signals import ThemeSignalManager
from src.services.styling import ThemeManager
from src.main_window.mixins.main_title_bar_mixin import MainTitleBarMixin
from src.features.calibration.mixins import CalibrationMenuMixin
from src.features.calibration.calibration_controller import CalibrationController
from src.services.devices.device_monitor import get_device_monitor
from src.services.devices import CameraDevices


class CameraCalibrationWindow(FramelessMainWindow, CalibrationMenuMixin):
    """
    Ventana independiente para la calibracion de la camara.

    Actua como contenedor principal para el CalibrationController y gestiona
    los servicios especificos de la ventana como el monitoreo de hardware
    y la persistencia del tema visual.
    """

    def __init__(self):
        """
        Inicializa la ventana de calibracion y sus servicios base.
        """
        super().__init__()
        self.setWindowTitle("Calibración De Cámara")

        # 1. Inicializar managers y atributos base
        self._theme_signal_manager = ThemeSignalManager.get_instance()
        self.sun_icon = QIcon(os.path.join("icons:sun.png"))
        self.moon_icon = QIcon(os.path.join("icons:moon.png"))

        # 2. Configurar estructura base de la ventana
        self.__setup_base_ui()

        # 3. Inicializar Controlador (Nueva Arquitectura)
        self._controller = CalibrationController(self)
        self._main_layout.addWidget(self._controller.get_widget())

        # 4. Configurar temas y monitores
        self.__setup_services()
        self.__setup_connections()

    def __setup_base_ui(self):
        """
        Configura los contenedores principales y la estetica de la ventana frameless.
        """
        self._root_container = QWidget()
        self._root_layout = QVBoxLayout(self._root_container)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(0)

        # Menus y Barra de Titulo personalizada
        self.create_calibration_menu()
        self.create_status_bar()
        self.title_bar = MainTitleBarMixin(self, "Calibración De La Cámara")
        self.setTitleBar(self.title_bar)
        self._root_layout.addWidget(self.title_bar)

        # Area de contenido central
        self._central_content = QWidget()
        self._main_layout = QVBoxLayout(self._central_content)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.addWidget(self._central_content)

        self.setCentralWidget(self._root_container)

        # Dimensiones adaptativas y posicionamiento centralizado
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        self.resize(int(screen_geometry.width()*0.66), int(screen_geometry.height()*0.66))
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)

    def __setup_services(self):
        """
        Inicializa servicios globales de tema y monitoreo de hardware camara.
        """
        self.theme_manager = ThemeManager(self)
        self.theme_manager._load_current_theme()

        self._camera_devices = CameraDevices()
        self._device_monitor = get_device_monitor(
            camera_callback=self._camera_devices.get_cameras,
            camera_only=True
        )
        self._device_monitor.install_filter(QCoreApplication.instance())
        self._camera_devices.get_cameras()

    def __setup_connections(self):
        """
        Establece las conexiones de eventos reactivos de la ventana.
        """
        if hasattr(self, 'theme_action'):
            self.theme_action.triggered.connect(self.theme_manager.toggle_theme_event)

        self._theme_signal_manager.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, is_dark: bool):
        """
        Maneja el cambio de tema visual sincronizado.

        Args:
            is_dark (bool): True si el tema es oscuro.
        """
        self.theme_manager._apply_theme_from_signal(is_dark)

    def closeEvent(self, event):
        """
        Gestiona la limpieza de recursos y detencion de monitores al cerrar.

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
        Retorna el controlador de calibracion de la ventana.

        Returns:
            CalibrationController: Instancia del controlador.
        """
        return self._controller
