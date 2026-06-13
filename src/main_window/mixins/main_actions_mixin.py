"""
Modulo que define el comportamiento de los botones de accion de la interfaz.

Gestiona las acciones principales del flujo de trabajo: iniciar, pausar,
detener y reiniciar, asi como la alternancia de visibilidad de paneles
y la inicializacion de ventanas de calibracion.
"""

from PyQt6.QtCore import pyqtSlot
from src.services.data.signals import (
    SearchSignalManager, ConfigSignalManager,
    SimulationSignalManager, PhysicalSignalManager
)


class MainActionsMixin:
    """
    Mixin que gestiona el comportamiento de las secciones de la interfaz.

    Implementa las acciones de control de flujo (start/pause/stop/reset),
    visibilidad de paneles (camara, modelo 3D, graficos, controles) e
    inicializacion de ventanas secundarias de calibracion.
    """

    def __init__(self):
        self.hab_simulation = ConfigSignalManager.get_instance().get_param(
            "settings.json", "simulation", "activated", default=True)

    def start(self):
        """
        Inicia la simulacion, camara, graficos y servicios del robot.

        Deshabilita el boton de inicio y habilita pausa/stop.
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
        Pausa la simulacion, camara y graficos.

        Detiene el servicio del robot si esta conectado.
        Habilita el boton de inicio y deshabilita pausa.
        """
        SimulationSignalManager.get_instance().pause_request.emit(True)

        self.camera_controller.pause_video()
        self.camera_paused = True

        self.graph_controller.pause()

        # El RobotController manejara la pausa si escucha el bus, o podemos enviar stop
        if self.connected_to_robot:
            PhysicalSignalManager.get_instance().stop_request.emit()

        self.pause_action.setEnabled(False)
        self.pause_action.setChecked(True)
        self.start_action.setEnabled(True)
        self.start_action.setChecked(False)

    def stop(self):
        """
        Detiene la simulacion, camara y graficos.

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
        Reinicia los valores de los sliders a su posicion central.
        """
        self.sliders_controller.reset_controls()

    @pyqtSlot(bool)
    def toggle_visibility_camera_event(self, checked: bool):
        """
        Alterna la visibilidad del dock de la camara.

        Args:
            checked (bool): True para mostrar el panel.
        """
        self.cameraDock.toggleView(checked)
        ConfigSignalManager.get_instance().request_change(
            "settings.json", "content", "camera", value=checked)

    @pyqtSlot(bool)
    def toggle_visibility_model_event(self, checked: bool):
        """
        Alterna la visibilidad del dock del modelo 3D.

        Args:
            checked (bool): True para mostrar el panel.
        """
        self.modelDock.toggleView(checked)
        ConfigSignalManager.get_instance().request_change(
            "settings.json", "content", "model", value=checked)

    @pyqtSlot(bool)
    def toggle_visibility_graphs_event(self, checked: bool):
        """
        Alterna la visibilidad del dock de graficos.

        Args:
            checked (bool): True para mostrar el panel.
        """
        self.graphsDock.toggleView(checked)
        ConfigSignalManager.get_instance().request_change(
            "settings.json", "content", "graphs", value=checked)

    @pyqtSlot(bool)
    def toggle_visibility_controls_event(self, checked: bool):
        """
        Alterna la visibilidad del dock de controles.

        Args:
            checked (bool): True para mostrar el panel.
        """
        self.controlsDock.toggleView(checked)
        ConfigSignalManager.get_instance().request_change(
            "settings.json", "content", "controls", value=checked)

    def initiate_camera_calibration(self):
        """
        Inicializa la ventana de calibracion de camara.

        Detiene la camara de la interfaz principal si esta corriendo.
        Importacion local para evitar circulos.
        """
        from src.features.calibration import CameraCalibrationWindow

        self.camera_controller.stop_video()

        self.calibration_window = CameraCalibrationWindow()
        self.calibration_window.show()

    def initiate_color_calibration(self):
        """
        Inicializa la ventana de calibracion de colores.

        Detiene la camara de la interfaz principal si esta corriendo.
        Importacion local para evitar circulos.
        """
        from src.features.color import ColorWindow

        self.camera_controller.stop_video()

        self.color_window = ColorWindow()
        self.color_window.show()

    @pyqtSlot(bool)
    def toggle_activation_simulation_event(self, checked: bool):
        """
        Habilita o deshabilita la activacion de la simulacion fisica.

        Args:
            checked (bool): True para activar la simulacion.
        """
        self.hab_simulation = checked
        ConfigSignalManager.get_instance().request_change("settings.json", "simulation",
                                                          "activated", value=checked)

    @pyqtSlot(bool)
    def toggle_shadows_event(self, checked: bool):
        ConfigSignalManager.get_instance().request_change("settings.json", "simulation", "shadows", value=checked)

    @pyqtSlot(bool)
    def toggle_grid_event(self, checked: bool):
        ConfigSignalManager.get_instance().request_change("settings.json", "simulation", "grid", value=checked)

    @pyqtSlot(bool)
    def toggle_axes_event(self, checked: bool):
        ConfigSignalManager.get_instance().request_change("settings.json", "simulation", "axes", value=checked)

    @pyqtSlot(bool)
    def toggle_labels_event(self, checked: bool):
        ConfigSignalManager.get_instance().request_change("settings.json", "simulation", "labels", value=checked)

    @pyqtSlot(bool)
    def toggle_aa_event(self, checked: bool):
        ConfigSignalManager.get_instance().request_change("settings.json", "simulation", "aa", value=checked)

    @pyqtSlot(bool)
    def toggle_charuco_search(self, checked: bool):
        """
        Alterna la busqueda de tablero ChArUco en la camara.

        Args:
            checked (bool): True para activar la deteccion.
        """
        SearchSignalManager.get_instance().set_charuco(checked)

    @pyqtSlot(bool)
    def toggle_sphere_search(self, checked: bool):
        """
        Alterna la busqueda de esferas de color en la camara.

        Args:
            checked (bool): True para activar la deteccion.
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
        else:
            self.sliders_controller.get_widget().hide()
            self.kinematics_controller.get_widget().set_horizontal_layout()
        ConfigSignalManager.get_instance().request_change(
            'settings.json', "mode", 'sliders', value=checked)

    def toggle_kinematics_controls(self, checked: bool):
        """
        Alterna la visibilidad del panel de control cinematico.

        Args:
            checked (bool): True para mostrar cinematica.
        """
        if checked:
            self.kinematics_controller.get_widget().show()
        else:
            self.kinematics_controller.get_widget().hide()
        ConfigSignalManager.get_instance().request_change(
            'settings.json', "mode", 'kinematics', value=checked)

    def toggle_pick_place_controls(self, checked: bool):
        """
        Alterna la visibilidad del panel de control pick and place.

        Args:
            checked (bool): True para mostrar el panel de controles
        """
        from src.services.data.signals import PickPlaceSignalManager
        PickPlaceSignalManager.get_instance().set_state(checked)
        
        self.toggle_visibility_controls_event(not checked)
        self.controls_action.setChecked(not checked)
        self.controls_action.setEnabled(not checked)
        ConfigSignalManager.get_instance().request_change(
            'settings.json', "mode", 'pick_place', value=checked)

    def connect_robot(self):
        """
        Inicia la conexion con el microcontrolador en el puerto COM seleccionado.
        """
        if not self.com:
            print("Error: Dispositivo no detectado")
            return
        self.connected_to_robot = True
        self.init_openbotv(self.com)
        self.com_connected_label.setText(self.com)
