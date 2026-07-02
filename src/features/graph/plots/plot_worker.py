"""
Módulo encargado de la optimización visual y renderizado de gráficas.

Este módulo define la clase PlotWorker, la cual extrae las porciones relevantes
de los buffers circulares globales y aplica técnicas de coalescencia de eventos
y limitación de FPS para asegurar un rendimiento visual óptimo.

Conexiones:
    - Recibe buffers mediante `update_visual_data`.
    - Emite `render_ready` con los datos listos para Pyqtgraph.
"""

import time
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, pyqtSlot


class PlotWorker(QObject):
    """
    Worker encargado de la lógica de renderizado y optimización de datos visuales.

    Implementa coalescencia de eventos para evitar saturar el hilo principal de Qt,
    recortando los buffers de datos según la ventana de visualización configurada.

    Attributes:
        render_ready (pyqtSignal): Emite (x, y_sim, y_phy, temp_text).
        MIN_RENDER_INTERVAL_MS (float): Intervalo minimo entre renders (~60 FPS).
    """
    # Envía los datos listos para ser graficados: (x, y_sim, y_phy, temp_text)
    render_ready = pyqtSignal(np.ndarray, np.ndarray, np.ndarray, str)
    
    # Intervalo mínimo entre renders (ms). 16.6ms ~ 60 FPS.
    MIN_RENDER_INTERVAL_MS = 16.0

    def __init__(self, display_window: int):
        """
        Inicializa el worker con el ancho de ventana especificado.

        Args:
            display_window (int): Número de muestras visibles.
        """
        super().__init__()
        self._display_window = display_window
        self._is_paused = False
        self._is_visible = True
        
        self._render_scheduled = False
        self._last_render_ns = 0
        
        # Historial visual (optimizado para el display_window)
        self._buffer_size = 10000
        self._x_template = np.arange(-display_window, 0, dtype=np.float32)
        
        # Datos pendientes de renderizado
        self._pending_data = None
        self._has_new_data = False

    @pyqtSlot(np.ndarray, np.ndarray, str, int, bool)
    def update_visual_data(self, y_sim_full, y_phy_full, temp_phy, write_index, buffer_full):
        """
        Extrae la porción necesaria para el renderizado basándose en la ventana.

        Gestiona los casos de buffer lineal (inicio) y buffer circular (wrap-around).

        Args:
            y_sim_full (np.ndarray): Buffer completo de simulación.
            y_phy_full (np.ndarray): Buffer completo físico.
            temp_phy (str): Texto de temperatura.
            write_index (int): Puntero de escritura.
            buffer_full (bool): Flag de desbordamiento de buffer.
        """
        if self._is_paused or not self._is_visible:
            return

        # --- Optimización: Preparación de datos para el widget ---
        available_data = self._buffer_size if buffer_full else write_index
        points_to_show = min(self._display_window, available_data)
        
        if points_to_show == 0:
            return

        if not buffer_full:
            if write_index <= self._display_window:
                offset = self._display_window - write_index
                x_data = self._x_template[offset:]
                y_sim = y_sim_full[:write_index]
                y_phy = y_phy_full[:write_index]
            else:
                start = write_index - self._display_window
                x_data = self._x_template
                y_sim = y_sim_full[start:write_index]
                y_phy = y_phy_full[start:write_index]
        else:
            if write_index >= self._display_window:
                start = write_index - self._display_window
                x_data = self._x_template
                y_sim = y_sim_full[start:write_index]
                y_phy = y_phy_full[start:write_index]
            else:
                wrap = self._display_window - write_index
                x_data = self._x_template
                y_sim = np.concatenate([y_sim_full[-wrap:], y_sim_full[:write_index]])
                y_phy = np.concatenate([y_phy_full[-wrap:], y_phy_full[:write_index]])

        self._pending_data = (x_data, y_sim, y_phy, temp_phy)
        self._has_new_data = True
        self._schedule_render()

    def _schedule_render(self):
        """
        Agenda un render para la próxima vuelta del event loop.
        """
        if self._render_scheduled:
            return
        self._render_scheduled = True
        # singleShot(0) permite que Qt procese otros eventos antes de renderizar
        QTimer.singleShot(0, self._do_render)

    def _do_render(self):
        """
        Ejecuta el render real respetando el límite de FPS configurado.
        """
        self._render_scheduled = False
        
        if self._is_paused or not self._is_visible or not self._has_new_data:
            return

        now_ns = time.monotonic_ns()
        elapsed_ms = (now_ns - self._last_render_ns) / 1_000_000
        
        if self._last_render_ns and elapsed_ms < self.MIN_RENDER_INTERVAL_MS:
            # Re-agendar si estamos por debajo del intervalo de FPS (Throttling)
            remaining_ms = int(self.MIN_RENDER_INTERVAL_MS - elapsed_ms)
            self._render_scheduled = True
            QTimer.singleShot(remaining_ms, self._do_render)
            return

        self._last_render_ns = now_ns
        self._has_new_data = False
        
        if self._pending_data:
            self.render_ready.emit(*self._pending_data)

    # --- Getters / Setters ---

    def set_paused(self, paused: bool):
        """
        Pausa o reanuda el renderizado visual.

        Args:
            paused (bool): True para pausar el renderizado.
        """
        self._is_paused = paused
        if not paused:
            self._schedule_render()

    def set_visible(self, visible: bool):
        """
        Define si el worker debe procesar datos según la visibilidad de la UI.

        Args:
            visible (bool): True si el plot está visible.
        """
        self._is_visible = visible
        if visible:
            self._schedule_render()

    def get_is_paused(self):
        """
        Retorna el estado de pausa del worker.

        Returns:
            bool: True si está pausado.
        """
        return self._is_paused
