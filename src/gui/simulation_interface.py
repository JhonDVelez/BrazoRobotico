import os
from data import Units, Modes, Domains, DataFlow
from simulation import PhysicsWorker
from gui.main_window.image_utils_mixin import ImageUtilsMixin
from gui.main_window.main_theme_mixin import ThemeManager
from gui.simulation_worker import SimWorker
from PyQt6.QtGui import QPixmap
from PyQt6.QtQuick import QQuickView
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QVBoxLayout, QLabel, QSizePolicy


class SimInterface(ImageUtilsMixin):
    """ Clase encargada de gestionar el modelo 3D del robot. 
        Utiliza un contenedor precargado para una transición instantánea sin esperas de carga.
    """

    def __init__(self, parent, preloaded_container, robot_id):
        super().__init__()
        # Almacenamiento de recursos precargados y referencias
        self.preloaded_container = preloaded_container  # Objeto que contiene la vista QML ya lista
        self.robot_id = robot_id
        self.parent = parent
        self.sim_worker = None      # Hilo para actualizar la posición de las piezas 3D
        self.process_running = False
        self.quick_view = None      # La vista de QtQuick (motor de renderizado 3D)
        self.window_container = None # El widget de Qt que envuelve la vista 3D

        # Verificación y extracción de los componentes del contenedor precargado
        if preloaded_container and preloaded_container.is_ready:
            self.quick_view = preloaded_container.quick_view
            self.window_container = preloaded_container.window_container
        else:
            print("Warning: No hay contenedor precargado disponible")

        # --- CONFIGURACIÓN DEL LAYOUT ---
        # Si no existe un layout previo, se crea uno vertical para organizar la imagen y el 3D
        if not self.layout():
            self.v_layout = QVBoxLayout(self)
            self.v_layout.setContentsMargins(0, 0, 0, 0)
            self.setLayout(self.v_layout)

        # Política de expansión para ocupar todo el espacio disponible en la interfaz
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)
        self.setMinimumSize(160, 120)

        # 1. Configurar la imagen estática (Placeholder) que se ve antes de dar "Play"
        self.__setup_static_image()

        # 2. Integrar los componentes 3D precargados en este widget
        self.__integrate_preloaded_container()
        
        # 3. Configurar el motor de física y el flujo de datos
        self.__setup_controller()

    def __setup_static_image(self):
        """ Configura la imagen estática que se muestra cuando la simulación está apagada.
            Carga diferentes versiones (clara/oscura) según el tema del sistema.
        """
        self.image_path_r = os.path.join(os.path.dirname(
            __file__), "img", 'robotArm_r.png')
            
        self.image_path_b = os.path.join(os.path.dirname(
            __file__), "img", 'robotArm_b.png')
            
        self.pixmap = QPixmap(self.image_path_r)
        
        # Etiqueta para contener la imagen con alineación centrada
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.image_label.setMinimumSize(160, 120)
        
        self.layout().addWidget(self.image_label)
        self.load_image() # Método heredado de ImageUtilsMixin
        
        # Suscripción al cambio de tema global
        self.theme_manager = ThemeManager.get_instance()
        self.theme_manager.theme_changed.connect(self.toggle_theme)

    def __integrate_preloaded_container(self):
        """ Realiza el 'transplante' del contenedor 3D precargado hacia este widget.
            Ajusta las banderas de ventana para que se comporte como un widget hijo.
        """
        try:
            # Transferir el parentesco del widget contenedor a esta clase (SimInterface)
            self.window_container.setParent(self)

            self.window_container.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Expanding
            )
            self.window_container.setMinimumSize(160, 120)

            # Insertar el contenedor 3D en el layout principal
            self.layout().addWidget(self.window_container)

            # Se mantiene oculto hasta que el usuario inicie la simulación
            self.window_container.hide()

            # Configuración técnica de la vista QtQuick para integrarla sin bordes
            if self.quick_view:
                self.quick_view.setFlags(
                    Qt.WindowType.Widget | Qt.WindowType.FramelessWindowHint
                )
                self.quick_view.setResizeMode(
                    QQuickView.ResizeMode.SizeRootObjectToView)
            else:
                print("Error de configuracion de vista")

            # Inicializar el 'SimWorker': El hilo que comunica la lógica con el modelo QML 3D
            root_object = self.quick_view.rootObject() # El nodo raíz del archivo .qml
            if root_object:
                self.sim_worker = SimWorker(root_object, self.robot_id)
                self.sim_worker.start() # El hilo queda a la espera de datos
            else:
                print("Error de inicializacion del worker")

        except Exception as e:
            print(f"Error integrando contenedor precargado: {e}")

    def __setup_controller(self):
        """ Inicializa el motor de física y el controlador de flujo de datos (DataFlow).
        """
        # El PhysicsWorker calcula trayectorias y colisiones
        self.physics_worker = PhysicsWorker(self.robot_id)
        self.physics_worker.set_max_velocity(1.2) # Límite de velocidad angular

        # El DataFlow orquesta el origen de los datos (Sliders, Teclado, etc.)
        self.controller = DataFlow(
            Modes.SLIDERS, Units.RAD, Domains.SIMULATION)
        self.controller.start()

    def start_simulation(self):
        """ Activa la visualización 3D, oculta el placeholder e inicia los motores de física.
        """
        if not self.window_container or not self.quick_view:
            print("Error: Contenedor precargado no disponible")
            return

        try:
            # Intercambio visual: Imagen fuera, Modelo 3D dentro
            self.image_label.hide()
            self.window_container.show()
            self.quick_view.show()
            self.quick_view.update()

            # Asegurar que el hilo de actualización 3D esté corriendo
            if self.sim_worker:
                if not self.sim_worker.isRunning():
                    self.sim_worker.start()

            # Iniciar el cálculo de físicas
            self.physics_worker.start()

            self.process_running = True
        except Exception as e:
            print(f"Error iniciando simulación: {e}")

    def pause_simulation(self):
        """ Pausa el cálculo de físicas pero mantiene la vista 3D visible.
        """
        if self.physics_worker:
            self.physics_worker.pause()

    def stop_simulation(self):
        """ Detiene la simulación por completo y restaura la imagen estática.
        """
        self.process_running = False

        if self.sim_worker:
            self.physics_worker.stop()

        # Ocultar el renderizado 3D
        if self.window_container:
            self.window_container.hide()
        if self.quick_view:
            self.quick_view.hide()

        # Mostrar de nuevo la imagen estática
        self.image_label.show()

    def closeEvent(self, event):
        """ Gestión de limpieza de memoria y detención de hilos al cerrar el widget.
            Es crucial para evitar que el motor 3D quede colgado en memoria.
        """
        if self.process_running:
            self.stop_simulation()
            
        if self.sim_worker:
            try:
                self.sim_worker.stop_simulation()
                if self.sim_worker.isRunning():
                    self.sim_worker.quit()
                    self.sim_worker.wait(2000) # Espera de seguridad de 2 segundos
            except Exception as e:
                print(f"Error cerrando worker: {e}")
            self.sim_worker = None

        # Limpieza de referencias para ayudar al recolector de basura
        self.window_container = None
        self.quick_view = None
        self.preloaded_container = None

        super().closeEvent(event)