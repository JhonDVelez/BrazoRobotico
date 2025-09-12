import os
from PyQt6.QtWidgets import QVBoxLayout, QWidget, QLabel, QSizePolicy
from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtQuickWidgets import QQuickWidget
from PyQt6.QtGui import QResizeEvent, QPixmap
from gui.simulation_worker import SimWorker
from simulation.physics_worker import PhysicsWorker
from data.control_utils import units, modes, domains
from data.controller import dataFlow


class SimInterface(QWidget):
    """ Clase encargada del modelo 3d mostrado en la interfaz
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.qwindow = None
        self.window_container = None
        self.sim_worker = None
        self.quick_widget = None

        # Adicion de layout si no existe y configuraciones
        if not self.layout():
            self.v_layout = QVBoxLayout(self)
            self.v_layout.setContentsMargins(0, 0, 0, 0)
            self.setLayout(self.v_layout)

        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)
        self.setMinimumSize(160, 120)

        # Adicion del widget de Quick3D
        self.__init_model()
        if self.quick_widget is not None:
            self.layout().addWidget(self.quick_widget)

        # Instancias de las clases encargadas de la simulacion asi como su controlador
        root_object = self.quick_widget.rootObject()
        self.sim_worker = SimWorker(root_object)
        self.quick_widget.hide()

        self.physics_worker = PhysicsWorker()
        self.physics_worker.set_max_velocity(1.2)

        self.controller = dataFlow(
            modes.SLIDERS, units.RAD, domains.SIMULATION)
        self.controller.start()

        # Imagen que representa la seccion de la simulacion y su configuracion
        self.image_path = os.path.join(os.path.dirname(
            __file__), "img", 'robotArm.png')
        self.pipmax = QPixmap(self.image_path)
        self.label = QLabel()
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.label.setScaledContents(False)
        self.label.setMinimumSize(160, 120)
        self.layout().addWidget(self.label)
        self.set_label_pixmap(self.pipmax)

    def __init_model(self):
        try:
            self.quick_widget = QQuickWidget()
            self.quick_widget.setSource(QUrl.fromLocalFile(os.path.join(
                os.path.dirname(__file__), '..', 'simulation', 'simulation.qml')))
        except Exception as e:
            print(f"Error al cargar el qml de la simulacion: {e}")

    def start_simulation(self):
        """ Inicia la simulacion dando inicio al proceso de ejecucion
        """
        self.label.hide()
        self.quick_widget.show()
        self.sim_worker.start()
        self.physics_worker.start()

    def pause_simulation(self):
        """ Pausa la simulación
        """
        self.physics_worker.pause()
        self.physics_worker.wait()

    def stop_simulation(self):
        """ Pausa la simulación
        """
        self.sim_worker.exit()
        self.sim_worker.wait()
        self.physics_worker.wait()
        self.physics_worker.stop()
        self.label.show()
        self.label.update()

    def set_label_pixmap(self, pixmap: QPixmap):
        """ Método para establecer el pixmap del video en el label reescalado si es necesario.

        Args:
            pixmap (QPixmap): El pixmap del video a mostrar
        """
        if pixmap and not pixmap.isNull():
            # Escalar solo si es necesario
            label_size = self.label.size()
            if pixmap.size() != label_size:
                scaled_pixmap = pixmap.scaled(
                    label_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.FastTransformation
                )
                self.label.setPixmap(scaled_pixmap)
            else:
                self.label.setPixmap(pixmap)
        else:
            self.videoLabel.clear()

    def resizeEvent(self, event: QResizeEvent):
        """ Maneja el evento de redimensionamiento del widget.

        Args:
            event (QResizeEvent): Evento de redimensionamiento
        """
        super().resizeEvent(event)

        # Reescalar imagen actual si existe (de forma optimizada)

        if self.label.isVisible():
            self.set_label_pixmap(self.pipmax)

    def closeEvent(self, event):
        """ Asegurar limpieza cuando se cierra el widget
        """
        # self.pause_simulation()

        if self.qwindow is not None:
            self.qwindow = None
        if self.window_container is not None:
            self.window_container.setParent(None)
            self.window_container = None

        super().closeEvent(event)
