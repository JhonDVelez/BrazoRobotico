"""
Modulo que controla el flujo de la simulacion 3D y la integracion de PyBullet.

Este modulo define la clase SimulationController, la cual orquesta la vista QML,
el worker de fisica y la sincronizacion de datos reactiva para el gemelo digital
del robot.

Conexiones:
    - Escucha `update_robot_signal` para mover el modelo 3D.
    - Gestiona el ciclo de vida de `PhysicsWorker` y `SimulationWorker`.
    - Sincroniza el tema visual con el fondo de la escena Quick3D.
"""

from PyQt6.QtCore import pyqtSlot, QObject
from src.services.data import DataController
from src.services.data.enums import Units, Modes, Domains
from src.services.simulation import PhysicsWorker
from src.services.styling.theme_manger import ThemeSignalManager
from src.services.data.signals import SimulationSignalManager
from src.features.simulation.simulation_worker import SimulationWorker
from src.features.simulation.simulation_widget import SimulationWidget


class SimulationController(QObject):
    """
    Controlador principal del feature de simulacion.

    Administra la integracion entre el motor de fisica (PyBullet) y la representacion
    grafica (QtQuick/QML), gestionando estados de inicio, pausa y parada.
    """

    def __init__(self, parent, preloaded_container, robot_id):
        """
        Inicializa el controlador de simulacion y configura el flujo de datos.

        Args:
            parent (QWidget): Widget padre.
            preloaded_container (PreloadedContainer): Contenedor con la escena QML cargada.
            robot_id (str): Identificador del robot.
        """
        super().__init__()
        self.robot_id = robot_id
        self.parent = parent
        self.simulation_worker = None
        self._root_object = None

        # Inicializar UI y Fisica
        self.simulation_widget = SimulationWidget(
            preloaded_container, self.init_pybullet_processing).get_simulation_widget()
        self.physics_worker = PhysicsWorker(self.robot_id)

        # Sincronizacion de temas
        self.theme_manager = ThemeSignalManager.get_instance()
        self.theme_manager.theme_changed.connect(self.change_theme)
        self.simulation_widget.theme_needed.connect(self._apply_root_theme)

        # Controlador de datos especifico para el dominio de simulacion
        self.controller = DataController(
            Modes.SLIDERS, Units.RAD, Domains.SIMULATION)

        # Conexiones de señales globales
        self.signal_manager = SimulationSignalManager.get_instance()
        self.signal_manager.update_robot_signal.connect(self.update_simulation)
        self.signal_manager.sphere_pos.connect(
            self.update_sphere_pose_simulation)

    def init_pybullet_processing(self, root_object):
        """
        Callback para inicializar el worker visual una vez cargado el objeto raiz QML.

        Args:
            root_object (QObject): Objeto raiz de la escena QML.
        """
        self._root_object = root_object
        self.simulation_worker = SimulationWorker(
            root_object, self.robot_id)
        self.simulation_worker.start()

    def _apply_root_theme(self, dark_t: bool):
        """
        Ajusta las propiedades de color de la escena 3D segun el tema actual.

        Args:
            dark_t (bool): True si el tema es oscuro.
        """
        if self._root_object is not None:
            if dark_t:
                self._root_object.setProperty("bgColor", "#191B20")
                self._root_object.setProperty("floorColor", "#E6E8ED")
            else:
                self._root_object.setProperty("bgColor", "#E6E8ED")
                self._root_object.setProperty("floorColor", "#191B20")

    def get_simulation_widget(self):
        """
        Retorna el widget visual de la simulacion.

        Returns:
            SimulationWidget: Instancia del widget.
        """
        return self.simulation_widget

    def change_theme(self, dark_t: bool):
        """
        Notifica al widget el cambio de tema.

        Args:
            dark_t (bool): Nuevo estado del tema.
        """
        self.simulation_widget.change_theme(dark_t)

    @pyqtSlot(list)
    def update_simulation(self, joint_positions: list):
        """
        Slot para actualizar las posiciones de las articulaciones en el modelo 3D.

        Args:
            joint_positions (list): Lista de angulos.
        """
        if self.simulation_worker is not None:
            self.simulation_worker.update_simulation(joint_positions)

    @pyqtSlot(dict)
    def update_sphere_pose_simulation(self, poses: dict):
        """
        Slot para actualizar las posiciones 3D de las esferas detectadas.

        Args:
            poses (dict): Coordenadas cartesianas de las esferas.
        """
        if self.simulation_worker is not None:
            self.simulation_worker.update_sphere_pose_simulation(poses)

    def start_simulation(self):
        """
        Inicia el motor de fisica y muestra la vista de simulacion activa.
        """
        try:
            self.simulation_widget.image_hide()
            self.simulation_widget.container_show()
            self.simulation_widget.quick_show()
            self.simulation_widget.quick_update()

            if self.simulation_worker:
                if not self.simulation_worker.isRunning():
                    self.simulation_worker.start()

            self.physics_worker.start()
        except Exception as e:
            print(f"Error iniciando simulación: {e}")

    def pause_simulation(self):
        """
        Detiene temporalmente el paso de tiempo en el motor de fisica.
        """
        if self.physics_worker:
            self.physics_worker.pause()

    def stop_simulation(self):
        """
        Detiene la simulacion fisica y restaura la vista estatica.
        """
        if self.simulation_worker:
            self.physics_worker.pause()

        if self.simulation_widget.window_container:
            self.simulation_widget.container_hide()
        if self.simulation_widget.quick_view:
            self.simulation_widget.quick_hide()

        self.simulation_widget.image_show()

    def closeEvent(self, event):
        """
        Gestiona el cierre y liberacion de hilos.

        Args:
            event (QCloseEvent): Evento de Qt.
        """
        self.stop_simulation()
        if self.simulation_worker:
            try:
                self.simulation_worker.deleteLater()
                if self.simulation_worker.isRunning():
                    self.simulation_worker.quit()
                    self.simulation_worker.wait(2000)
            except Exception as e:
                print(f"Error cerrando worker: {e}")
            self.simulation_worker = None
