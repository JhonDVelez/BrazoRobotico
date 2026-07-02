"""
Módulo para el procesamiento asíncrono de datos cinemáticos para gráficos.

Este módulo define la clase GraphProcessingWorker, un hilo que descarga al
hilo de la interfaz de usuario de cálculos pesados como la cinemática directa,
asegurando una visualización fluida de las trayectorias cartesianas.

Conexiones:
    - Inyecta el servicio de cinemática (KinematicsWorker).
    - Utiliza colas de prioridad baja (tamaño 1) para procesar solo el último dato.
    - Emite `sim_result_ready` y `phy_result_ready` con los puntos 3D calculados.
"""

import queue
import numpy as np
from PyQt6.QtCore import pyqtSignal, QThread


class GraphProcessingWorker(QThread):
    """
    Worker encargado de procesar cálculos pesados fuera del hilo de la interfaz.

    Recibe ángulos articulares, ejecuta la cinemática directa y emite posiciones
    cartesianas para ser graficadas. Gestiona colas independientes para los
    datos de simulación y los datos físicos reales.

    Attributes:
        sim_result_ready (pyqtSignal): Emite una lista [x, y, z] de la simulación.
        phy_result_ready (pyqtSignal): Emite ([x, y, z], temps) del robot físico.
    """
    sim_result_ready = pyqtSignal(list)
    phy_result_ready = pyqtSignal(list, list) # pos_data, temp_data

    def __init__(self, kinematics_service):
        """
        Inicializa el worker de procesamiento con el servicio de cinemática.

        Args:
            kinematics_service (KinematicsWorker): Instancia para el cálculo de CD.
        """
        super().__init__()
        # Inyectamos el servicio de cinemática (CD) desde el controlador
        self._kinematics_service = kinematics_service
        self._sim_queue = queue.Queue(maxsize=1)
        self._phy_queue = queue.Queue(maxsize=1)
        self._running = True

    def push_sim_angles(self, angles: np.ndarray):
        """
        Agrega ángulos de simulación a la cola para su procesamiento asíncrono.

        Mantiene solo el dato más reciente descartando los anteriores si la
        cola está llena.

        Args:
            angles (np.ndarray): Vector de 4 ángulos en radianes.
        """
        try:
            self._sim_queue.get_nowait()
        except queue.Empty:
            pass
        try:
            self._sim_queue.put_nowait(angles)
        except queue.Full:
            pass

    def push_phy_angles(self, angles: np.ndarray, temp_data: list):
        """
        Agrega ángulos físicos y telemetría a la cola para su procesamiento.

        Args:
            angles (np.ndarray): Vector de ángulos reales.
            temp_data (list): Datos de temperatura de los servos.
        """
        try:
            self._phy_queue.get_nowait()
        except queue.Empty:
            pass
        try:
            self._phy_queue.put_nowait((angles, temp_data))
        except queue.Full:
            pass

    def run(self):
        """
        Bucle principal del hilo de procesamiento.

        Extrae datos de las colas, calcula la CD y emite los resultados.
        """
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
        """
        Detiene la ejecución del hilo de forma segura.
        """
        self._running = False
        self.wait()

    # Getters / Setters
    def is_running(self):
        """
        Verifica si el worker está ejecutando su bucle.

        Returns:
            bool: True si está en ejecución.
        """
        return self._running
