"""
Módulo que define el comportamiento de los botones de acción de la interfaz.

Gestiona las acciones principales del flujo de trabajo: iniciar, pausar,
detener y reiniciar, así como la alternancia de visibilidad de paneles
y la inicialización de ventanas de calibración.
"""

from PyQt6.QtCore import pyqtSlot
from src.services.data.enums import Modes
from src.services.data.signals import (
    KinematicsSignalManager, SearchSignalManager, ConfigSignalManager,
    SimulationSignalManager, PhysicalSignalManager, SlidersSignalManager
)


class MainActionsMixin:
    """
    Mixin que gestiona el comportamiento de las secciones de la interfaz.

    Implementa las acciones de control de flujo (start/pause/stop/reset),
    visibilidad de paneles (cámara, modelo 3D, gráficos, controles) e
    inicialización de ventanas secundarias de calibración.
    """

    def __init__(self):
        self.hab_simulation = ConfigSignalManager.get_instance().get_param(
            "settings.json", "simulation", "activated", default=True)

    def start(self):
        """
        Inicia la simulación, cámara, gráficos y servicios del robot.

        Deshabilita el botón de inicio y habilita pausa/stop.
        """
        if self.hab_simulation:
            # Solicitar inicio vía DataController (Bus Global)
            SimulationSignalManager.get_instance().start_request.emit()

        self.simulation_action.setEnabled(False)

        if self.camera_paused:
            self.camera_controller.resume_video()

        self.camera_controller.show_controls()
        self.com_submenu.setEnabled(True)

        if self.connected_to_robot:
            PhysicalSignalManager.get_instance().start_request.emit()

        self.graph_controller.start()

        self.start_action.setEnabled(False)
        self.start_action.setChecked(True)
        self.pause_action.setEnabled(True)
        self.pause_action.setChecked(False)
        self.stop_action.setEnabled(True)
        self.stop_action.setChecked(False)

        self.stopped = False

    def pause(self):
        """
        Pausa la simulación, cámara y gráficos.

        Detiene el servicio del robot si está conectado.
        Habilita el botón de inicio y deshabilita pausa.
        """
        SimulationSignalManager.get_instance().pause_request.emit(True)

        self.camera_controller.pause_video()
        self.camera_paused = True

        self.graph_controller.pause()

        # El RobotController manejará la pausa si escucha el bus, o podemos enviar stop
        if self.connected_to_robot:
            PhysicalSignalManager.get_instance().stop_request.emit()

        self.pause_action.setEnabled(False)
        self.pause_action.setChecked(True)
        self.start_action.setEnabled(True)
        self.start_action.setChecked(False)

    def stop(self):
        """
        Detiene la simulación, cámara y gráficos.

        Restaura el estado de reposo de la interfaz.
        """
        if self.hab_simulation:
            SimulationSignalManager.get_instance().stop_request.emit()

        self.simulation_action.setEnabled(True)
        self.model_action.setEnabled(True)

        self.camera_controller.stop_video()

        self.graph_controller.stop()

        if self.connected_to_robot:
            PhysicalSignalManager.get_instance().stop_request.emit()

        self.start_action.setEnabled(True)
        self.start_action.setChecked(False)
        self.pause_action.setEnabled(False)
        self.pause_action.setChecked(False)
        self.stop_action.setEnabled(False)
        self.stop_action.setChecked(True)

        self.stopped = True

    def reset(self):
        """
        Reinicia los valores de los sliders a su posición central.
        """
        self.sliders_controller.reset_controls()

    @pyqtSlot(bool)
    def toggle_visibility_camera_event(self, checked: bool):
        """
        Alterna la visibilidad del dock de la cámara.

        Args:
            checked (bool): True para mostrar el panel.
        """
        self.cameraDock.toggleView(checked)
        ConfigSignalManager.get_instance().request_change(
            "settings.json", ["content", "camera"], checked)

    @pyqtSlot(bool)
    def toggle_visibility_model_event(self, checked: bool):
        """
        Alterna la visibilidad del dock del modelo 3D.

        Args:
            checked (bool): True para mostrar el panel.
        """
        self.modelDock.toggleView(checked)
        ConfigSignalManager.get_instance().request_change(
            "settings.json", ["content", "model"], checked)

    @pyqtSlot(bool)
    def toggle_visibility_graphs_event(self, checked: bool):
        """
        Alterna la visibilidad del dock de gráficos.

        Args:
            checked (bool): True para mostrar el panel.
        """
        self.graphsDock.toggleView(checked)
        ConfigSignalManager.get_instance().request_change(
            "settings.json", ["content", "graphs"], checked)

    @pyqtSlot(bool)
    def toggle_visibility_controls_event(self, checked: bool):
        """
        Alterna la visibilidad del dock de controles.

        Args:
            checked (bool): True para mostrar el panel.
        """
        self.controlsDock.toggleView(checked)
        ConfigSignalManager.get_instance().request_change(
            "settings.json", ["content", "controls"], checked)

    def initiate_camera_calibration(self):
        """
        Inicializa la ventana de calibración de cámara.

        Detiene la cámara de la interfaz principal si está corriendo.
        Importación local para evitar círculos.
        """
        from src.features.calibration import CameraCalibrationWindow

        self.camera_controller.stop_video()

        self.calibration_window = CameraCalibrationWindow()
        self.calibration_window.show()

    def initiate_color_calibration(self):
        """
        Inicializa la ventana de calibración de colores.

        Detiene la cámara de la interfaz principal si está corriendo.
        Importación local para evitar círculos.
        """
        from src.features.color import ColorWindow

        self.camera_controller.stop_video()

        self.color_window = ColorWindow()
        self.color_window.show()

    @pyqtSlot(bool)
    def toggle_activation_simulation_event(self, checked: bool):
        """
        Habilita o deshabilita la activación de la simulación física.

        Args:
            checked (bool): True para activar la simulación.
        """
        self.hab_simulation = checked
        ConfigSignalManager.get_instance().request_change("settings.json", ["simulation",
                                                          "activated"], checked)

    @pyqtSlot(bool)
    def toggle_shadows_event(self, checked: bool):
        ConfigSignalManager.get_instance().request_change(
            "settings.json", ["simulation", "shadows"], checked)

    @pyqtSlot(bool)
    def toggle_grid_event(self, checked: bool):
        ConfigSignalManager.get_instance().request_change(
            "settings.json", ["simulation", "grid"], checked)

    @pyqtSlot(bool)
    def toggle_axes_event(self, checked: bool):
        ConfigSignalManager.get_instance().request_change(
            "settings.json", ["simulation", "axes"], checked)

    @pyqtSlot(bool)
    def toggle_labels_event(self, checked: bool):
        ConfigSignalManager.get_instance().request_change(
            "settings.json", ["simulation", "labels"], checked)

    @pyqtSlot(bool)
    def toggle_aa_event(self, checked: bool):
        ConfigSignalManager.get_instance().request_change(
            "settings.json", ["simulation", "aa"], checked)

    @pyqtSlot(bool)
    def toggle_charuco_search(self, checked: bool):
        """
        Alterna la búsqueda de tablero ChArUco en la cámara.

        Args:
            checked (bool): True para activar la detección.
        """
        SearchSignalManager.get_instance().set_charuco(checked)

    @pyqtSlot(bool)
    def toggle_sphere_search(self, checked: bool):
        """
        Alterna la búsqueda de esferas de color en la cámara.

        Args:
            checked (bool): True para activar la detección.
        """
        SearchSignalManager.get_instance().set_circle(checked)

    def toggle_sliders_controls(self, checked: bool):
        """
        Alterna la visibilidad del panel de control manual (sliders).

        Args:
            checked (bool): True para mostrar sliders.
        """
        if checked:
            self.sliders_controller.get_widget().show()
            self.kinematics_controller.get_widget().set_vertical_layout()
            SlidersSignalManager.get_instance().change_mode_signal.emit(
                Modes.SLIDERS)
        else:
            self.sliders_controller.get_widget().hide()
            self.kinematics_controller.get_widget().set_horizontal_layout()
        ConfigSignalManager.get_instance().request_change(
            'settings.json', ["mode", 'sliders'], checked)

    def toggle_kinematics_controls(self, checked: bool):
        """
        Alterna la visibilidad del panel de control cinemático.

        Args:
            checked (bool): True para mostrar cinemática.
        """
        if checked:
            self.kinematics_controller.get_widget().show()
            KinematicsSignalManager.get_instance().change_mode_signal.emit(
                Modes.KINEMATIC)
        else:
            self.kinematics_controller.get_widget().hide()
        ConfigSignalManager.get_instance().request_change(
            'settings.json', ["mode", 'kinematics'], checked)

    def toggle_pick_place_controls(self, checked: bool):
        """
        Alterna la visibilidad del panel de control pick and place.

        Args:
            checked (bool): True para mostrar el panel de controles
        """
        if checked:
            SimulationSignalManager.get_instance().change_mode_signal.emit(
                Modes.PICK_PLACE)
        from src.services.data.signals import PickPlaceSignalManager
        PickPlaceSignalManager.get_instance().set_state(checked)

        self.toggle_visibility_controls_event(not checked)
        self.controls_action.setChecked(not checked)
        self.controls_action.setEnabled(not checked)
        ConfigSignalManager.get_instance().request_change(
            'settings.json', ["mode", 'pick_place'], checked)

    def connect_robot(self):
        """
        Inicia la conexión con el microcontrolador en el puerto COM seleccionado.
        """
        if not self.com:
            print("Error: Dispositivo no detectado")
            return
        self.connected_to_robot = True
        self.init_openbotv(self.com)
        self.com_connected_label.setText(self.com)
