from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtQuick import QQuickView
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QVBoxLayout, QLabel, QSizePolicy, QWidget
from src.services.ui.image_handler import ImageHandler


class SimulationWidget(QWidget):
    theme_needed = pyqtSignal(bool)

    def __init__(self, preloaded_container, pybullet_callback):
        super().__init__()
        self.preloaded_container = preloaded_container
        self.pybullet_callback = pybullet_callback
        self._root_object = None

        if preloaded_container and preloaded_container.is_ready:
            self.quick_view = preloaded_container.quick_view
            self.window_container = preloaded_container.window_container
        else:
            print("Warning: No hay contenedor precargado disponible")

        self.process_running = False

        # Configurar layout
        if not self.layout():
            self.v_layout = QVBoxLayout(self)
            self.v_layout.setContentsMargins(0, 0, 0, 0)
            self.setLayout(self.v_layout)

        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)
        self.setMinimumSize(160, 120)

        # Configurar imagen estática
        self.__setup_static_image()

        # Integrar contenedor pre-cargado
        self.__integrate_preloaded_container()

    def __setup_static_image(self):
        """Configura la imagen estática que se muestra cuando no hay simulación"""
        self.image_path_l = "img:robotArm_l.svg"
        self.image_path_d = "img:robotArm_d.svg"
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.image_label.setMinimumSize(160, 120)
        self.layout().addWidget(self.image_label)

        self.image_handler = ImageHandler(
            self.image_label, self.image_path_d, self.image_path_l
        )
        self.image_handler.set_static_image()

    def __integrate_preloaded_container(self):
        """Integra el contenedor completamente precargado en la interfaz"""
        try:
            if not self.quick_view:
                print("Error: No hay vista precargada")
                return

            self.window_container = QWidget.createWindowContainer(
                self.quick_view,
                self,
                Qt.WindowType.Widget
            )

            self.window_container.setParent(self)

            # Configurar políticas de tamaño
            self.window_container.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Expanding
            )
            self.window_container.setMinimumSize(160, 120)

            # Agregar al layout de SimInterface
            self.layout().addWidget(self.window_container)

            # Ocultar inicialmente
            self.window_container.hide()

            # Configurar vista para integración
            if self.quick_view:
                self.quick_view.setFlags(
                    Qt.WindowType.Widget | Qt.WindowType.FramelessWindowHint
                )
                self.quick_view.setResizeMode(
                    QQuickView.ResizeMode.SizeRootObjectToView)
            else:
                print("Error de configuracion de vista")

            # Inicializar worker de física
            self._root_object = self.quick_view.rootObject()
            if self._root_object:
                self.pybullet_callback(self._root_object)
            else:
                print("Error de inicializacion del worker")

        except Exception as e:
            print(f"Error integrando contenedor precargado: {e}")

    def get_simulation_widget(self):
        return self

    def image_show(self):
        self.image_label.show()

    def image_hide(self):
        self.image_label.hide()

    def container_show(self):
        self.window_container.show()

    def container_hide(self):
        self.window_container.hide()

    def quick_show(self):
        self.quick_view.show()

    def quick_hide(self):
        self.quick_view.hide()

    def quick_update(self):
        self.quick_view.update()

    def get_process_state(self):
        return self.process_running

    def set_static_image(self):
        self.image_handler.set_static_image()

    def set_process_state(self, state: bool):
        self.process_running = state
        self.image_handler.set_process_running(state)

    def change_theme(self, dark_t: bool):
        self.image_handler.update_theme(dark_t)
        self.theme_needed.emit(dark_t)
