import numpy as np
from PyQt6.QtCore import QObject, pyqtSlot, pyqtSignal
from src.features.kinematics.kinematics_widget import KinematicsWidget
from src.features.kinematics.kinematics_worker import KinematicsWorker
from src.services.data.signals import PhysicalSignalManager, SimulationSignalManager
from src.services.data.enums import Modes
from src.services.data.utils import rad_to_deg


class KinematicsController(QObject):
    """
    Orquestador del feature de cinemática.
    Gestiona la comunicación entre el widget de entrada y el worker de cálculo.
    """
    status_updated = pyqtSignal(list)

    # Estado compartido (estático para compatibilidad con DataFlow)
    kinematics_status = [150, 150, 150, 150, 150, 150]

    def __init__(self, parent=None):
        super().__init__()
        self.kinematics_widget = KinematicsWidget(parent)
        self.kinematics_worker = KinematicsWorker()

        self.__setup_connections()
        self.kinematics_worker.start()

    def __setup_connections(self):
        # UI -> Controlador
        self.kinematics_widget.send_clicked.connect(self.execute_kinematics)

        # Telemetría -> Worker
        PhysicalSignalManager.get_instance().data_received.connect(
            self.kinematics_worker.update_sensor_data)

        # Worker -> Sistema
        self.kinematics_worker.commands_ready.connect(
            self._update_shared_status)

    def execute_kinematics(self):
        """ Inicia el proceso cinemático realimentado """
        # Cambiar modo de operación global
        PhysicalSignalManager.get_instance().change_mode_signal.emit(Modes.KINEMATIC)
        SimulationSignalManager.get_instance().change_mode_signal.emit(Modes.KINEMATIC)

        coords = self.kinematics_widget.get_coordinates()

        # 1. Fijar objetivo en el worker para control realimentado
        self.kinematics_worker.set_target(
            coords['x'], coords['y'], coords['z'])

        # 2. Estimación inicial rápida para la simulación
        best_q, _ = self.kinematics_worker.ci(
            coords['x'], coords['y'], coords['z'], 0)
        q_deg = rad_to_deg(best_q.flatten())

        initial_status = [
            np.abs(q_deg[0] + 150.0),
            np.abs(q_deg[1] - 150.0),
            np.abs(q_deg[2] - 150.0),
            150.0,
            np.abs(q_deg[3] + 150.0),
            171
        ]
        self._update_shared_status(initial_status)

    def _update_shared_status(self, status):
        KinematicsController.kinematics_status = status
        self.status_updated.emit(status)
        # Notificar al DataFlow de forma reactiva
        PhysicalSignalManager.get_instance().update_target_signal.emit(status)
        SimulationSignalManager.get_instance().update_target_signal.emit(status)


    @classmethod
    def get_kinematics_state(cls):
        """ API estática para DataFlow """
        return cls.kinematics_status

    def get_widget(self):
        return self.kinematics_widget

    def get_worker(self):
        """ Retorna la instancia del worker de cinemática """
        return self.kinematics_worker

    def cleanup(self):
        self.kinematics_worker.terminate()
        self.kinematics_worker.wait()
