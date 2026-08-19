"""
Modulo que define el widget de grafico cartesiano basado en PyQtGraph.

Proporciona la clase CartesianPIDPlot, un widget Qt que contiene tres
subplots (X, Y, Z) de PyQtGraph para visualizar la convergencia del control
PID cartesiano en tiempo real, mostrando el valor real vs el objetivo
(target) por iteracion.
"""

import pyqtgraph as pg
import numpy as np
import csv
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QFileDialog
from PyQt6.QtCore import Qt


# ==========================================================================
# CONFIGURACION ESTETICA Y FORMATO (MODIFICABLE)
# ==========================================================================
COLORES_REALES = ["#FF0000", "#026807", "#02488D"]
COLORES_TARGET = ["#000000", "#000000", "#000000"]
ETIQUETAS = ["X", "Y", "Z"]

class CartesianPIDPlot(QWidget):
    """
    Widget que grafica la convergencia del PID cartesiano en tiempo real
    utilizando PyQtGraph para alto rendimiento.
    """
    MAX_POINTS = 1000

    def __init__(self, parent=None):
        super().__init__(parent)
        self._real_data = [[] for _ in range(3)]
        self._target_data = [[] for _ in range(3)]
        self._time_data = []
        self.text_items = []
        self.proxies = []

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.plots = []
        self.real_lines = []
        self.target_lines = []

        for i in range(3):
            plot = pg.PlotWidget()
            plot.setBackground(None)
            plot.showGrid(x=True, y=True, alpha=0.3)
            plot.setLabel('left', ETIQUETAS[i], units='mm')

            # Asignar un margen inferior mayor al gráfico Z (i == 2) para que quepa la etiqueta
            bottom_margin = 10 if i == 2 else 5
            plot.getPlotItem().layout.setContentsMargins(10, 5, 10, bottom_margin)

            if i == 2:
                plot.setLabel('bottom', 'Tiempo', units='s')

            # Crear las curvas
            pen_real = pg.mkPen(color=COLORES_REALES[i], width=2)
            line_real = plot.plot(pen=pen_real, symbol='o', symbolSize=4, symbolBrush=COLORES_REALES[i])
            
            line_target = plot.plot(pen=pg.mkPen(color=COLORES_TARGET[i], width=1.5, style=Qt.PenStyle.DashLine))
            
            layout.addWidget(plot)
            self.plots.append(plot)
            self.real_lines.append(line_real)
            self.target_lines.append(line_target)

            # Elemento de texto para el hover
            text = pg.TextItem(anchor=(1, 0), color='w')
            text.hide()
            plot.addItem(text)
            self.text_items.append(text)

            # Proxy para detectar mouseMove
            proxy = pg.SignalProxy(plot.scene().sigMouseMoved, rateLimit=60, slot=lambda ev, idx=i: self.on_mouse_moved(ev, idx))
            self.proxies.append(proxy)

        # Botón de Guardar
        self.save_button = QPushButton("GUARDAR")
        self.save_button.clicked.connect(self.save_to_csv)
        layout.addWidget(self.save_button)

    def on_mouse_moved(self, event, idx):
        """Maneja el evento de movimiento del mouse sobre el gráfico idx."""
        if not self._time_data:
            return

        pos = event[0]
        plot = self.plots[idx]
        if plot.sceneBoundingRect().contains(pos):
            mouse_point = plot.getViewBox().mapSceneToView(pos)
            t_val = mouse_point.x()
            
            # Buscar el índice más cercano al tiempo del mouse
            idx_closest = np.argmin(np.abs(np.array(self._time_data) - t_val))
            
            # Actualizar texto
            time_val = self._time_data[idx_closest]
            real_val = self._real_data[idx][idx_closest]
            
            self.text_items[idx].setText(f"t: {time_val:.2f}s\nVal: {real_val:.2f}mm")
            self.text_items[idx].show()
        else:
            self.text_items[idx].hide()

    def save_to_csv(self):
        """Guarda los datos del gráfico a un archivo CSV."""
        if not self._time_data:
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Guardar datos", "", "CSV Files (*.csv)")
        if not file_path:
            return
            
        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Tiempo(s)", "X_real", "Y_real", "Z_real", "X_target", "Y_target", "Z_target"])
            
            # Iterar sobre la longitud de los datos y guardar fila a fila
            for i in range(len(self._time_data)):
                writer.writerow([
                    self._time_data[i],
                    self._real_data[0][i], self._real_data[1][i], self._real_data[2][i],
                    self._target_data[0][i], self._target_data[1][i], self._target_data[2][i]
                ])

    def update_theme(self, is_dark: bool):
        """
        Actualiza los colores de los gráficos según el tema (claro/oscuro).
        """
        bg_color = '#1e1e1e' if is_dark else '#ffffff'
        text_color = '#ffffff' if is_dark else '#000000'
        target_color = '#ffffff' if is_dark else '#000000'

        for i in range(3):
            self.plots[i].setBackground(bg_color)
            
            # Actualizar eje izquierdo (Y)
            styles = {'color': text_color, 'font-size': '8pt'}
            self.plots[i].getAxis('left').setLabel(ETIQUETAS[i], units='mm', **styles)
            self.plots[i].getAxis('left').setPen(color=text_color)
            self.plots[i].getAxis('left').setTextPen(color=text_color)
            
            # Actualizar eje inferior (X)
            self.plots[i].getAxis('bottom').setPen(color=text_color)
            self.plots[i].getAxis('bottom').setTextPen(color=text_color)

            if i == 2:
                self.plots[i].getAxis('bottom').setLabel('Tiempo', units='s', **styles)

            # Actualizar línea target
            self.target_lines[i].setPen(color=target_color, width=1.5, style=Qt.PenStyle.DashLine)
            
            # Actualizar color del texto
            self.text_items[i].setColor(text_color)

    def reset_plot(self, target_xyz):
        """
        Limpia los datos acumulados y prepara el grafico para un nuevo movimiento.
        """
        for i in range(3):
            self._real_data[i].clear()
            self._target_data[i].clear()
            self.real_lines[i].setData([], [])
            self.target_lines[i].setData([], [])
            
        self._time_data.clear()

    def append_data(self, time_s, actual_xyz, target_xyz):
        """
        Agrega un punto de datos y actualiza el grafico.
        """
        for i in range(3):
            self._real_data[i].append(actual_xyz[i])
            self._target_data[i].append(target_xyz[i])
        self._time_data.append(time_s)

        # Truncar si excede el límite
        if len(self._time_data) > self.MAX_POINTS:
            self._time_data.pop(0)
            for i in range(3):
                self._real_data[i].pop(0)
                self._target_data[i].pop(0)

        self._redraw()

    def _redraw(self):
        if not self._time_data:
            return

        x_vals = self._time_data
        
        for i in range(3):
            self.real_lines[i].setData(x_vals, self._real_data[i])
            self.target_lines[i].setData(x_vals, self._target_data[i])
            
            # Auto-ajuste simple
            self.plots[i].enableAutoRange(axis='y')
            self.plots[i].enableAutoRange(axis='x')
