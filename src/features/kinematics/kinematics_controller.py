"""
Modulo que orquesta el flujo de control cinematico del robot.

Este modulo define la clase KinematicsController, la cual actua como el puente
entre la entrada de coordenadas cartesianas del usuario (KinematicsWidget)
y el motor de calculo y control realimentado (KinematicsWorker).

Conexiones:
    - Escucha eventos de clic del widget para iniciar trayectorias.
    - Sincroniza la telemetria real del robot con el worker cinematico.
    - Emite actualizaciones de estado a los managers de simulacion y hardware.
"""

import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal
from src.features.kinematics.kinematics_widget import KinematicsWidget
from src.features.kinematics.kinematics_worker import KinematicsWorker
from src.services.data.signals import PhysicalSignalManager, SimulationSignalManager
from src.services.data.enums import Modes
from src.services.data.utils import rad_to_deg


class KinematicsController(QObject):
    """
    Controlador para el modulo de cinematica del brazo robotico.

    Gestiona la ejecucion de la cinematica inversa y el mantenimiento del
    estado deseado del robot cuando se opera en modo cartesiano.

    Attributes:
        status_updated (pyqtSignal): Emite el nuevo vector de posiciones de servos.
        kinematics_status (list): Estado compartido de las articulaciones.
    """
    status_updated = pyqtSignal(list)

    # Estado compartido (estático para compatibilidad con el flujo de datos reactivo)
    kinematics_status = [150, 150, 150, 150, 150, 150]

    def __init__(self, parent=None):
        """
        Inicializa el controlador y arranca el hilo del worker cinematico.

        Args:
            parent (QWidget, optional): Widget padre.
        """
        super().__init__()
        self.kinematics_widget = KinematicsWidget(parent)
        self.kinematics_worker = KinematicsWorker()

        self.__setup_connections()
        self.kinematics_worker.start()

    def __setup_connections(self):
        """
        Configura las señales internas y globales para el feature.
        """
        # UI -> Controlador (Peticion de movimiento)
        self.kinematics_widget.send_clicked.connect(self.execute_kinematics)

        # Telemetria -> Worker (Retroalimentacion para control de lazo cerrado)
        PhysicalSignalManager.get_instance().data_received.connect(
            self.kinematics_worker.update_sensor_data)

        # Worker -> Sistema (Publicacion de comandos calculados)
        self.kinematics_worker.commands_ready.connect(
            self._update_shared_status)

    def execute_kinematics(self):
        """
        Inicia el proceso de calculo cinematico basado en la entrada de la UI.

        Cambia el modo de operacion a KINEMATIC y establece el objetivo
        en el worker para el seguimiento de la trayectoria.
        """
        # Cambiar modo de operación global para que el sistema ignore los Sliders manuales
        PhysicalSignalManager.get_instance().change_mode_signal.emit(Modes.KINEMATIC)
        SimulationSignalManager.get_instance().change_mode_signal.emit(Modes.KINEMATIC)

        coords = self.kinematics_widget.get_coordinates()

        # 1. Fijar objetivo en el worker para control realimentado (Newton-Raphson / DLS)
        self.kinematics_worker.set_target(
            coords['x'], coords['y'], coords['z'])

        # 2. Estimación inicial rápida mediante CI iterativa para actualizacion inmediata
        best_q, _ = self.kinematics_worker.ci(
            coords['x'], coords['y'], coords['z'], 0)
        q_deg = rad_to_deg(best_q.flatten())

        # Mapeo a formato de servos (0-300) con offsets y signos correspondientes
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
        """
        Actualiza el estado interno y notifica a los suscriptores del sistema.

        Args:
            status (list): Vector de posiciones de servos.
        """
        KinematicsController.kinematics_status = status
        self.status_updated.emit(status)
        # Notificar al DataFlow (Simulacion y Robot Fisico) de forma reactiva
        PhysicalSignalManager.get_instance().update_target_signal.emit(status)
        SimulationSignalManager.get_instance().update_target_signal.emit(status)

    @classmethod
    def get_kinematics_state(cls):
        """
        API estática para acceder al ultimo estado cinematico calculado.

        Returns:
            list: Posiciones actuales de los servos.
        """
        return cls.kinematics_status

    def get_widget(self):
        """
        Retorna la vista asociada al controlador.

        Returns:
            KinematicsWidget: Instancia del widget.
        """
        return self.kinematics_widget

    def get_worker(self):
        """
        Retorna el worker de calculo.

        Returns:
            KinematicsWorker: Instancia del hilo de cinematica.
        """
        return self.kinematics_worker

    def cleanup(self):
        """
        Libera recursos y detiene el hilo del worker.
        """
        self.kinematics_worker.terminate()
        self.kinematics_worker.wait()
