import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout
from PyQt6.QtGui import QScreen
from PyQt6 import uic
from gui.camera_interface import VideoOverlayWidget
from gui.sliders_interface import SlidersWidget
from gui.simulation_interface import Model3D


class MainInterface(QMainWindow):
    """ Ventana principal de la interfaz

    Args:
        QMainWindow (QtWidget): Integracion como ventana principal de la aplicacion
    """

    def __init__(self):
        super().__init__()
        self.init_main_window()
        self.init_camera()
        self.init_controls()
        self.init_simulation()
        self.setup_connections()

    def init_main_window(self):
        """"" Inicializa la ventana principal de la aplicación y configura su diseño
        """""
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

        self.video_widget = VideoOverlayWidget(self.ui)
        self.cameraBox.layout().addWidget(self.video_widget)

    # def init_model(self):
        # self.modelBox = self.ui.modelBox
    def init_controls(self):
        """ Inicializa la interfaz de controladores con sliders que indica el  
           angulo objetivo de cada motor del robot
        """
        if not self.controlsBox.layout():
            layout = QVBoxLayout(self.controlsBox)
            layout.setContentsMargins(0, 0, 0, 0)
            self.controlsBox.setLayout(layout)

        self.controls_widget = SlidersWidget(self.ui)
        self.controlsBox.layout().addWidget(self.controls_widget)

    def init_simulation(self):
        """ Inicializa la interfaz de la simulacion creando el layout y realizando ajustes para una
            correcta adicion a esta.
        """
        if not self.modelBox.layout():
            layout = QVBoxLayout(self.modelBox)
            layout.setContentsMargins(0, 0, 0, 0)
            self.modelBox.setLayout(layout)

        self.simulation_widget = Model3D()
        self.modelBox.layout().addWidget(self.simulation_widget)

    def setup_connections(self):
        """ Configura las conexiones de eventos para los botones de la interfaz
        """
        if hasattr(self.ui, 'cameraButton'):
            self.ui.cameraButton.clicked.connect(
                lambda: self.toogle_visibility_camera_event(self.cameraBox))
        if hasattr(self.ui, 'modelButton'):
            self.ui.modelButton.clicked.connect(
                lambda: self.toogle_visibility_model_event(self.modelBox))

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
