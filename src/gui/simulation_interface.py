from sys import exception
from PyQt6.QtWidgets import QVBoxLayout, QWidget
from PyQt6.QtGui import QWindow
from gui.simulation_worker import SimWorker


class SimInterface(QWidget):
    """ Clase encargada del modelo 3d mostrado en la interfaz
    """

    def __init__(self):
        super().__init__()
        self.qwindow = None
        self.window_container = None
        self.physics_worker = None
        self.simulation_running = False

        self.physics_worker = SimWorker(self)
        self.physics_worker.pybullet_window.connect(self.capture_window)
        self.physics_worker.start()
        self.simulation_running = True

        if not self.layout():
            self.Vlayout = QVBoxLayout(self)
            self.Vlayout.setContentsMargins(0, 0, 0, 0)
            self.setLayout(self.Vlayout)

    def capture_window(self, hwnd):
        """ Captura la ventana del GUI de pybullet y la incrusta en la interfaz

        Args:
            hwnd (int): Numero de identificacion de la ventana del gui de pybullet
        """
        self.qwindow = QWindow.fromWinId(hwnd)
        if self.qwindow is not None:
            self.window_container = QWidget.createWindowContainer(
                self.qwindow, self)
            self.layout().addWidget(self.window_container)
            self.window_container.update()
            self.activateWindow()

    def start_simulation(self):
        """ Inicia la simulacion dando inicio al proceso de ejecucion
        """
        self.physics_worker.start_simulation()

    def pause_simulation(self):
        """ Pausa la simulación
        """
        self.physics_worker.pause_simulation()

    def stop_simulation(self):
        """ Pausa la simulación
        """
        self.physics_worker.exit()
        self.physics_worker.wait()
        self.physics_worker.stop_simulation()

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
