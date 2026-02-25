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
from PyQt6.QtCore import QThread
from pyqtgraph.Qt.QtCore import pyqtSlot
from gui.sliders_interface import SlidersWidget
from data import deg_to_rad, rad_to_deg
from data import PhysicalSignalManager, Modes, Units, Domains, SimulationSignalManager


class DataFlow(QThread):
    """ Clase que actúa como controlador de datos entre la interfaz y la simulación o el 
        robot físico. Hereda de QThread para procesar el flujo sin bloquear la UI.
    """

    def __init__(self, mode: Modes, unit: Units, domain: Domains) -> None:
        super().__init__()
        self.actual_pos = None  # Almacena la posición real reportada por el sistema (sim/físico)
        self.source_pos = None  # Almacena la posición objetivo capturada de la UI
        self.mode = mode        # Modo de control (ej. SLIDERS)
        self.units = unit       # Sistema de unidades de entrada (RAD o DEG)
        self.signal_manager = None # Se asignará al gestor correspondiente (Sim o Phys)
        self.domain = domain    # Identifica si el destino es la simulación o el hardware

        # --- CONFIGURACIÓN DINÁMICA DE SEÑALES ---
        # Dependiendo del dominio, se suscribe a los eventos del Singleton correspondiente
        if self.domain is Domains.SIMULATION:
            self.signal_manager = SimulationSignalManager.get_instance()
            # Conecta la petición de datos con el método que lee la interfaz
            self.signal_manager.get_data_signal.connect(
                self.request_objective_data)
            # Conecta la respuesta de posición real con el actualizador visual
            self.signal_manager.actual_position_signal.connect(
                self.update_simulation)
                
        elif self.domain is Domains.PHYSICAL:
            self.signal_manager = PhysicalSignalManager.get_instance()
            # Misma lógica de petición pero para el dominio físico
            self.signal_manager.get_data_signal.connect(
                self.request_objective_data)
            # Actualiza el estado del robot real en la interfaz/gráficas
            self.signal_manager.actual_position_signal.connect(
                self.update_robot)
        else:
            # Error de seguridad en caso de recibir un dominio no definido
            raise Exception("El dominio proporcionado no existe.")

    def request_objective_data(self):
        """ Solicita los datos objetivos de los motores, es decir, los ángulos a los que se desea
            mover cada motor. Obtiene los valores de la fuente activa (actualmente Sliders).

            Estos datos se entregan en forma de una lista de seis elementos. Realiza la 
            conversión necesaria: la simulación (PyBullet) requiere radianes, mientras que
            el robot físico suele trabajar en grados.
        """
        if self.mode is Modes.SLIDERS:
            # Si estamos en simulación, envía los ángulos convertidos a PyBullet
            if self.domain is Domains.SIMULATION:
                self.signal_manager.update_pybullet_signal.emit(
                    self.__get_sliders_data())
            # Si es físico, envía los datos (normalmente en grados) al hardware
            elif self.domain is Domains.PHYSICAL:
                self.signal_manager.send_to_robot.emit(
                    self.__get_sliders_data())

    def __get_sliders_data(self):
        """ Método privado que extrae el estado actual de los sliders de la interfaz.
            Aplica conversiones de unidad sobre la marcha según la configuración del objeto.
        """
        if self.units is Units.DEG:
            # Retorna la lista de ángulos tal cual están en la interfaz (grados)
            return SlidersWidget.get_sliders_state()
        if self.units is Units.RAD:
            # Convierte los grados de la interfaz a radianes para cálculos matemáticos/física
            return deg_to_rad(SlidersWidget.get_sliders_state())

    @pyqtSlot(list)
    def update_simulation(self, actual_positions):
        """ Slot que recibe la posición real calculada por PyBullet (en radianes).
            1. Convierte los datos a grados.
            2. Notifica al modelo visual 3D para que mueva las piezas.
            3. Envía los datos al módulo de gráficas para el registro temporal.

        Args:
            actual_positions (list): Posiciones actuales de los motores en radianes.
        """
        # Conversión necesaria para que la visualización y gráficas sean legibles (grados)
        pos = rad_to_deg(actual_positions)
        # Dispara la actualización del robot 3D
        self.signal_manager.update_robot_signal.emit(pos)
        # Dispara la actualización de las gráficas de telemetría
        self.signal_manager.update_graph_signal.emit(pos)

    @pyqtSlot(list)
    def update_robot(self, actual_positions):
        """ Procesa el feedback del robot físico. Envía las posiciones reales recibidas
            del hardware directamente al graficador.

        Args:
            actual_positions (list): Posiciones actuales de los motores del robot físico.
        """
        # Envía los datos para ser graficados en tiempo real
        self.signal_manager.update_graph_signal.emit(actual_positions)