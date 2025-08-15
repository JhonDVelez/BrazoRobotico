import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout
from PyQt6.QtGui import QScreen
from PyQt6 import uic
from interface.cameraInterface import VideoOverlayWidget

class main_i(QMainWindow):

    def __init__(self):
        super().__init__()
        self.init_main_window()
        self.init_camera()
        # self.init_model()
        self.setup_connections()
        
    def init_main_window(self):
        """ Inicializa la ventana principal de la aplicación y configura su diseño
        """
        self.ui = uic.loadUi(os.path.join(os.path.dirname(__file__), "appInterface.ui"), self)

        # Centra la ventana en la pantalla
        window = QMainWindow()
        screen_center = QScreen.availableGeometry(QApplication.primaryScreen()).center()     
        window_geometry = window.frameGeometry()
        window_geometry.moveCenter(screen_center)
        window.move(window_geometry.topLeft())

        # Configura el tamaño por defecto de las ventanas
        self.contentSplitter.setSizes([500,500,300])
        self.visualSplitter.setSizes([100,100])

    def init_camera(self):
        """ Inicializa la interfaz de la cámara y agrega el widget de video
        """
        # Limpiar cameraBox y agregar layout si no existe
        if not self.cameraBox.layout():
            layout = QVBoxLayout(self.cameraBox)
            layout.setContentsMargins(0, 0, 0, 0)
            self.cameraBox.setLayout(layout)
        
        self.videoWidget = VideoOverlayWidget(self.ui)
        self.cameraBox.layout().addWidget(self.videoWidget)
    
    # def init_model(self):
        # self.modelBox = self.ui.modelBox
    
    def setup_connections(self):
        """ Configura las conexiones de eventos para los botones de la interfaz
        """
        if hasattr(self.ui, 'cameraButton'):
            self.ui.cameraButton.clicked.connect(lambda: self.toogle_visibility_camera_event(self.cameraBox))
        if hasattr(self.ui, 'modelButton'):
            self.ui.modelButton.clicked.connect(lambda: self.toogle_visibility_model_event(self.modelBox))

    def toogle_visibility_camera_event(self, cameraBox):
        """ Alterna la visibilidad del widget de la cámara y actualiza el texto del botón correspondiente.

        Args:
            cameraBox (PyQt6.QtWidgets.QGroupBox): El widget que contiene la cámara.
        """
        if cameraBox.isVisible():
            cameraBox.hide()
            self.ui.cameraButton.setText("Mostrar Cámara")
        else:
            cameraBox.show()
            self.ui.cameraButton.setText("Ocultar Cámara")
    
    def toogle_visibility_model_event(self, modelBox):
        """ Alterna la visibilidad del widget del modelo 3D y actualiza el texto del botón correspondiente.

        Args:
            modelBox (PyQt6.QtWidgets.QGroupBox): El widget que contiene el modelo 3D.
        """
        if modelBox.isVisible():
            modelBox.hide()
            self.ui.modelButton.setText("Mostrar Modelo 3D")
        else:
            modelBox.show()
            self.ui.modelButton.setText("Ocultar Modelo 3D")