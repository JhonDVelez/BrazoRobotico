import numpy as np
import queue
from PyQt6.QtCore import QObject, pyqtSignal, QThread, pyqtSlot

class GraphProcessingWorker(QThread):
    """
    Worker encargado de procesar cálculos pesados (como cinemática) 
    fuera del hilo de la interfaz de usuario.
    Recibe ángulos y emite posiciones cartesianas.
    """
    sim_result_ready = pyqtSignal(list)
    phy_result_ready = pyqtSignal(list, list) # pos_data, temp_data

    def __init__(self, kinematics_service):
        super().__init__()
        # Inyectamos el servicio de cinemática (CD) desde el controlador
        self._kinematics_service = kinematics_service
        self._sim_queue = queue.Queue(maxsize=1)
        self._phy_queue = queue.Queue(maxsize=1)
        self._running = True

    def push_sim_angles(self, angles: np.ndarray):
        """ Agrega ángulos de simulación para procesar """
        try:
            self._sim_queue.get_nowait()
        except queue.Empty:
            pass
        try:
            self._sim_queue.put_nowait(angles)
        except queue.Full:
            pass

    def push_phy_angles(self, angles: np.ndarray, temp_data: list):
        """ Agrega ángulos físicos y sus temperaturas para procesar """
        try:
            self._phy_queue.get_nowait()
        except queue.Empty:
            pass
        try:
            self._phy_queue.put_nowait((angles, temp_data))
        except queue.Full:
            pass

    def run(self):
        self._running = True
        while self._running:
            # Procesar Simulación
            try:
                angles_sim = self._sim_queue.get(timeout=0.05)
                pos = self._kinematics_service.cd(angles_sim[0], angles_sim[1], angles_sim[2], angles_sim[3])
                self.sim_result_ready.emit(list(pos))
            except queue.Empty:
                pass

            # Procesar Físico
            try:
                data_phy = self._phy_queue.get(timeout=0.05)
                angles_phy, temp_data = data_phy
                pos = self._kinematics_service.cd(angles_phy[0], angles_phy[1], angles_phy[2], angles_phy[3])
                self.phy_result_ready.emit(list(pos), temp_data)
            except queue.Empty:
                pass

    def stop(self):
        self._running = False
        self.wait()

    # Getters / Setters
    def is_running(self):
        return self._running
