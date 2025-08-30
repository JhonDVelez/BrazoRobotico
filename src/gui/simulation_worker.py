import os
import win32gui
import win32api
import win32con
from PyQt6.QtCore import QThread, pyqtSignal, QTimer
from simulation.simulation_controller import SimController


class SimWorker(QThread):
    """Worker thread para manejar gui del pybullet e incrustarla en la interfaz de pyqt
    """

    pybullet_window = pyqtSignal(int)

    def __init__(self, sim_interface):
        super().__init__()
        self.hwnd = None
        self.timer = None
        self.sim_controller = None
        self.sim_interface = sim_interface

        self.sim_controller = SimController(
            self.sim_interface)
        self.sim_controller.start_simulation()

    def run(self):
        """ Define el ciclo de ejecucion del subproceso el cual se ejecuta hasta que detecta 
            la ventana del gui de pybullet
        """
        self.capture_window()
        self.exec()

    def capture_window(self):
        """ Captura la ventana del gui de pybullet obteniendo el numero de identificion de windows
        """
        if self.hwnd is None:
            hwnd = win32gui.FindWindow(
                "DeviceWin32",
                "Bullet Physics ExampleBrowser using OpenGL3+ [btgl] Release build"
            )
            if hwnd:
                self.hwnd = hwnd
                self.pybullet_window.emit(self.hwnd)

        QTimer.singleShot(4, self.capture_window)

    def send_key(self, hwnd, vk_code, press=True):
        """ Simula una tecla hacia la ventana hwnd (al interactuar con la interfaz la ventana de
            pybullet deja de estar en foco por lo que no detecta el teclado por ello se deben emular
            las pulsaciones de este)
        """
        if press:
            win32api.SendMessage(hwnd, win32con.WM_KEYDOWN, vk_code, 0)
        else:
            win32api.SendMessage(hwnd, win32con.WM_KEYUP, vk_code, 0)
