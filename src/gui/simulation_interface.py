from PyQt6.QtWidgets import QVBoxLayout, QWidget
from PyQt6.QtGui import QWindow
from PyQt6.QtCore import QTimer
from gui.simulation_worker import SimWorker


class SimInterface(QWidget):
    """ Clase encargada del modelo 3d mostrado en la interfaz
    """

    def __init__(self, slider_widget):
        super().__init__()
        self.qwindow = None
        self.window_container = None
        self.physics_worker = None
        self.slider_widget = slider_widget
        self.simulation_running = False

        self.physics_worker = SimWorker(self)
        self.physics_worker.pybullet_window.connect(self.capture_window)
        self.physics_worker.start()
        self.simulation_running = True

        QTimer.singleShot(0, self.start_simulation)

        if not self.layout():
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            self.setLayout(layout)

    def capture_window(self, hwnd):
        """ Captura la ventana del GUI de pybullet y la incrusta en la interfaz

        Args:
            hwnd (int): Numero de identificacion de la ventana del gui de pybullet
        """
        self.qwindow = QWindow.fromWinId(hwnd)
        if self.qwindow is not None:
            print(f"ventana recibida: {hwnd}, {self.qwindow}")
            self.window_container = QWidget.createWindowContainer(
                self.qwindow, self)
            self.layout().addWidget(self.window_container)

    def start_simulation(self):
        """ Inicia la simulacion dando inicio al proceso de ejecucion
        """
        self.physics_worker.sim_controller.start_simulation()

    def stop_simulation(self):
        """ Pausa la simulación
        """
        self.physics_worker.sim_controller.stop_simulation()

    def closeEvent(self, event):
        """ Asegurar limpieza cuando se cierra el widget
        """
        self.stop_simulation()
        super().closeEvent(event)

    def __del__(self):
        """ Destructor para limpieza final
        """
        self.stop_simulation()
