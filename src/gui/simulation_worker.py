import os
import win32gui
import win32api
import win32con
from PyQt6.QtCore import QThread, pyqtSignal, QTimer, QObject
from PyQt6.QtQuick3D import QQuick3D
from PyQt6.QtGui import QVector3D
from simulation.physics_worker import PhysicsWorker


class SimWorker(QThread):
    """Worker thread para manejar gui del pybullet e incrustarla en la interfaz de pyqt
    """

    pybullet_window = pyqtSignal(int)

    def __init__(self, root_object):
        super().__init__()
        self.hwnd = None
        self.timer = None
        self.root_object = root_object
        self.joint_names = [
            "arm1_link_1",
            "arm2_link_1",
            "arm3_link_1",
            "arm4_link_1",
            "clamp_arm_link_1",
            "clamp2_link_1"]
        self.direction_rotation = [
            "y",
            "z",
            "z",
            "y",
            "z",
            "z"
        ]

        self.worker = PhysicsWorker()
        self.worker.set_max_velocity(1.2)
        self.worker.update_model.connect(self.update_simulation)

    def update_simulation(self, joint_positions=[0, 0, 0, 0, 0]):
        joint_positions[-1] = joint_positions[-1]*-1
        for motor_name, angle, direction in zip(self.joint_names, joint_positions, self.direction_rotation):
            motor = self.root_object.findChild(QObject, motor_name)
            if direction == "z":
                motor.setProperty("eulerRotation", QVector3D(0, 0, angle))
            elif direction == "y":
                motor.setProperty("eulerRotation", QVector3D(0, angle, 0))

    def send_key(self, hwnd, vk_code, press=True):
        """ Simula una tecla hacia la ventana hwnd (al interactuar con la interfaz la ventana de
            pybullet deja de estar en foco por lo que no detecta el teclado por ello se deben emular
            las pulsaciones de este)
        """
        if press:
            win32api.SendMessage(hwnd, win32con.WM_KEYDOWN, vk_code, 0)
        else:
            win32api.SendMessage(hwnd, win32con.WM_KEYUP, vk_code, 0)

    def start_simulation(self):
        """ Da inicio a la ejecucion de la simulacion o la vuelve a poner en curso si fue pausada
        """
        self.worker.start()

    def pause_simulation(self):
        """ Detiene el ciclo de procesamiento del hilo pausando la ejecucion de la simulacion
        """
        self.worker.pause()
        self.worker.wait()

    def stop_simulation(self):
        """ Detiene el ciclo de procesamiento del hilo pausando la ejecucion de la simulacion
        """
        self.worker.wait()
        self.worker.stop()
