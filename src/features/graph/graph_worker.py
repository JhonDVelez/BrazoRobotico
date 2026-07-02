"""
Módulo que gestiona el almacenamiento y sincronización de datos para gráficos.

Este módulo define la clase GraphWorker, la cual mantiene buffers circulares
de alta eficiencia (usando NumPy) para datos provenientes de la simulación
y del hardware físico.

Conexiones:
    - Recibe datos de simulación mediante `add_sim_data`.
    - Recibe telemetría física mediante `add_phy_data`.
    - Emite `channel_updated` cada vez que los buffers se modifican.
"""

import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot


class GraphWorker(QObject):
    """
    Worker encargado de la gestión de buffers circulares y almacenamiento de datos.

    Es agnóstico a la visualización y a los cálculos externos, enfocándose en
    la integridad y sincronización temporal de las series de datos para múltiples canales.

    Attributes:
        channel_updated (pyqtSignal): Emite los buffers actualizados para un canal:
            (index, y_sim, y_phy, temp_phy, write_idx, full, x).
    """
    # Emite los buffers actualizados para un canal específico: (index, y_sim, y_phy, temp_phy, write_idx, full, x)
    channel_updated = pyqtSignal(int, np.ndarray, np.ndarray, str, int, bool, np.ndarray)

    def __init__(self, display_window: int = 1000, graphs_amount: int = 6):
        """
        Inicializa el worker con el tamaño de ventana y número de canales.

        Args:
            display_window (int): Número de puntos visibles en el eje X.
            graphs_amount (int): Cantidad de canales/motores a monitorear.
        """
        super().__init__()
        self._buffer_size = 10000
        self._display_window = display_window
        self._graphs_amount = graphs_amount
        self._is_paused = False

        self.__setup_buffers()

    def __setup_buffers(self):
        """
        Configura e inicializa los arreglos de NumPy para el almacenamiento.
        """
        # Almacenamiento de datos (N canales)
        self._y_sim = np.zeros((self._graphs_amount, self._buffer_size), dtype=np.float32)
        self._y_phy = np.zeros((self._graphs_amount, self._buffer_size), dtype=np.float32)
        self._temp_phy = [""] * self._graphs_amount

        self._x_data = np.arange(-self._display_window, 0, dtype=np.float32)
        self._write_index = 0
        self._buffer_full = False

    @pyqtSlot(list)
    def add_sim_data(self, data: list):
        """
        Agrega datos de simulación para todos los canales y avanza el índice.

        Args:
            data (list): Lista de valores flotantes de la simulación.
        """
        if self._is_paused:
            return

        for i, val in enumerate(data):
            if i < self._graphs_amount:
                self._y_sim[i, self._write_index] = val

        self._advance_index()

    @pyqtSlot(list, list)
    def add_phy_data(self, pos_data: list, temp_data: list):
        """
        Agrega datos físicos y de temperatura para todos los canales.

        Args:
            pos_data (list): Lista de posiciones reales recibidas.
            temp_data (list): Lista de temperaturas de los motores.
        """
        if self._is_paused:
            return

        for i, pos in enumerate(pos_data):
            if i < self._graphs_amount:
                self._y_phy[i, self._write_index] = pos
                if temp_data and i < len(temp_data):
                    self._temp_phy[i] = str(temp_data[i])
                else:
                    self._temp_phy[i] = ""

        # Notificar actualización sin avanzar el reloj (paridad con original)
        self.notify_update()

    def _advance_index(self):
        """
        Incrementa el puntero de escritura del buffer circular.
        """
        self._write_index += 1
        if self._write_index >= self._buffer_size:
            self._write_index = 0
            self._buffer_full = True

        self.notify_update()

    def notify_update(self):
        """
        Notifica a los suscriptores (plots) que los buffers han cambiado.

        Itera sobre todos los canales emitiendo sus respectivos datos.
        """
        for i in range(self._graphs_amount):
            self.channel_updated.emit(
                i,
                self._y_sim[i],
                self._y_phy[i],
                self._temp_phy[i],
                self._write_index,
                self._buffer_full,
                self._x_data
            )

    # --- API Pública (Getters / Setters) ---

    def set_paused(self, paused: bool):
        """
        Pausa o reanuda la ingestión de datos.

        Args:
            paused (bool): True para pausar.
        """
        self._is_paused = paused

    def get_is_paused(self):
        """
        Retorna el estado de pausa actual.

        Returns:
            bool: True si está pausado.
        """
        return self._is_paused

    def reset_buffers(self):
        """
        Limpia todos los datos almacenados reinicializando los buffers.
        """
        self.__setup_buffers()
