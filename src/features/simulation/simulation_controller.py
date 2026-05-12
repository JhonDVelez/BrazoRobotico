from PyQt6.QtCore import pyqtSlot, QObject
from src.services.data import DataController
from src.services.data.enums import Units, Modes, Domains
from src.services.simulation import PhysicsWorker
from src.services.styling.theme_manger import ThemeSignalManager
from src.services.data.signals import SimulationSignalManager
from src.features.simulation.simulation_worker import SimulationWorker
from src.features.simulation.simulation_widget import SimulationWidget


class SimulationController(QObject):
    """ Clase encargada del modelo 3d usando contenedor completamente precargado
    """

    def __init__(self, parent, preloaded_container, robot_id):
        super().__init__()
        self.robot_id = robot_id
        self.parent = parent
        self.simulation_worker = None
        self._root_object = None

        self.simulation_widget = SimulationWidget(
            preloaded_container, self.init_pybullet_processing).get_simulation_widget()
        self.physics_worker = PhysicsWorker(self.robot_id)

        self.theme_manager = ThemeSignalManager.get_instance()
        self.theme_manager.theme_changed.connect(self.change_theme)
        self.simulation_widget.theme_needed.connect(self._apply_root_theme)

        self.controller = DataController(
            Modes.SLIDERS, Units.RAD, Domains.SIMULATION)
        self.controller.start()

        self.signal_manager = SimulationSignalManager.get_instance()
        self.signal_manager.update_robot_signal.connect(self.update_simulation)
        self.signal_manager.sphere_pos.connect(
            self.update_sphere_pose_simulation)

    def init_pybullet_processing(self, root_object):
        self._root_object = root_object
        self.simulation_worker = SimulationWorker(
            root_object, self.robot_id)
        self.simulation_worker.start()

    def _apply_root_theme(self, dark_t: bool):
        if self._root_object is not None:
            if dark_t:
                self._root_object.setProperty("bgColor", "#191B20")
                self._root_object.setProperty("floorColor", "#E6E8ED")
            else:
                self._root_object.setProperty("bgColor", "#E6E8ED")
                self._root_object.setProperty("floorColor", "#191B20")

    def get_simulation_widget(self):
        return self.simulation_widget

    def change_theme(self, dark_t: bool):
        self.simulation_widget.change_theme(dark_t)

    @pyqtSlot(list)
    def update_simulation(self, joint_positions: list):
        if self.simulation_worker is not None:
            self.simulation_worker.update_simulation(joint_positions)

    @pyqtSlot(dict)
    def update_sphere_pose_simulation(self, poses: dict):
        if self.simulation_worker is not None:
            self.simulation_worker.update_sphere_pose_simulation(poses)

    def start_simulation(self):
        """ Inicia la simulación con recursos ya precargados
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

            self.simulation_widget.set_process_state(True)
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
        self.simulation_widget.set_process_state(False)

        if self.simulation_worker:
            self.physics_worker.pause()

        if self.simulation_widget.window_container:
            self.simulation_widget.container_hide()
        if self.simulation_widget.quick_view:
            self.simulation_widget.quick_hide()

        self.simulation_widget.image_show()
        self.simulation_widget.set_static_image()

    def closeEvent(self, event):
        """ Limpieza al cerrar
        """
        if self.simulation_widget.get_process_state():
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

        super().closeEvent(event)
