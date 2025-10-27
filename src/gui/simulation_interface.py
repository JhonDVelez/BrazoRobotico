import os
from PyQt6.QtWidgets import QVBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import Qt
from PyQt6.QtQuick import QQuickView
from PyQt6.QtGui import QPixmap
from gui.simulation_worker import SimWorker
from gui.main_window.main_theme_mixin import ThemeManager
from gui.main_window.image_utils_mixin import ImageUtilsMixin
from simulation import PhysicsWorker
from data import Units, Modes, Domains, DataFlow


class SimInterface(ImageUtilsMixin):
    """ Clase encargada del modelo 3d usando contenedor completamente precargado
    """

    def __init__(self, parent, preloaded_container, robot_id):
        super().__init__()
        self.preloaded_container = preloaded_container  # Contenedor completo precargado
        self.robot_id = robot_id
        self.parent = parent
        self.sim_worker = None
        self.process_running = False
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
        self.__setup_static_image()

        # Integrar contenedor precargado
        self.__integrate_preloaded_container()

        self.__setup_controller()

    def __setup_static_image(self):
        """Configura la imagen estática que se muestra cuando no hay simulación"""
        self.image_path_r = os.path.join(os.path.dirname(
            __file__), "img", 'robotArm_r.png')
        self.image_path_b = os.path.join(os.path.dirname(
            __file__), "img", 'robotArm_b.png')
        self.pixmap = QPixmap(self.image_path_r)
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.image_label.setMinimumSize(160, 120)
        self.layout().addWidget(self.image_label)
        self.load_image()
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
                self.sim_worker = SimWorker(root_object, self.robot_id)
                self.sim_worker.start()

        except Exception as e:
            print(f"Error integrando contenedor precargado: {e}")

    def __setup_controller(self):
        self.physics_worker = PhysicsWorker(self.robot_id)
        self.physics_worker.set_max_velocity(1.2)

        self.controller = DataFlow(
            Modes.SLIDERS, Units.RAD, Domains.SIMULATION)
        self.controller.start()

    def start_simulation(self):
        """ Inicia la simulación con recursos ya precargados
        """
        if not self.window_container or not self.quick_view:
            print("Error: Contenedor precargado no disponible")
            return

        try:
            self.image_label.hide()
            self.window_container.show()
            self.quick_view.show()
            self.quick_view.update()

            if self.sim_worker:
                if not self.sim_worker.isRunning():
                    self.sim_worker.start()

            self.physics_worker.start()

            self.process_running = True
        except Exception as e:
            print(f"Error iniciando simulación: {e}")

    def pause_simulation(self):
        """ Pausa la simulación
        """
        if self.physics_worker:
            self.physics_worker.pause()

    def stop_simulation(self):
        """ Para la simulación
        """
        self.process_running = False

        if self.sim_worker:
            self.physics_worker.stop()

        if self.window_container:
            self.window_container.hide()
        if self.quick_view:
            self.quick_view.hide()

        self.image_label.show()

    def closeEvent(self, event):
        """ Limpieza al cerrar
        """
        if self.process_running:
            self.stop_simulation()
        if self.sim_worker:
            try:
                self.sim_worker.stop_simulation()
                if self.sim_worker.isRunning():
                    self.sim_worker.quit()
                    self.sim_worker.wait(2000)
            except Exception as e:
                print(f"Error cerrando worker: {e}")
            self.sim_worker = None

        self.window_container = None
        self.quick_view = None
        self.preloaded_container = None

        super().closeEvent(event)
