""" Modulo que contiene el Worker para el procesamiento de flujo de datos.
    Sigue el patrón Worker-Widget-Controller.
"""
import numpy as np
from PyQt6.QtCore import QObject, pyqtSlot
from src.services.data.utils import deg_to_rad, rad_to_deg
from src.services.data.enums import Units, Modes


class DataWorker(QObject):
    """ Worker encargado del procesamiento pesado y transformación de datos.
        Realiza conversiones de unidades y prepara los paquetes para los diferentes
        destinos (simulación, robot físico, gráficos).
    """

    def __init__(self, signal_manager, robot_controller=None):
        super().__init__()
        self.signal_manager = signal_manager
        self.robot_controller = robot_controller

    @pyqtSlot(list, object, object)
    def process_simulation_data(self, data, unit, mode):
        """ Procesa datos destinados a la simulación. """
        if data is None:
            return

        # Convertir a radianes para PyBullet si vienen en grados
        if unit is Units.RAD:
            processed_data = deg_to_rad(data)
        else:
            processed_data = np.array(data)

        self.signal_manager.update_pybullet_signal.emit(processed_data)

    @pyqtSlot(list, object, object)
    def process_physical_data(self, data, unit, mode):
        """ Procesa datos destinados al robot físico y simulación sincronizada. """
        if data is None:
            return

        # El robot físico usualmente recibe grados, pero validamos
        if unit is Units.RAD:
            data_deg = rad_to_deg(data)
        else:
            data_deg = np.array(data)

        # Enviar al robot físico mediante el controlador
        if self.robot_controller:
            self.robot_controller.move_to(data_deg.tolist())

        # También actualizamos la simulación para que refleje el movimiento del robot
        # PyBullet usa radianes
        data_rad = deg_to_rad(data_deg)
        self.signal_manager.update_pybullet_signal.emit(data_rad)

    @pyqtSlot(list)
    def update_graph_data(self, actual_positions):
        """ Procesa posiciones recibidas para actualización de gráficos. """
        # PyBullet envía radianes, los gráficos usan grados
        pos_deg = rad_to_deg(actual_positions)
        self.signal_manager.update_graph_signal.emit(pos_deg)

    @pyqtSlot(list)
    def update_model_data(self, actual_positions):
        """ Procesa posiciones recibidas para actualización del modelo 3D. """
        # PyBullet envía radianes, el modelo usa grados
        pos_deg = rad_to_deg(actual_positions)
        self.signal_manager.update_robot_signal.emit(pos_deg)

    @pyqtSlot(list)
    def update_robot_feedback(self, actual_positions):
        """ Procesa el feedback recibido del robot físico. """
        # Reenvía los datos recibidos para que otros componentes los consuman
        self.signal_manager.data_received.emit(actual_positions, [])
