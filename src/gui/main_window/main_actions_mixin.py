""" Modulo donde se define el comportamiento de los botones presentes en la interfaz a excepción de
    los ubicados en la barra de menu.
"""
from ..sliders_interface import SlidersWidget


class MainActionsMixin:
    """ Gestiona el comportamiento de las secciones de la interfaz frente a distintas acciones de 
        los botones como iniciar, pausar o detener la ejecución.
        Funciona como un controlador de estados para sincronizar múltiples interfaces (SIM, Cámara, Gráficas).
    """

    def __init__(self):
        # Flag booleano para determinar si la simulación 3D está habilitada por el usuario
        self.hab_simulation = None

    def start(self):
        """ Inicia o detiene la simulation en caso de ser la primera vez instancia la clase
            SimInterface, también cambia los colores e iconos del botón.
            Coordina el encendido simultáneo de la cámara, simulación, gráficas y comunicación serial.
        """
        # --- Gestión de la Simulación 3D ---
        if self.hab_simulation:
            # Asegura que el contenedor visual sea visible si la simulación está activa
            if not self.modelBox.isVisible():
                self.toggle_visibility_model_event()
            self.simulation_interface.start_simulation()
            self.model_action.setEnabled(True)
        else:
            # Oculta el contenedor si la simulación está deshabilitada
            if self.modelBox.isVisible():
                self.toggle_visibility_model_event()
            self.model_action.setEnabled(False)

        # --- Gestión de la Cámara ---
        if self.camera_paused:
            self.camera_interface.resume_video()

        # Asegura que los controles de video estén en el plano frontal
        self.camera_interface.video_button.show()
        self.camera_interface.video_button.raise_()
        
        # Bloquea opciones de configuración mientras el proceso está en ejecución
        self.simulation_action.setEnabled(False)
        self.com_submenu.setEnabled(True)

        # --- Conexión con Hardware ---
        if self.connected_to_robot:
            self.robot_controller.start() # Lógica de control
            self.openbotv.start()        # Comunicación física

        # Inicia la telemetría en tiempo real
        self.graph_interface.start()

        # --- Cambio de Estado de la UI ---
        # Intercambia la visibilidad de los botones de control de flujo
        self.stop_button.show()
        self.pause_button.show()
        self.start_button.hide()

        self.stopped = False

    def pause(self):
        """ Pone en pausa la simulation si existe y la cámara.
            Mantiene los hilos vivos pero detiene el procesamiento de datos entrantes.
        """
        if self.simulation_interface is not None:
            self.simulation_interface.pause_simulation()

        self.camera_interface.pause_video()
        self.camera_paused = True

        # Actualiza la UI para permitir la reanudación
        self.pause_button.hide()
        self.start_button.show()

    def stop(self):
        """ "Detiene" la simulation y apaga la cámara.
            Libera o detiene los recursos de los Workers (hilos) para ahorrar CPU.
        """
        if self.simulation_interface is not None and self.hab_simulation:
            self.simulation_interface.stop_simulation()

        # Desbloquea menús de configuración para permitir cambios antes de un nuevo inicio
        self.simulation_action.setEnabled(True)
        self.model_action.setEnabled(True)

        # Finaliza procesos de visión y gráficas
        self.camera_interface.stop_video()
        self.camera_interface.video_button.hide()
        self.graph_interface.stop()

        # Restablece el estado de los botones de control
        self.stop_button.hide()
        self.pause_button.hide()
        self.start_button.show()

        self.stopped = True

    def reset(self):
        """ Reinicia los valores de los sliders a 0 llamando al método estático de SlidersWidget.
        """
        SlidersWidget.restart_sliders()

    def toggle_visibility_camera_event(self):
        """ Alterna la visibilidad del widget de la cámara y actualiza el texto del botón
            correspondiente en el menú para reflejar el estado actual.
        """
        if self.cameraBox.isVisible():
            self.cameraBox.hide()
            self.camera_action.setText("Mostrar Cámara")
        else:
            self.cameraBox.show()
            self.camera_action.setText("Ocultar Cámara")

    def toggle_visibility_model_event(self):
        """ Alterna la visibilidad del widget del modelo 3D y actualiza el texto del botón
            correspondiente para retroalimentación del usuario.
        """
        if self.modelBox.isVisible():
            self.modelBox.hide()
            self.model_action.setText("Mostrar Modelo 3D")
        else:
            self.modelBox.show()
            self.model_action.setText("Ocultar Modelo 3D")

    def toggle_activation_model_event(self):
        """ Habilita o deshabilita la lógica de simulación de QtQuick. 
            A diferencia de 'toggle_visibility', esto controla si la simulación debe ejecutarse o no.
        """
        if self.hab_simulation:
            self.hab_simulation = False
            self.simulation_action.setText("Habilitar simulación")
        else:
            self.hab_simulation = True
            self.simulation_action.setText("Deshabilitar simulación")

    def connect_robot(self):
        """ Establece el enlace de comunicación con el microcontrolador (ej. Arduino/ESP32)
            utilizando el puerto COM previamente seleccionado.
        """
        if not self.com:
            print("Error: Dispositivo no detectado")
            return
        
        self.connected_to_robot = True
        # Inicializa el objeto de comunicación con el hardware
        self.init_openbotv(self.com)
        # Actualiza el indicador visual de conexión en la interfaz
        self.com_connected_label.setText(self.com)