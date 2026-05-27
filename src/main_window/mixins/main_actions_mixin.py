"""
Modulo que define el comportamiento de los botones de accion de la interfaz.

Gestiona las acciones principales del flujo de trabajo: iniciar, pausar,
detener y reiniciar, asi como la alternancia de visibilidad de paneles
y la inicializacion de ventanas de calibracion.
"""

from PyQt6.QtCore import pyqtSlot
from src.services.data.signals import SearchSignalManager, ConfigSignalManager


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
            self.simulation_controller.start_simulation()

        self.simulation_action.setEnabled(False)

        if self.camera_paused:
            self.camera_controller.resume_video()

        self.camera_controller.show_controls()
        self.com_submenu.setEnabled(True)

        if self.connected_to_robot:
            self.robot_controller.request_processing.connect(
                self.robot_service.move_to)
            self.robot_service.start_service()

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
        if self.simulation_controller is not None:
            self.simulation_controller.pause_simulation()

        self.camera_controller.pause_video()
        self.camera_paused = True

        self.graph_controller.pause()

        if self.connected_to_robot:
            self.robot_service.stop_service()

        self.pause_action.setEnabled(False)
        self.pause_action.setChecked(True)
        self.start_action.setEnabled(True)
        self.start_action.setChecked(False)

    def stop(self):
        """
        Detiene la simulacion, camara y graficos.

        Restaura el estado de reposo de la interfaz.
        """
        if self.simulation_controller is not None and self.hab_simulation:
            self.simulation_controller.stop_simulation()

        self.simulation_action.setEnabled(True)
        self.model_action.setEnabled(True)

        self.camera_controller.stop_video()

        self.graph_controller.stop()

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
        Alterna la visibilidad del panel de camara.

        Args:
            checked (bool): True para mostrar el panel.
        """
        self.cameraBox.setVisible(checked)
        ConfigSignalManager.get_instance().request_change(
            "settings.json", "content", "camera", value=checked)
        self.check_handle_visibility()

    @pyqtSlot(bool)
    def toggle_visibility_model_event(self, checked: bool):
        """
        Alterna la visibilidad del panel del modelo 3D.

        Args:
            checked (bool): True para mostrar el panel.
        """
        self.modelBox.setVisible(checked)
        ConfigSignalManager.get_instance().request_change(
            "settings.json", "content", "model", value=checked)
        self.check_handle_visibility()

    @pyqtSlot(bool)
    def toggle_visibility_graphs_event(self, checked: bool):
        """
        Alterna la visibilidad del panel de graficos.

        Args:
            checked (bool): True para mostrar el panel.
        """
        self.graphsBox.setVisible(checked)
        ConfigSignalManager.get_instance().request_change(
            "settings.json", "content", "graphs", value=checked)
        self.check_handle_visibility()

    @pyqtSlot(bool)
    def toggle_visibility_controls_event(self, checked: bool):
        """
        Alterna la visibilidad del panel de controles.

        Args:
            checked (bool): True para mostrar el panel.
        """
        self.controlsBox.setVisible(checked)
        ConfigSignalManager.get_instance().request_change(
            "settings.json", "content", "controls", value=checked)
        self.check_handle_visibility()

    def check_handle_visibility(self):
        """
        Ajusta el handle del splitter segun la visibilidad de las secciones.

        Oculta el handle cuando solo hay una seccion visible.
        """
        visible_1 = any(
            self.contentSplitter.widget(0).widget(j).isVisible()
            for j in range(self.contentSplitter.widget(0).count())
        )

        visible_2 = any(
            self.contentSplitter.widget(1).widget(j).isVisible()
            for j in range(self.contentSplitter.widget(1).count())
        )
        has_both = visible_1 and visible_2

        self.contentSplitter.setHandleWidth(8 if has_both else 0)
        self.contentSplitter.handle(1).setEnabled(has_both)

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
    def toggle_charuco_search(self, checked: bool):
        """
        Alterna la busqueda de patrones ChArUco en la camara.

        Args:
            checked (bool): True para activar la deteccion.
        """
        SearchSignalManager().get_instance().set_charuco(checked)
        ConfigSignalManager.get_instance().request_change(
            "settings.json", "camera", "charuco", value=checked)

    @pyqtSlot(bool)
    def toggle_sphere_search(self, checked: bool):
        """
        Alterna la busqueda de esferas de color en la camara.

        Args:
            checked (bool): True para activar la deteccion.
        """
        SearchSignalManager().get_instance().set_circle(checked)
        ConfigSignalManager.get_instance().request_change(
            "settings.json", "camera", "circle", value=checked)

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
