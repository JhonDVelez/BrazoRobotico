import os
from PyQt6.QtWidgets import QVBoxLayout, QWidget, QLabel, QSizePolicy
from PyQt6.QtCore import QUrl, Qt, QSize
from PyQt6.QtQuickWidgets import QQuickWidget
from PyQt6.QtQuick import QQuickView
from PyQt6.QtGui import QResizeEvent, QPixmap
from gui.simulation_worker import SimWorker
from gui.main_window.main_theme import ThemeManager


class SimInterface(QWidget):
    """ Clase encargada del modelo 3d usando contenedor completamente precargado
    """

    def __init__(self, parent, preloaded_container, robot_id):
        super().__init__()
        self.preloaded_container = preloaded_container  # Contenedor completo precargado
        self.robot_id = robot_id
        self.parent = parent
        self.physics_worker = None
        self.simulation_running = False
        self.quick_view = None
        self.window_container = None

        if preloaded_container and preloaded_container.is_ready:
            self.quick_view = preloaded_container.quick_view
            self.window_container = preloaded_container.window_container
        else:
            print("Warning: No hay contenedor precargado disponible")

        # Configurar layout
        if not self.layout():
            self.v_layout = QVBoxLayout(self)
            self.v_layout.setContentsMargins(0, 0, 0, 0)
            self.setLayout(self.v_layout)

        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)
        self.setMinimumSize(160, 120)

        # Configurar imagen estática
        self._setup_static_image()

        # Integrar contenedor precargado
        self.__integrate_preloaded_container()

    def _setup_static_image(self):
        """Configura la imagen estática que se muestra cuando no hay simulación"""
        self.image_path_r = os.path.join(os.path.dirname(
            __file__), "img", 'robotArm_r.png')
        self.image_path_b = os.path.join(os.path.dirname(
            __file__), "img", 'robotArm_b.png')
        self.pixmap = QPixmap(self.image_path_r)
        self.label = QLabel()
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.label.setMinimumSize(160, 120)
        self.layout().addWidget(self.label)
        self.set_label_pixmap(self.pixmap)
        self.theme_manager = ThemeManager.get_instance()
        self.theme_manager.theme_changed.connect(self.toggle_theme)

    def __integrate_preloaded_container(self):
        """Integra el contenedor completamente precargado en la interfaz"""
        try:
            # Transferir parentesco del contenedor
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

            # Inicializar worker de física
            root_object = self.quick_view.rootObject()
            if root_object:
                self.physics_worker = SimWorker(root_object, self.robot_id)

        except Exception as e:
            print(f"Error integrando contenedor precargado: {e}")

    def start_simulation(self):
        """Inicia la simulación con recursos ya precargados - INSTANTÁNEO"""
        if not self.window_container or not self.quick_view:
            print("Error: Contenedor precargado no disponible")
            return

        try:
            self.label.hide()
            self.window_container.show()
            self.quick_view.show()
            self.quick_view.update()

            if self.physics_worker:
                if not self.physics_worker.isRunning():
                    self.physics_worker.start()
                self.physics_worker.start_simulation()

            self.simulation_running = True
        except Exception as e:
            print(f"Error iniciando simulación: {e}")

    def pause_simulation(self):
        """Pausa la simulación"""
        if self.physics_worker:
            self.physics_worker.pause_simulation()

    def stop_simulation(self):
        """Para la simulación"""
        self.simulation_running = False

        if self.physics_worker:
            self.physics_worker.stop_simulation()

        if self.window_container:
            self.window_container.hide()
        if self.quick_view:
            self.quick_view.hide()

        self.label.show()

    def set_label_pixmap(self, pixmap: QPixmap):
        """Establece el pixmap de la imagen estática"""
        if pixmap and not pixmap.isNull():
            label_size = self.label.size()
            if label_size.width() > 0 and label_size.height() > 0:
                if pixmap.size() != label_size:
                    scaled_pixmap = pixmap.scaled(
                        label_size,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.FastTransformation
                    )
                    self.label.setPixmap(scaled_pixmap)
                else:
                    self.label.setPixmap(pixmap)
            else:
                self.label.setPixmap(pixmap)
        else:
            self.label.clear()

    def resizeEvent(self, event: QResizeEvent):
        """Maneja el redimensionamiento"""
        super().resizeEvent(event)

        # Actualizar imagen estática
        if self.label.isVisible() and hasattr(self, 'pixmap'):
            self.set_label_pixmap(self.pixmap)

        # Actualizar vista 3D solo si está visible
        if (self.quick_view and self.window_container and
                self.window_container.isVisible()):
            self.quick_view.update()

    def closeEvent(self, event):
        """Limpieza al cerrar"""
        if self.simulation_running:
            self.stop_simulation()
        if self.physics_worker:
            try:
                self.physics_worker.stop_simulation()
                if self.physics_worker.isRunning():
                    self.physics_worker.quit()
                    self.physics_worker.wait(2000)
            except Exception as e:
                print(f"Error cerrando worker: {e}")
            self.physics_worker = None

        self.window_container = None
        self.quick_view = None
        self.preloaded_container = None

        super().closeEvent(event)

    def toggle_theme(self, dark_t):
        """ Alterna el tema de la imagen estática
        """
        if dark_t:
            self.pixmap = QPixmap(self.image_path_r)
        else:
            self.pixmap = QPixmap(self.image_path_b)
        self.set_label_pixmap(self.pixmap)
