""" Modulo que actúa como controlador de flujo de datos permitiendo la comunicación ya sea entre 
    la interfaz y el robot físico o entre la interfaz y la simulación.

    Las clases de SignalManager actúan como puente entre estos elementos de la siguiente forma:

    ```
        GUI (Datos de la interfaz como los ángulos de los sliders)
        ⭣
    DataFlow
        ⮃
        ├──⮞ SimulationSignalManager ⭢ SimWorker (Hilo de proceso del modelo 3D)
        |
        ├──⮞ SimulationSignalManager ⮂ PhysicsWorker (Recibe y obtiene datos de pybullet)
        │
        └──⮞ SimulationSignalManager ⭢ GraphWorker (Agrega los datos al graficador)
    ```
    En cuanto al robot físico se tiene un flujo similar
    ```
       GUI (Datos de la interfaz como los ángulos de los sliders)
        ⭣
    DataFlow
        ⮃
        ├──⮞ PhysicalSignalManager ⮂ RobotWorker (Recibe y obtiene datos de pybullet)
        │
        └──⮞ PhysicalSignalManager ⭢ GraphWorker (Agrega los datos al graficador)
    ```
"""
import numpy as np
from PyQt6.QtCore import QThread
from pyqtgraph.Qt.QtCore import pyqtSlot
from data import deg_to_rad, rad_to_deg
from data import PhysicalSignalManager, Modes, Units, Domains, SimulationSignalManager, GlobalTimer


class DataFlow(QThread):
    """ Clase que actúa como controlador de datos entre la interfaz y la simulación o el 
        robot físico, permitiendo un mejor manejo del flujo de datos entre las diferentes secciones
        de la aplicación.
    """

    def __init__(self, mode: Modes, unit: Units, domain: Domains) -> None:
        super().__init__()
        self.actual_pos = None  # Posición actual del robot simulación o físico
        self.source_pos = None  # Posiciones deseadas de la fuente seleccionada
        self.mode = mode
        self.units = unit
        self.signal_manager = None
        self.domain = domain
        self.sync_timer = GlobalTimer.get_instance()
        self.sync_timer.start()

        # Inicializa las señales dependiendo de cual sea el dominio
        if self.domain is Domains.SIMULATION:
            self.signal_manager = SimulationSignalManager.get_instance()
            self.signal_manager.sensor_position_signal.connect(
                self.update_simulation_graph)
            self.signal_manager.model_position_signal.connect(
                self.update_simulation_model)
            self.sync_timer.sync_simulation_tick.connect(
                self.request_objective_data_simulation)
        elif self.domain is Domains.PHYSICAL:
            self.signal_manager = PhysicalSignalManager.get_instance()
            self.signal_manager.sensor_position_signal.connect(
                self.update_robot)
            self.sync_timer.sync_robot_tick.connect(
                self.request_objective_data_robot)
        else:
            raise Exception("El dominio proporcionado no existe.")

        # Lazy import para evitar ciclo circular
        try:
            from gui.sliders_interface import SlidersWidget
            if SlidersWidget.instance is not None:
                SlidersWidget.instance.mode_changed.connect(
                    self.signal_manager.change_mode_signal)
        except Exception:
            pass
        self.signal_manager.change_mode_signal.connect(self.change_mode)

    def request_objective_data_simulation(self):
        """ Solicita los datos objetivos de los motores, es decir, los ángulos a los que se desea
            mover cada motor, estos datos pueden tener diferentes fuentes como lo son los slider, 
            los cuales se obtienen con la función __get_sliders_data().

            Estos datos se entregan en forma de una lista de seis elementos, los cuales dependiendo
            del dominio en que se encuentren serán entregados en radianes o en grados:
            ```
                - La simulación con pybullet utiliza radianes.
                - El robot físico Openbotv-V1 utiliza grados.
            ```
        """
        if self.mode is Modes.SLIDERS:
            self.signal_manager.update_pybullet_signal.emit(
                self.__get_sliders_data())
        elif self.mode is Modes.KINEMATIC:
            self.signal_manager.update_pybullet_signal.emit(
                self.__get_kinematics_data())

    def request_objective_data_robot(self):
        """ Solicita los datos objetivos de los motores, es decir, los ángulos a los que se desea
            mover cada motor, estos datos pueden tener diferentes fuentes como lo son los slider, 
            los cuales se obtienen con la función __get_sliders_data().

            Estos datos se entregan en forma de una lista de seis elementos, los cuales dependiendo
            del dominio en que se encuentren serán entregados en radianes o en grados:
            ```
                - La simulación con pybullet utiliza radianes.
                - El robot físico Openbotv-V1 utiliza grados.
            ```
        """
        if self.mode is Modes.SLIDERS:
            new_data = self.__get_sliders_data()
            self.signal_manager.send_to_robot.emit(new_data)
            self.signal_manager.update_pybullet_signal.emit(new_data)
        elif self.mode is Modes.KINEMATIC:
            new_data = self.__get_kinematics_data()
            self.signal_manager.send_to_robot.emit(new_data)
            self.signal_manager.update_pybullet_signal.emit(new_data)

    def __get_sliders_data(self):
        """ Obtiene los datos provenientes de la interfaz para los ángulos objetivos definidos con
            los sliders, se reciben como una lista de seis posiciones y dependiendo de lo requerido
            según el dominio de ejecución, se realiza la transformación a radianes o se retorna en 
            grados como los proporciona la interfaz.

        Returns:
            NDArray: Arreglo con las posiciones objetivos configuradas en la interfaz
        """
        from gui.sliders_interface import SlidersWidget
        if self.units is Units.DEG:
            return np.array(SlidersWidget.get_sliders_state())
        if self.units is Units.RAD:
            return deg_to_rad(SlidersWidget.get_sliders_state())

    def __get_kinematics_data(self):
        """ Obtiene los datos provenientes de la interfaz para los ángulos objetivos definidos con
            los sliders, se reciben como una lista de seis posiciones y dependiendo de lo requerido
            según el dominio de ejecución, se realiza la transformación a radianes o se retorna en 
            grados como los proporciona la interfaz.

        Returns:
            NDArray: Arreglo con las posiciones objetivos configuradas en la interfaz
        """
        from gui.kinematics_interface import KinematicsWidget
        kin_vals = KinematicsWidget.get_kinematics_state()

        # Intentar actualizar los sliders de la interfaz si existe la instancia
        try:
            from gui.sliders_interface import SlidersWidget
            if SlidersWidget.instance is not None and kin_vals is not None:
                SlidersWidget.instance.set_values(kin_vals)
            self.change_mode(Modes.KINEMATIC)
        except Exception:
            pass

        if self.units is Units.DEG:
            return np.array(kin_vals)
        if self.units is Units.RAD:
            return deg_to_rad(kin_vals)

    @pyqtSlot(list)
    def update_simulation_graph(self, actual_positions):
        """ Esta función es un slot de pyqt es decir esta conectada a la señal de activación 
            actual_position_signal la cual al hacer el emit activa esta función con los datos
            actual_position los cuales se reciben en radianes ya que provienen de pybullet y deben
            ser convertidos a grados luego se emite esta trasformación al modelo 3D de qtQuick
            y a los gráficos de pyqtgraph

        Args:
            actual_positions (list): Posiciones actuales de los motores del robot de pybullet
        """
        pos = rad_to_deg(actual_positions)
        self.signal_manager.update_graph_signal.emit(pos)

    @pyqtSlot(list)
    def update_simulation_model(self, actual_positions):
        """ Esta función es un slot de pyqt es decir esta conectada a la señal de activación 
            actual_position_signal la cual al hacer el emit activa esta función con los datos
            actual_position los cuales se reciben en radianes ya que provienen de pybullet y deben
            ser convertidos a grados luego se emite esta trasformación al modelo 3D de qtQuick
            y a los gráficos de pyqtgraph

        Args:
            actual_positions (list): Posiciones actuales de los motores del robot de pybullet
        """
        pos = rad_to_deg(actual_positions)
        self.signal_manager.update_robot_signal.emit(pos)

    @pyqtSlot(list)
    def update_robot(self, actual_positions):
        """Slot conectado en el dominio físico.  Recibe una lista de seis ángulos
           (grados) provenientes del robot y los reemite como `data_received`, de
           modo que cualquier clase (por ejemplo el worker de cinemática) pueda
           suscribirse a ella.

        Args:
            actual_positions (list): Posiciones actuales de los motores del robot físico
        """
        # corregir nombre de la señal y reenviar junto con temperaturas vacías
        self.signal_manager.data_received.emit(actual_positions, [])

    def change_mode(self, mode):
        self.mode = mode
