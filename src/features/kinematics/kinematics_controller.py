"""
Modulo que orquesta el flujo de control cinematico del robot.

Actua como puente entre la entrada de coordenadas cartesianas del usuario
(KinematicsWorker en hilo independiente) y el motor de control PID basado
en el codigo standalone Prueba_controlv11.

Flujo:
    1. Al activar modo cinematica:
       - Verificar conexion del robot.
       - Suspender serial del RobotWorker.
       - Enviar HOME directo (sin PID) y esperar 2.5s.
       - Habilitar entrada de coordenadas del usuario.
    2. Al recibir coordenadas ("Enviar"):
       - PID al HOME con compensaciones.
       - PID al TARGET con compensaciones.
    3. Al salir del modo cinematica:
       - Detener el worker.
       - Reanudar serial del RobotWorker.
"""

import numpy as np
from PyQt6.QtCore import QObject, pyqtSlot, QTimer
from PyQt6.QtWidgets import QMessageBox
from src.features.kinematics.kinematics_widget import KinematicsWidget
from src.features.kinematics.kinematics_worker import KinematicsWorker
from src.services.data.signals import (
    PhysicalSignalManager, KinematicsSignalManager,
    SlidersSignalManager, SimulationSignalManager
)
from src.services.data.enums import Modes
from src.services.data.utils import robotang_angulos
from .coordinate_correction import corregir_xy, corregir_z


class KinematicsController(QObject):
    """
    Controlador para el modo cinematico del brazo robotico.

    Orquesta el lifecycle completo:
    - Entrada al modo (HOME directo + habilitar UI)
    - Ejecucion de movimientos (PID HOME + PID TARGET)
    - Salida del modo (detener worker + reanudar RobotWorker)
    """

    def __init__(self, parent=None):
        super().__init__()
        self.kinematics_widget = KinematicsWidget(parent)
        self.kinematics_worker = KinematicsWorker()
        self._claw_mm = 30 # Valor inicial persistente
        self._robot_service = None
        self._graph_controller = None
        self._mode_active = False
        self._last_emitted_angulos = None
        self._last_processed_pos = None
        self._smoothed_pos = None

        self.__setup_connections()

    def set_robot_service(self, robot_service):
        self._robot_service = robot_service

    def set_graph_controller(self, graph_controller):
        self._graph_controller = graph_controller

    def __setup_connections(self):
        self.kinematics_widget.send_clicked.connect(
            self.execute_kinematics)
        self.kinematics_widget.claw_changed.connect(
            self._on_claw_changed)

        self.kinematics_worker.status_changed.connect(
            self._on_status_changed)
        self.kinematics_worker.movement_finished.connect(
            self._on_movement_finished)
        self.kinematics_worker.input_enabled.connect(
            self._on_input_enabled)
        self.kinematics_worker.joint_update.connect(
            self._on_joint_update)

        SlidersSignalManager.get_instance().change_mode_signal.connect(
            self._on_global_mode_changed)
        SimulationSignalManager.get_instance().change_mode_signal.connect(
            self._on_global_mode_changed)
        KinematicsSignalManager.get_instance().change_mode_signal.connect(
            self._on_global_mode_changed)

    def enter_kinematics_mode(self):
        if self._mode_active:
            return

        phys = PhysicalSignalManager.get_instance()
        if not phys.is_connected:
            QMessageBox.warning(
                self.kinematics_widget,
                "Robot no conectado",
                "Para usar el modo Cinematica debe conectar el robot "
                "previamente desde el menu Robot > Puerto."
            )
            return

        if self._robot_service is None:
            return

        self._mode_active = True
        self.kinematics_worker.reset_state()
        
        # Sincronizar valor persistente
        self.kinematics_worker.set_claw_value(self._claw_mm)
        
        KinematicsSignalManager.get_instance().change_mode_signal.emit(
            Modes.KINEMATIC)

        SimulationSignalManager.get_instance().pause_simulation.emit(True)

        self._set_inputs_enabled(False)
        self._robot_service.suspend_serial()

        com = self._robot_service.get_com()
        self.kinematics_worker.send_home_direct(com)

    def exit_kinematics_mode(self):

        if not self._mode_active:
            return

        self._mode_active = False
        self.kinematics_worker.stop()

        SimulationSignalManager.get_instance().resume_simulation.emit()

        if self._robot_service is not None:
            self._robot_service.resume_serial()

        self._set_inputs_enabled(False)
    def _update_simulation_with_positions(self, positions):
        """Procesa y emite posiciones suavizadas a la simulación."""
        positions[4]= positions[4]*-1
        positions[5]= positions[5]*-1 
        #1. Aplicar filtro EMA
        alpha = 0.1
        if self._smoothed_pos is None:
            self._smoothed_pos = positions
        else:
            self._smoothed_pos = [
                (alpha * new) + ((1 - alpha) * old)
                for new, old in zip(positions, self._smoothed_pos)
            ]
        
        # 2. Enviar a la simulación
        SimulationSignalManager.get_instance().update_robot_from_kinematics.emit(self._smoothed_pos)


    def execute_kinematics(self):

        if not self._mode_active:
            return

        if not self.kinematics_worker.isRunning():
            return

        coords = self.kinematics_widget.get_coordinates()
        gains = self.kinematics_widget.get_pid_gains()
        self.kinematics_worker.set_pid_gains(
            gains["kp"], gains["ki"], gains["kd"])

        tx_raw = coords['x']
        ty_raw = coords['y']
        tz_raw = coords['z']

        tx = tx_raw + 110
        ty = ty_raw
        tz = tz_raw
        tz = corregir_z(tx, ty, tz)
        tx, ty = corregir_xy(tx, ty)

        self._set_inputs_enabled(False)
        self.kinematics_widget.set_control_state("running")
        
        # Asegurar que el worker no esté pausado antes de enviar la tarea
        self.kinematics_worker.resume()
        
        if self._graph_controller:
            self._graph_controller.reset_cartesian_plot()
        
        self.kinematics_worker.execute_target(tx, ty, tz)

    @pyqtSlot(int)
    def _on_claw_changed(self, value):
        self._claw_mm = value
        if self._mode_active:
            self.kinematics_worker.set_claw_value(value)

    @pyqtSlot(str)
    def _on_status_changed(self, message):
        print(f"[Cinematica] {message}")

    @pyqtSlot()
    def _on_movement_finished(self):
        if self._mode_active:
            self._set_inputs_enabled(True)
            self.kinematics_widget.set_control_state("idle")

    @pyqtSlot()
    def _on_input_enabled(self):
        if self._mode_active:
            self._set_inputs_enabled(True)
            self.kinematics_widget.set_control_state("idle")

    @pyqtSlot(list)
    def _on_joint_update(self, joints):
        # Usar la lógica centralizada para procesar y enviar las posiciones del worker
        self._update_simulation_with_positions(joints)

    @pyqtSlot(object)
    def _on_global_mode_changed(self, mode):
        if mode != Modes.KINEMATIC and self._mode_active:
            self.exit_kinematics_mode()

    def _on_restart(self):
        # 1. Bloquear inputs inmediatamente
        self._set_inputs_enabled(False)
        self.kinematics_widget.set_control_state("homing")
        
        # Resetear valor de garra
        self._claw_mm = 30
        self.kinematics_widget.reset_claw_value()
        
        # 2. Resetear el worker (abortar PID y limpiar cola)
        self.kinematics_worker.reset_state()
        self.kinematics_worker.resume()
        
        # 3. Resetear gráfica
        if self._graph_controller:
            self._graph_controller.reset_cartesian_plot()
            
        # 4. Enviar HOME (la señal input_enabled del worker re-habilitará la UI)
        self.kinematics_worker.send_home()

    def _set_inputs_enabled(self, enabled):
        self.kinematics_widget.coordinates_button.setEnabled(enabled)
        self.kinematics_widget.set_inputs_enabled(enabled)

    def get_widget(self):
        return self.kinematics_widget

    def get_worker(self):
        return self.kinematics_worker

    def cleanup(self):
        self.exit_kinematics_mode()
        self.kinematics_worker.wait(3000)
