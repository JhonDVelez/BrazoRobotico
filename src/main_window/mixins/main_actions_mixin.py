""" Modulo donde se define el comportamiento de los botones presentes en la interfaz a excepción de
    los ubicados en la barra de menu.
"""
from PyQt6.QtCore import pyqtSlot
from src.services.data.signals import SearchSignalManager
from src.services.data import config_manager as cfg


class MainActionsMixin:
    """ Gestiona el comportamiento de las secciones de la interfaz frente a distintas acciones de 
        los botones como iniciar, pausar o detener la ejecución.
    """

    def __init__(self):
        self.hab_simulation = cfg.get("setting.json", "simulation")

    def start(self):
        """ Inicia o detiene la simulation en caso de ser la primera vez instancia la clase
            SimInterface, también deshabilita los botones de control.
        """
        if self.hab_simulation:
            self.simulation_controller.start_simulation()

        self.simulation_action.setEnabled(False)

        if self.camera_paused:
            self.camera_controller.resume_video()

        self.camera_controller.show_controls()
        self.com_submenu.setEnabled(True)

        if self.connected_to_robot:
            self.robot_controller.request_processing.connect(self.robot_service.move_to)
            self.robot_service.start_service()

        self.graph_controller.start()

        # Deshabilitar el botón de inicio y habilitar pausa y stop
        self.start_action.setEnabled(False)
        self.start_action.setChecked(True)
        self.pause_action.setEnabled(True)
        self.pause_action.setChecked(False)
        self.stop_action.setEnabled(True)
        self.stop_action.setChecked(False)

        self.stopped = False

    def pause(self):
        """ Pone en pausa la simulation si existe y la cámara
        """
        if self.simulation_controller is not None:
            self.simulation_controller.pause_simulation()

        self.camera_controller.pause_video()
        self.camera_paused = True

        self.graph_controller.pause()

        if self.connected_to_robot:
            self.robot_service.stop_service()

        # Habilitar inicio y deshabilitar pausa
        self.pause_action.setEnabled(False)
        self.pause_action.setChecked(True)
        self.start_action.setEnabled(True)
        self.start_action.setChecked(False)

    def stop(self):
        """ "Detiene" la simulation y apaga la cámara
        """
        if self.simulation_controller is not None and self.hab_simulation:
            self.simulation_controller.stop_simulation()

        self.simulation_action.setEnabled(True)
        self.model_action.setEnabled(True)

        self.camera_controller.stop_video()

        self.graph_controller.stop()

        # Habilitar inicio y deshabilitar pausa y stop
        self.start_action.setEnabled(True)
        self.start_action.setChecked(False)
        self.pause_action.setEnabled(False)
        self.pause_action.setChecked(False)
        self.stop_action.setEnabled(False)
        self.stop_action.setChecked(True)

        self.stopped = True

    def reset(self):
        """ Reinicia los valores de los sliders a 0
        """
        self.sliders_controller.reset_controls()

    @pyqtSlot(bool)
    def toggle_visibility_camera_event(self, checked: bool):
        """ Alterna la visibilidad del widget de la cámara y actualiza el texto del botón
            correspondiente.

        Args:
            cameraBox (PyQt6.QtWidgets.QGroupBox): El widget que contiene la cámara.
        """

        self.cameraBox.setVisible(checked)
        cfg.set_value("settings.json", "content", "camera", value=checked)
        self.check_handle_visibility()

    @pyqtSlot(bool)
    def toggle_visibility_model_event(self, checked: bool):
        """ Alterna la visibilidad del widget del modelo 3D y actualiza el texto del botón
            correspondiente.

        Args:
            modelBox (PyQt6.QtWidgets.QGroupBox): El widget que contiene el modelo 3D.
        """
        self.modelBox.setVisible(checked)
        cfg.set_value("settings.json", "content", "model", value=checked)
        self.check_handle_visibility()

    @pyqtSlot(bool)
    def toggle_visibility_graphs_event(self, checked: bool):
        """ Habilita o deshabilita la visualización del modelo 3D de QtQuick mediante la acción en 
            la barra de menu.
        """
        self.graphsBox.setVisible(checked)
        cfg.set_value("settings.json", "content", "graphs", value=checked)
        self.check_handle_visibility()

    @pyqtSlot(bool)
    def toggle_visibility_controls_event(self, checked: bool):
        """ Habilita o deshabilita la visualización del modelo 3D de QtQuick mediante la acción en 
            la barra de menu.
        """

        self.controlsBox.setVisible(checked)
        cfg.set_value("settings.json", "content", "controls", value=checked)
        self.check_handle_visibility()

    def check_handle_visibility(self):
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
        """ Inicializa la ventana de calibración y detiene la cámara de la interfaz principal 
            si esta corriendo
            Importa la clase de forma local vara evitar importaciones circulares
        """
        from src.features.calibration import CameraCalibrationWindow

        self.camera_controller.stop_video()

        self.calibration_window = CameraCalibrationWindow()
        self.calibration_window.show()

    def initiate_color_calibration(self):
        """ Inicializa la ventana de calibración de colores y detiene la cámara de la interfaz 
            principal si esta corriendo
            Importa la clase de forma local para evitar importaciones circulares
        """
        from src.features.color import ColorWindow

        self.camera_controller.stop_video()

        self.color_window = ColorWindow()
        self.color_window.show()

    @pyqtSlot(bool)
    def toggle_activation_simulation_event(self, checked: bool):
        """ Habilita o deshabilita la visualización del modelo 3D de QtQuick mediante la acción en 
            la barra de menu.
        """
        self.hab_simulation = checked
        cfg.set_value("settings.json", "simulation",
                      "activated", value=checked)

    @pyqtSlot(bool)
    def toggle_charuco_search(self, checked: bool):
        SearchSignalManager().get_instance().set_charuco(checked)

    @pyqtSlot(bool)
    def toggle_sphere_search(self, checked: bool):
        SearchSignalManager().get_instance().set_ellipse(checked)

    def toggle_sliders_controls(self, checked: bool):
        if checked:
            self.sliders_controller.get_widget().show()
            self.kinematics_controller.get_widget().set_vertical_layout()
        else:
            self.sliders_controller.get_widget().hide()
            self.kinematics_controller.get_widget().set_horizontal_layout()
        cfg.set_value('settings.json', "mode", 'sliders', value=checked)

    def toggle_kinematics_controls(self, checked: bool):
        if checked:
            self.kinematics_controller.get_widget().show()
        else:
            self.kinematics_controller.get_widget().hide()
        cfg.set_value('settings.json', "mode", 'kinematics', value=checked)

    def connect_robot(self):
        """ Inicia la colección con el microcontrolador en el puerto de comunicación seleccionado
        """
        if not self.com:
            print("Error: Dispositivo no detectado")
            return
        self.connected_to_robot = True
        self.init_openbotv(self.com)
        self.com_connected_label.setText(self.com)
