import os
from PyQt6.QtWidgets import QVBoxLayout, QWidget, QLabel, QSizePolicy
from PyQt6.QtCore import QUrl, Qt, QSize
from PyQt6.QtQuickWidgets import QQuickWidget
from PyQt6.QtQuick import QQuickView
from PyQt6.QtGui import QResizeEvent, QPixmap
from gui.simulation_worker import SimWorker
from gui.main_window.main_theme import ThemeManager


class SimInterface(QWidget):
    """ Clase encargada del modelo 3d mostrado en la interfaz usando QQuickView
    """

    def __init__(self, parent, data, robot_id):
        super().__init__()
        self.quick_view = data
        self.robot_id = robot_id
        self.parent = parent
        self.window_container = None
        self.physics_worker = None
        self.simulation_running = False

        if not self.layout():
            self.v_layout = QVBoxLayout(self)
            self.v_layout.setContentsMargins(0, 0, 0, 0)
            self.setLayout(self.v_layout)

        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)
        self.setMinimumSize(160, 120)

        # Configurar la imagen estática
        self._setup_static_image()

        # Inicializar QQuickView
        self.__init_quick_view()

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

    def __init_quick_view(self):
        """Inicializa QQuickView"""
        try:
            # Configurar como widget sin marco
            self.quick_view.setFlags(
                Qt.WindowType.Widget | Qt.WindowType.FramelessWindowHint)

            # Inicializar worker si hay contenido
            root_object = self.quick_view.rootObject()
            if root_object:
                self.physics_worker = SimWorker(root_object, self.robot_id)
                self.physics_worker.start()

            if not self.window_container:
                self.window_container = self.createWindowContainer(
                    self.quick_view,
                    self,
                    Qt.WindowType.Widget
                )

                if self.window_container:
                    self.window_container.setSizePolicy(
                        QSizePolicy.Policy.Expanding,
                        QSizePolicy.Policy.Expanding
                    )
                    self.window_container.setMinimumSize(160, 120)
                    self.layout().addWidget(self.window_container)
            self.window_container.hide()

        except Exception as e:
            print(f"Error al inicializar QQuickView: {e}")
            self.quick_view = None

    def start_simulation(self):
        """Inicia la simulación"""
        if not self.quick_view:
            print("Error: QQuickView no disponible")
            return

        try:
            # Mostrar simulación
            self.label.hide()
            if self.window_container:
                self.window_container.show()
            self.quick_view.show()

            # Iniciar worker
            if self.physics_worker:
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

        if self.label.isVisible() and hasattr(self, 'pixmap'):
            self.set_label_pixmap(self.pixmap)

    def closeEvent(self, event):
        """Limpieza al cerrar"""
        if self.simulation_running:
            self.stop_simulation()

        if self.physics_worker:
            try:
                self.physics_worker.exit()
                self.physics_worker.wait(3000)
            except:
                pass
            self.physics_worker = None

        if self.window_container:
            self.window_container.setParent(None)
            self.window_container = None

        if self.quick_view:
            self.quick_view.close()
            self.quick_view = None

        super().closeEvent(event)

    def createWindowContainer(self, window, parent=None, flags=Qt.WindowType.Widget):
        """Crea contenedor de ventana"""
        try:
            from PyQt6.QtWidgets import QWidget
            if hasattr(QWidget, 'createWindowContainer'):
                return QWidget.createWindowContainer(window, parent, flags)
            else:
                # Fallback
                container = QWidget(parent)
                window.setParent(container.winId())
                return container
        except Exception as e:
            print(f"Error creando contenedor: {e}")
            return None

    def toggle_theme(self, dark_t):
        """ Alterna el estado de la captura de video.
        """
        if dark_t:
            self.pixmap = QPixmap(self.image_path_r)
        else:
            self.pixmap = QPixmap(self.image_path_b)
        self.set_label_pixmap(self.pixmap)
