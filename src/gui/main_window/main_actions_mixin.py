""" Modulo donde se define el comportamiento de los botones presentes en la interfaz a excepción de
    los ubicados en la barra de menu.
"""
from PyQt6.QtCore import pyqtSlot
from data import SearchSignalManager
from data import config_manager as cfg
from ..sliders_interface import SlidersWidget


class MainActionsMixin:
    """ Gestiona el comportamiento de las secciones de la interfaz frente a distintas acciones de 
        los botones como iniciar, pausar o detener la ejecución.
    """

    def __init__(self):
        self.hab_simulation = cfg.get("setting.json", "simulation")

    def start(self):
        """ Inicia o detiene la simulation en caso de ser la primera vez instancia la clase
            SimInterface, también cambia los colores e iconos del botón.
        """
        if self.hab_simulation:
            self.simulation_interface.start_simulation()

        self.simulation_action.setEnabled(False)

        if self.camera_paused:
            self.camera_interface.resume_video()

        self.camera_interface.buttons_widget.show()
        self.camera_interface.buttons_widget.raise_()
        self.com_submenu.setEnabled(True)

        if self.connected_to_robot:
            self.robot_controller.start()
            self.openbotv.start()

        self.graph_interface.start()

        self.stop_button.show()
        self.pause_button.show()
        self.start_button.hide()

        self.stopped = False

    def pause(self):
        """ Pone en pausa la simulation si existe y la cámara
        """
        if self.simulation_interface is not None:
            self.simulation_interface.pause_simulation()

        self.camera_interface.pause_video()
        self.camera_paused = True

        self.graph_interface.pause()

        if self.connected_to_robot:
            self.openbotv.stop()

        self.pause_button.hide()
        self.start_button.show()

    def stop(self):
        """ "Detiene" la simulation y apaga la cámara
        """
        if self.simulation_interface is not None and self.hab_simulation:
            self.simulation_interface.stop_simulation()

        self.simulation_action.setEnabled(True)
        self.model_action.setEnabled(True)

        self.camera_interface.stop_video()

        self.graph_interface.stop()

        self.stop_button.hide()
        self.pause_button.hide()
        self.start_button.show()

        self.stopped = True

    def reset(self):
        """ Reinicia los valores de los sliders a 0
        """
        SlidersWidget.restart_sliders()

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
        from ..calibration_window import CameraCalibrationWindow

        self.clear_camera_selection()
        self.camera_interface.stop_video()

        self.calibration_window = CameraCalibrationWindow()
        self.calibration_window.show()
        signal_manager = SearchSignalManager().get_instance()
        signal_manager.set_charuco(True)
        signal_manager.set_sphere(False)

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
        cfg.set_value("settings.json", "camera", "charuco", value=checked)

    @pyqtSlot(bool)
    def toggle_sphere_search(self, checked: bool):
        SearchSignalManager().get_instance().set_sphere(checked)
        cfg.set_value("settings.json", "camera", "sphere", value=checked)

    def toggle_sliders_controls(self, checked: bool):
        if checked:
            self.slider_widget.show()
            self.kinematics_widget.set_vertical_layout()
        else:
            self.slider_widget.hide()
            self.kinematics_widget.set_horizontal_layout()
        cfg.set_value('settings.json', "mode", 'sliders', value=checked)

    def toggle_kinematics_controls(self, checked: bool):
        if checked:
            self.kinematics_widget.show()
        else:
            self.kinematics_widget.hide()
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
