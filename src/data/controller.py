from PyQt6.QtCore import QThread
from gui.sliders_interface import SlidersWidget
from data import control_utils
from data.control_utils import PhysicalSignalManager, modes, units, domains, SimulationSignalManager


class dataFlow(QThread):
    """ Clase que actua como controlador de datos entre la interfaz y la simulacion o el 
        robot fisico
    """

    def __init__(self, mode: modes, unit: units, domain: domains) -> None:
        super().__init__()
        self.actual_pos = None  # Posicion actual del robot simulacion o fisico
        self.source_pos = None  # Posiciones deseadas de la fuente seleccionada
        self.mode = mode
        self.units = unit
        self.signal_manager = None

        # Inicializa las señales dependiendo de cual sea el dominio
        if domain is domains.SIMULATION:
            self.signal_manager = SimulationSignalManager.get_instance()
            self.signal_manager.get_data_signal.connect(self.get_data)
            self.signal_manager.actual_position_signal.connect(
                self.update_simulation)
        elif domain is domains.PHYSICAL:
            self.signal_manager = PhysicalSignalManager.get_instance()
        else:
            raise Exception("El dominio proporcionado no existe.")

    def get_data(self):
        """ Envia los datos al simulador dependiendo de la fuente seleccionada
        """
        if self.mode is modes.SLIDERS:
            self.signal_manager.update_pybullet_signal.emit(
                self.__get_sliders_data())

    def __get_sliders_data(self):
        if self.units is units.DEG:
            return SlidersWidget.get_sliders_state()
        if self.units is units.RAD:
            return control_utils.deg_to_rad(SlidersWidget.get_sliders_state())

    def update_graph(self):
        pass  # Enviar datos a los graficos

    def update_simulation(self, actual_positions):
        """ Envia los datos al modelo 3D de QtQuick los cuales deben estar en grados

        Args:
            actual_positions (list): Posiciones actuales de los motores del robot de pybullet
        """
        self.signal_manager.update_robot_signal.emit(
            control_utils.rad_to_deg(actual_positions))

    def set_mode(self, mode: modes):
        """ Permite redefinir el modo de ejecucion, es decir, cambiar la fuente de los datos 
            objetivos para el robot

        Args:
            mode (modes): modo que debe estar entre el enum modes
        """
        self.mode = mode

    def set_units(self, unit: units):
        """ Permite redefinir las unidades en las que se obtienen los datos entre radianes y grados

        Args:
            unit (units): unidades manejadas que deben estar presentes en el enum units
        """
        self.units = unit
