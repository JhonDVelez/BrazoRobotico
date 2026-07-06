"""
Módulo que orquesta el flujo de control cinemático del robot.

Este módulo define la clase KinematicsController, la cual actúa como el puente
entre la entrada de coordenadas cartesianas del usuario (KinematicsWidget)
y el motor de cálculo y control realimentado (KinematicsWorker).

Conexiones:
    - Escucha eventos de clic del widget para iniciar trayectorias.
    - Sincroniza la telemetría real del robot con el worker cinemático.
    - Emite actualizaciones de estado a los managers de simulación y hardware.
"""

import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from src.features.kinematics.kinematics_widget import KinematicsWidget
from src.features.kinematics.kinematics_worker import KinematicsWorker
from src.services.data.signals import (
    PhysicalSignalManager, KinematicsSignalManager,
    SimulationSignalManager, SlidersSignalManager
)
from src.services.data.enums import Modes
from src.services.data.utils import rad_to_deg
from .coordinate_correction import corregir_xy, corregir_z


class KinematicsController(QObject):
    """
    Controlador para el módulo de cinemática del brazo robótico.

    Gestiona la ejecución de la cinemática inversa y el mantenimiento del
    estado deseado del robot cuando se opera en modo cartesiano.

    Attributes:
        status_updated (pyqtSignal): Emite el nuevo vector de posiciones de servos.
    """
    status_updated = pyqtSignal(list)

    def __init__(self, parent=None):
        """
        Inicializa el controlador y arranca el hilo del worker cinemático.

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
        # UI -> Controlador (Petición de movimiento)
        self.kinematics_widget.send_clicked.connect(self.execute_kinematics)

        # Telemetria -> Worker (Retroalimentacion para control de lazo cerrado)
        # El controlador actúa como puente hacia el worker
        PhysicalSignalManager.get_instance().data_received.connect(
            self.kinematics_worker.update_sensor_data)

        # Worker -> Sistema (Publicacion de comandos calculados)
        self.kinematics_worker.commands_ready.connect(
            self._update_shared_status)

        # IK del flujo Pick and Place mediada por el DataController.
        # Kinematics escucha en su propio bus; no conoce a PickPlace.
        KinematicsSignalManager.get_instance().inverse_kinematics_requested.connect(
            self._on_inverse_kinematics_requested
        )

        # Pausar/Reanudar PID segun el modo global de operacion.
        # Escucha todos los orígenes de cambio de modo (sliders, sim, etc.)
        # para pausar el lazo PID cuando no se esta en modo cinematico.
        SimulationSignalManager.get_instance().change_mode_signal.connect(
            self._on_global_mode_changed)
        PhysicalSignalManager.get_instance().change_mode_signal.connect(
            self._on_global_mode_changed)
        SlidersSignalManager.get_instance().change_mode_signal.connect(
            self._on_global_mode_changed)
        KinematicsSignalManager.get_instance().change_mode_signal.connect(
            self._on_global_mode_changed)

    def execute_kinematics(self):
        """
        Inicia el proceso de cálculo cinemático basado en la entrada de la UI.

        Cambia el modo de operacion a KINEMATIC y establece el objetivo
        en el worker para el seguimiento de la trayectoria.
        """
        # Cambiar modo de operación global mediante el bus propio de la feature.
        # El DataController escucha y orquesta el resto del sistema.
        KinematicsSignalManager.get_instance().change_mode_signal.emit(
            Modes.KINEMATIC)

        coords = self.kinematics_widget.get_coordinates()

        # Aplicar offset y correccion de coordenadas
        tx, ty, tz = coords['x'], coords['y'], coords['z']
        tx = tx + 110
        tz = corregir_z(tx, ty, tz)
        tx, ty = corregir_xy(tx, ty)

<<<<<<< HEAD
        # Ejecutar secuencia home + target en el worker (no bloqueante, via QTimer)
        self.kinematics_worker.execute_target(tx, ty, tz)
=======
        # 2. Estimación inicial rápida mediante CI iterativa para actualización inmediata

        _, q_deg = self.execute_inverse_kinematics(coords)
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
>>>>>>> 1825586cf103f63ef7f9c90d4540b2f568c648da

    def execute_inverse_kinematics(self, coords: dict):
        """
        Calcula cinemática inversa para coordenadas cartesianas.

        Args:
            coords (dict): Coordenadas objetivo con claves `x`, `y` y `z`.

        Returns:
            tuple: Ángulos articulares en radianes y grados.
        """
        q_rad = self.kinematics_worker.ci(
            coords['x'], coords['y'], coords['z'])
        q_deg = rad_to_deg(q_rad.flatten())
        return q_rad, q_deg

    @pyqtSlot(dict)
    def _on_inverse_kinematics_requested(self, request: dict):
        """
        Atiende solicitudes de cinemática inversa ruteadas por el DataController.

        Args:
            request (dict): Contiene `color`, `coords` y `gripper_degrees`.
        """
        coords = request.get('coords')
        if not coords:
            return

        tx, ty, tz = coords['x'], coords['y'], coords['z']
        tz = corregir_z(tx, ty, tz)
        tx, ty = corregir_xy(tx, ty)
        coords = {'x': tx, 'y': ty, 'z': tz}

        _, q_deg = self.execute_inverse_kinematics(coords)
        gripper_degrees = request.get('gripper_degrees', 0)
        target = [
            np.abs(q_deg[0] + 150.0),
            np.abs(q_deg[1] - 150.0),
            np.abs(q_deg[2] - 150.0),
            150.0,
            np.abs(q_deg[3] + 150.0),
            float(gripper_degrees + 150.0)
        ]
        # Publicar el resultado en el bus propio. El DataController lo rutea a PickPlace.
        KinematicsSignalManager.get_instance().inverse_kinematics_ready.emit({
            'color': request.get('color'),
            'target': target
        })

    @pyqtSlot(object)
    def _on_global_mode_changed(self, mode: Modes):
        """
        Pausa o reanuda el PID cartesiano segun el modo de operacion global.

        Solo se permite el lazo PID en modo KINEMATIC. Al salir de este
        modo (sliders, pick-place, etc.) se pausa el control para evitar
        que el PID compita con otras fuentes de comando.

        Args:
            mode (Modes): Nuevo modo de operacion.
        """
        if mode == Modes.KINEMATIC:
            self.kinematics_worker.resume_pid()
        else:
            self.kinematics_worker.pause_pid()

    def _update_shared_status(self, status):
        """
        Notifica el nuevo estado articular a los suscriptores del sistema.

        Args:
            status (list): Vector de posiciones de servos.
        """
        self.status_updated.emit(status)
        # Notificar el nuevo objetivo al bus propio. El DataController orquestará el resto.
        KinematicsSignalManager.get_instance().update_target_signal.emit(status)

    def get_widget(self):
        """
        Retorna la vista asociada al controlador.

        Returns:
            KinematicsWidget: Instancia del widget.
        """
        return self.kinematics_widget

    def get_worker(self):
        """
        Retorna el worker de cálculo.

        Returns:
            KinematicsWorker: Instancia del hilo de cinemática.
        """
        return self.kinematics_worker

    def cleanup(self):
        """
        Libera recursos y detiene el hilo del worker.
        """
        self.kinematics_worker.terminate()
        self.kinematics_worker.wait()
