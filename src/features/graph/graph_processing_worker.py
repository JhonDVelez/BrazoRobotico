"""
Modulo para el procesamiento asincrono de datos cinematicos para graficos.

Este modulo define la clase GraphProcessingWorker, un hilo que descarga al
hilo de la interfaz de usuario de calculos pesados como la cinematica directa,
asegurando una visualizacion fluida de las trayectorias cartesianas.

Conexiones:
    - Inyecta el servicio de cinematica (KinematicsWorker).
    - Utiliza colas de prioridad baja (tamaño 1) para procesar solo el ultimo dato.
    - Emite `sim_result_ready` y `phy_result_ready` con los puntos 3D calculados.
"""

import queue
import numpy as np
from PyQt6.QtCore import pyqtSignal, QThread


class GraphProcessingWorker(QThread):
    """
    Worker encargado de procesar calculos pesados fuera del hilo de la interfaz.

    Recibe angulos articulares, ejecuta la cinematica directa y emite posiciones
    cartesianas para ser graficadas. Gestiona colas independientes para los
    datos de simulacion y los datos fisicos reales.

    Attributes:
        sim_result_ready (pyqtSignal): Emite una lista [x, y, z] de la simulacion.
        phy_result_ready (pyqtSignal): Emite ([x, y, z], temps) del robot fisico.
    """
    sim_result_ready = pyqtSignal(list)
    phy_result_ready = pyqtSignal(list, list) # pos_data, temp_data

    def __init__(self, kinematics_service):
        """
        Inicializa el worker de procesamiento con el servicio de cinematica.

        Args:
            kinematics_service (KinematicsWorker): Instancia para el calculo de CD.
        """
        super().__init__()
        # Inyectamos el servicio de cinemática (CD) desde el controlador
        self._kinematics_service = kinematics_service
        self._sim_queue = queue.Queue(maxsize=1)
        self._phy_queue = queue.Queue(maxsize=1)
        self._running = True

    def push_sim_angles(self, angles: np.ndarray):
        """
        Agrega angulos de simulacion a la cola para su procesamiento asincrono.

        Mantiene solo el dato mas reciente descartando los anteriores si la
        cola esta llena.

        Args:
            angles (np.ndarray): Vector de 4 angulos en radianes.
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
        Agrega angulos fisicos y telemetria a la cola para su procesamiento.

        Args:
            angles (np.ndarray): Vector de angulos reales.
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
        Detiene la ejecucion del hilo de forma segura.
        """
        self._running = False
        self.wait()

    # Getters / Setters
    def is_running(self):
        """
        Verifica si el worker esta ejecutando su bucle.

        Returns:
            bool: True si esta en ejecucion.
        """
        return self._running
