import os
import win32con
import win32gui
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QMessageBox
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QSizePolicy
from PyQt6.QtGui import QScreen, QIcon
from PyQt6.QtCore import Qt, QSize
from PyQt6 import uic
from gui.camera_interface import VideoOverlayWidget
from gui.sliders_interface import SlidersWidget
from gui.simulation_interface import SimInterface


class MainInterface(QMainWindow):
    """ Ventana principal de la interfaz

    Args:
        QMainWindow (QtWidget): Integracion como ventana principal de la aplicacion
    """

    def __init__(self):
        super().__init__()
        self.simulation_interface = None
        self.stopped = True
        self.camera_paused = False
        self.init_main_window()
        self.init_camera()
        self.init_controls()
        self.init_simulation()
        self.setup_connections()

    def init_main_window(self):
        """ Inicializa la ventana principal de la aplicación y configura su diseño
        """
        self.ui = uic.loadUi(os.path.join(
            os.path.dirname(__file__), "app_interface.ui"), self)

        # Centra la ventana en la pantalla
        window = QMainWindow()
        screen_center = QScreen.availableGeometry(
            QApplication.primaryScreen()).center()
        window_geometry = window.frameGeometry()
        window_geometry.moveCenter(screen_center)
        window.move(window_geometry.topLeft())

        # Configura el tamaño por defecto de las ventanas
        self.contentSplitter.setSizes([500, 500, 300])
        self.visualSplitter.setSizes([100, 100])

    def init_camera(self):
        """ Inicializa la interfaz de la cámara y agrega el widget de video
        """
        # Limpiar cameraBox y agregar layout si no existe
        if not self.cameraBox.layout():
            layout = QVBoxLayout(self.cameraBox)
            layout.setContentsMargins(0, 0, 0, 0)
            self.cameraBox.setLayout(layout)

        self.camera_interface = VideoOverlayWidget(self.ui)
        self.cameraBox.layout().addWidget(self.camera_interface)

    def init_controls(self):
        """ Inicializa la interfaz de controladores con sliders que indica el
           angulo objetivo de cada motor del robot
        """
        self.slider_widget = SlidersWidget(self.ui)
        self.controlsBox.layout().addWidget(self.slider_widget)

        self.control_app_widget = QWidget()
        if not self.control_app_widget.layout():
            layout = QHBoxLayout(self.control_app_widget)
            layout.setContentsMargins(0, 0, 0, 0)
            self.control_app_widget.setLayout(layout)

        self.start_icon = QIcon(os.path.join(os.path.dirname(__file__),
                                             "icons", "play.png"))
        self.pause_icon = QIcon(os.path.join(os.path.dirname(__file__),
                                             "icons", "pause.png"))
        self.stop_icon = QIcon(os.path.join(os.path.dirname(__file__),
                                            "icons", "stop.png"))
        self.reset_icon = QIcon(os.path.join(os.path.dirname(__file__),
                                             "icons", "refresh.png"))

        self.start_button.setIcon(self.start_icon)
        self.start_button.setStyleSheet(
            "background-color: #3B963F")  # Boton color verde

        self.reset_button.setIcon(self.reset_icon)
        self.reset_button.setStyleSheet(
            "background-color: #777777")  # Boton color gris

        self.stop_button.setIcon(self.stop_icon)
        self.stop_button.setStyleSheet(
            "background-color: #F74220")  # Boton color rojo

        self.pause_button.setIcon(self.pause_icon)
        self.pause_button.setStyleSheet(
            "background-color: #777777")  # Boton color gris

        self.control_app_widget.layout().addWidget(self.start_button)
        self.control_app_widget.layout().addWidget(self.pause_button)
        self.control_app_widget.layout().addWidget(self.stop_button)
        self.control_app_widget.layout().addWidget(self.reset_button)

        self.controlsBox.layout().addWidget(self.control_app_widget)

        self.pause_button.hide()
        self.stop_button.hide()

    def init_simulation(self):
        """ Inicializa la interfaz de la simulacion creando el layout y realizando ajustes para una
            correcta adicion a esta.
        """
        if not self.modelBox.layout():
            self.sim_layout = QVBoxLayout(self.modelBox)
            self.sim_layout.setContentsMargins(0, 0, 0, 0)
            self.modelBox.setLayout(self.sim_layout)

        self.simulation_interface = SimInterface(self.ui)
        self.simulation_interface.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.simulation_interface.setMinimumSize(QSize(0, 0))
        self.sim_layout.addWidget(self.simulation_interface)

    def start(self):
        """ Inicia o detiene la simulacion en caso de ser la primera vez instancia la clase
            SimInterface, tambien cambia los colores e iconos del boton.
        """
        if self.habSimulationCheck.isChecked():
            self.simulation_interface.start_simulation()
        else:
            if self.modelBox.isVisible():
                self.toogle_visibility_model_event(self.modelBox)

        self.habSimulationCheck.setEnabled(False)
        if self.camera_paused:
            self.camera_interface.resume_video()

        self.stop_button.show()
        self.pause_button.show()
        self.start_button.hide()

        self.stopped = False

    def pause(self):
        """ Pone en pausa la simulacion si existe y la camara
        """
        if self.simulation_interface is not None:
            self.simulation_interface.pause_simulation()

        self.camera_interface.pause_video()
        self.camera_paused = True

        self.pause_button.hide()
        self.start_button.show()

    def stop(self):
        """ "Detiene" la simulacion y apaga la camara
        """
        if self.simulation_interface is not None:
            self.simulation_interface.stop_simulation()
        self.habSimulationCheck.setEnabled(True)

        self.camera_interface.stop_video()

        self.stop_button.hide()
        self.pause_button.hide()
        self.start_button.show()

        self.stopped = True

    def reset(self):
        """ Reinicia los valores de los sliders a 0
        """
        SlidersWidget.restart_sliders()

    def setup_connections(self):
        """ Configura las conexiones de eventos para los botones de la interfaz
        """
        if hasattr(self.ui, 'cameraButton'):
            self.ui.cameraButton.clicked.connect(
                lambda: self.toogle_visibility_camera_event(self.cameraBox))
        if hasattr(self.ui, 'modelButton'):
            self.ui.modelButton.clicked.connect(
                lambda: self.toogle_visibility_model_event(self.modelBox))
        if hasattr(self.ui, 'start_button'):
            self.start_button.clicked.connect(self.start)
        if hasattr(self.ui, 'pause_button'):
            self.pause_button.clicked.connect(self.pause)
        if hasattr(self.ui, 'stop_button'):
            self.stop_button.clicked.connect(self.stop)
        if hasattr(self.ui, 'reset_button'):
            self.reset_button.clicked.connect(self.reset)

    def toogle_visibility_camera_event(self, camera_box):
        """ Alterna la visibilidad del widget de la cámara y actualiza el texto del botón
            correspondiente.

        Args:
            cameraBox (PyQt6.QtWidgets.QGroupBox): El widget que contiene la cámara.
        """
        if camera_box.isVisible():
            camera_box.hide()
            self.ui.cameraButton.setText("Mostrar Cámara")
        else:
            camera_box.show()
            self.ui.cameraButton.setText("Ocultar Cámara")

    def toogle_visibility_model_event(self, model_box):
        """ Alterna la visibilidad del widget del modelo 3D y actualiza el texto del botón
            correspondiente.

        Args:
            modelBox (PyQt6.QtWidgets.QGroupBox): El widget que contiene el modelo 3D.
        """
        if model_box.isVisible():
            model_box.hide()
            self.ui.modelButton.setText("Mostrar Modelo 3D")
        else:
            model_box.show()
            self.ui.modelButton.setText("Ocultar Modelo 3D")

    def closeEvent(self, event):
        """ Gestiona el evento de cerrado presentando una ventana para verificar la salida de
            la aplicacion
        """
        reply = QMessageBox.question(
            self,
            "Salir",
            "¿Seguro que quieres cerrar la aplicación?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()

    def keyPressEvent(self, event):
        """ Toma los eventos del teclado y los envia a la ventana incrustada de pybullet, presionado
        """
        try:
            if self.simulation_interface is not None:
                if event.key() == Qt.Key.Key_Control:
                    self.simulation_interface.physics_worker.send_key(
                        self.simulation_interface.physics_worker.hwnd,
                        win32con.VK_CONTROL,
                        press=True
                    )
                if event.key() == Qt.Key.Key_S:
                    self.simulation_interface.physics_worker.send_key(
                        self.simulation_interface.physics_worker.hwnd,
                        ord('S'),
                        press=True
                    )
        except (TypeError, win32gui.error) as e:
            print(f"Error en la captura del teclado: {e}")

    def keyReleaseEvent(self, event):
        """ Toma los eventos del teclado y los envia a la ventana incrustada de pybullet, librerado
        """
        try:
            if self.simulation_interface is not None:
                if event.key() == Qt.Key.Key_Control:
                    self.simulation_interface.physics_worker.send_key(
                        self.simulation_interface.physics_worker.hwnd,
                        win32con.VK_CONTROL,
                        press=False
                    )
                if event.key() == Qt.Key.Key_S:
                    self.simulation_interface.physics_worker.send_key(
                        self.simulation_interface.physics_worker.hwnd,
                        ord('S'),
                        press=False
                    )
        except (TypeError, win32gui.error) as e:
            print(f"Error en la captura del teclado: {e}")
