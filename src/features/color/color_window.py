from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt6.QtCore import QCoreApplication, Qt
from PyQt6.QtGui import QIcon
import os
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
    Ventana para la calibración de colores HSV.
    Mantiene la paridad visual y estructural original pero delegando a la arquitectura W-W-C.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Calibración De Colores")

        # 1. Managers y Atributos
        self._theme_signal_manager = ThemeSignalManager.get_instance()
        self.sun_icon = QIcon(os.path.join("icons:sun.png"))
        self.moon_icon = QIcon(os.path.join("icons:moon.png"))

        # 2. UI Base
        self.__setup_base_ui()
        
        # 3. Inicializar Controlador
        self._controller = ColorController(self)
        self._main_layout.addWidget(self._controller.get_widget())

        # 4. Servicios
        self.__setup_services()
        self.__setup_connections()

    def __setup_base_ui(self):
        self._root_container = QWidget()
        self._root_layout = QVBoxLayout(self._root_container)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(0)

        # Menús y Barra de Título
        self.create_calibration_menu()
        self.create_status_bar()
        self.title_bar = MainTitleBarMixin(self, "Calibración De Colores")
        self.setTitleBar(self.title_bar)
        self._root_layout.addWidget(self.title_bar)

        # Área Central
        self._central_content = QWidget()
        self._main_layout = QVBoxLayout(self._central_content)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.addWidget(self._central_content)

        self.setCentralWidget(self._root_container)

        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        self.resize(int(screen_geometry.width() * 0.75), int(screen_geometry.height() * 0.75))
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)

    def __setup_services(self):
        self.theme_manager = ThemeManager(self)
        self.theme_manager._load_current_theme()

        self._camera_devices = CameraDevices()
        self._device_monitor = get_device_monitor(
            camera_callback=self._camera_devices.get_cameras, camera_only=True)
        self._device_monitor.install_filter(QCoreApplication.instance())
        self._camera_devices.get_cameras()

    def __setup_connections(self):
        if hasattr(self, 'theme_action'):
            self.theme_action.triggered.connect(self.theme_manager.toggle_theme_event)
        self._theme_signal_manager.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, is_dark: bool):
        self.theme_manager._apply_theme_from_signal(is_dark)

    def closeEvent(self, event):
        self._controller.cleanup()
        if hasattr(self, "_device_monitor"):
            self._device_monitor.uninstall_filter()
        event.accept()

    # Getters explícitos
    def get_controller(self):
        return self._controller
