""" Modulo donde se define el comportamiento de los botones presentes en la interfaz a excepción de
    los ubicados en la barra de menu.
"""
from ..sliders_interface import SlidersWidget


class MainActionsMixin:
    """ Gestiona el comportamiento de las secciones de la interfaz frente a distintas acciones de 
        los botones como iniciar, pausar o detener la ejecución.
    """

    def __init__(self):
        self.hab_simulation = None

    def start(self):
        """ Inicia o detiene la simulation en caso de ser la primera vez instancia la clase
            SimInterface, también cambia los colores e iconos del botón.
        """
        if self.hab_simulation:
            if not self.modelBox.isVisible():
                self.toggle_visibility_model_event()
            self.simulation_interface.start_simulation()
            self.model_action.setEnabled(True)
        else:
            if self.modelBox.isVisible():
                self.toggle_visibility_model_event()
            self.model_action.setEnabled(False)

        if self.camera_paused:
            self.camera_interface.resume_video()

        self.camera_interface.video_button.show()
        self.camera_interface.video_button.raise_()
        self.simulation_action.setEnabled(False)
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
        self.camera_interface.video_button.hide()

        self.graph_interface.stop()

        self.stop_button.hide()
        self.pause_button.hide()
        self.start_button.show()

        self.stopped = True

    def reset(self):
        """ Reinicia los valores de los sliders a 0
        """
        SlidersWidget.restart_sliders()

    def toggle_visibility_camera_event(self):
        """ Alterna la visibilidad del widget de la cámara y actualiza el texto del botón
            correspondiente.

        Args:
            cameraBox (PyQt6.QtWidgets.QGroupBox): El widget que contiene la cámara.
        """
        if self.cameraBox.isVisible():
            self.cameraBox.hide()
            self.camera_action.setText("Mostrar Cámara")
        else:
            self.cameraBox.show()
            self.camera_action.setText("Ocultar Cámara")

    def toggle_visibility_model_event(self):
        """ Alterna la visibilidad del widget del modelo 3D y actualiza el texto del botón
            correspondiente.

        Args:
            modelBox (PyQt6.QtWidgets.QGroupBox): El widget que contiene el modelo 3D.
        """
        if self.modelBox.isVisible():
            self.modelBox.hide()
            self.model_action.setText("Mostrar Modelo 3D")
        else:
            self.modelBox.show()
            self.model_action.setText("Ocultar Modelo 3D")

    def initiate_camera_calibration(self):
        from ..calibration_window import CameraCalibrationWindow

        self.camera_interface.stop_video()

        self.calibration_window = CameraCalibrationWindow()
        self.calibration_window.show()

    def toggle_activation_model_event(self):
        """ Habilita o deshabilita la visualización del modelo 3D de QtQuick mediante la acción en 
            la barra de menu.
        """
        if self.hab_simulation:
            self.hab_simulation = False
            self.simulation_action.setText("Habilitar simulación")
        else:
            self.hab_simulation = True
            self.simulation_action.setText("Deshabilitar simulación")

    def connect_robot(self):
        """ Inicia la colección con el microcontrolador en el puerto de comunicación seleccionado
        """
        if not self.com:
            print("Error: Dispositivo no detectado")
            return
        self.connected_to_robot = True
        self.init_openbotv(self.com)
        self.com_connected_label.setText(self.com)
