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
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer
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
    send_enabled = pyqtSignal(bool)

    def __init__(self, parent=None):
        """
        Inicializa el controlador y arranca el hilo del worker cinemático.

        Args:
            parent (QWidget, optional): Widget padre.
        """
        super().__init__()
        self._first_kinematic_entry = True
        self.kinematics_widget = KinematicsWidget(parent)
        self.kinematics_worker = KinematicsWorker()

        self.send_enabled.connect(self.kinematics_widget.set_send_enabled)

        # Temporizador de sincronización de UI a 30 Hz (33 ms): desacopla
        # el renderizado del modelo 3D y los sliders del lazo PID a 100 Hz.
        self._ui_timer = QTimer(self)
        self._ui_timer.setInterval(33)
        self._ui_timer.timeout.connect(self._sync_ui)

        self.__setup_connections()
        self.kinematics_worker.start()

    def __setup_connections(self):
        """
        Configura las señales internas y globales para el feature.
        """
        # UI -> Controlador (Petición de movimiento)
        self.kinematics_widget.send_clicked.connect(self.execute_kinematics)

        # Telemetría -> Worker: el KinematicsWorker la lee por polling del
        # RobotWorker (variables compartidas bajo cerrojo), por lo que no
        # necesita conexión de señal hacia el hilo.

        # Worker -> Sistema (Publicacion de comandos calculados)
        self.kinematics_worker.commands_ready.connect(
            self._update_shared_status)

        # Fin de secuencia PID -> rehabilitar controles de la UI
        self.kinematics_worker.control_finished.connect(
            lambda: self.send_enabled.emit(True))

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
        Inicia el seguimiento del destino cartesiano del usuario.

        Al entrar al modo Cartesiano ya se envio el home (ver
        `_on_global_mode_changed`); aqui se va al destino solicitado.
        """
        coords = self.kinematics_widget.get_coordinates()

        # Aplicar offset y correccion de coordenadas
        tx, ty, tz = coords['x'], coords['y'], coords['z']
        tx = tx + 110
        tz = corregir_z(tx, ty, tz)
        tx, ty = corregir_xy(tx, ty)

        # Home ya enviado al entrar al modo; aqui se va al destino.
        self.kinematics_worker.start_target_only(tx, ty, tz)

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
        que el PID compita con otras fuentes de comando. El temporizador
        de sincronización de UI se apaga al salir del modo Cartesiano.

        Args:
            mode (Modes): Nuevo modo de operacion.
        """
        if mode == Modes.KINEMATIC:
            if self._first_kinematic_entry:
                # Primera entrada al modo: enviar el brazo al home.
                self._first_kinematic_entry = False
                self.send_enabled.emit(False)
                self.kinematics_worker.go_home_sequence(
                    on_done=lambda: self.send_enabled.emit(True))
            else:
                self.kinematics_worker.resume_pid()
            if not self._ui_timer.isActive():
                self._ui_timer.start()
        else:
            self.kinematics_worker.pause_pid()
            self._first_kinematic_entry = True
            self.kinematics_worker._pid_stop()
            self._ui_timer.stop()

    def _update_shared_status(self, status):
        """
        Notifica el nuevo estado articular a los suscriptores del sistema.

        Args:
            status (list): Vector de posiciones de servos.
        """
        self.status_updated.emit(status)
        physical_signals = PhysicalSignalManager.get_instance()
        if physical_signals.is_connected:
            physical_signals.send_to_robot.emit(status)

        # Notificar el nuevo objetivo al bus propio. El DataController orquestará el resto.
        KinematicsSignalManager.get_instance().update_target_signal.emit(status)

    def set_robot_worker(self, robot_worker):
        """
        Inyecta la referencia al RobotWorker en el worker de cinemática.

        Permite al KinematicsWorker leer la telemetría por polling de
        forma segura (variables compartidas bajo cerrojo).

        Args:
            robot_worker (RobotWorker): Worker serial del robot físico.
        """
        self.kinematics_worker.set_robot_worker(robot_worker)

    def _sync_ui(self):
        """
        Sincroniza el modelo 3D y los sliders con la posición actual
        del brazo físico a 30 Hz, desacoplando el renderizado del
        lazo PID a 100 Hz.
        """
        # Usamos la posición COMANDADA (siempre disponible una vez
        # enviado un comando) en lugar de la telemetría física, para
        # que los sliders se muevan a la par del brazo aunque el
        # robot no esté conectado por puerto serial.
        pos = self.kinematics_worker.get_commanded_positions()
        if not any(p is not None for p in pos):
            return
        SlidersSignalManager.get_instance().external_values.emit(pos)

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
