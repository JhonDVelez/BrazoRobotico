"""
Modulo que define el widget de grafico cartesiano basado en PyQtGraph.

Proporciona la clase CartesianPIDPlot, un widget Qt que contiene tres
subplots (X, Y, Z) de PyQtGraph para visualizar la convergencia del control
PID cartesiano en tiempo real, mostrando el valor real vs el objetivo
(target) por iteracion.
"""

import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QVBoxLayout
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

    def __init__(self, parent=None):
        super().__init__(parent)
        self._real_data = [[] for _ in range(3)]
        self._target_data = [[] for _ in range(3)]
        self._time_data = []

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
            if i == 2:
                plot.setLabel('bottom', 'Tiempo', units='s')
            
            # Crear las curvas
            # Real: línea sólida con marcadores
            pen_real = pg.mkPen(color=COLORES_REALES[i], width=2)
            line_real = plot.plot(pen=pen_real, symbol='o', symbolSize=4, symbolBrush=COLORES_REALES[i])
            
            # Target: línea discontinua
            line_target = plot.plot(pen=pg.mkPen(color=COLORES_TARGET[i], width=1.5, style=Qt.PenStyle.DashLine))
            
            layout.addWidget(plot)
            self.plots.append(plot)
            self.real_lines.append(line_real)
            self.target_lines.append(line_target)

    def update_theme(self, is_dark: bool):
        """
        Actualiza los colores de los gráficos según el tema (claro/oscuro).
        """
        bg_color = '#1e1e1e' if is_dark else '#ffffff'
        text_color = '#ffffff' if is_dark else '#000000'
        target_color = '#ffffff' if is_dark else '#000000'

        for i in range(3):
            self.plots[i].setBackground(bg_color)
            
            # Actualizar ejes
            styles = {'color': text_color, 'font-size': '8pt'}
            self.plots[i].getAxis('left').setLabel(ETIQUETAS[i], units='mm', **styles)
            self.plots[i].getAxis('left').setPen(color=text_color)
            self.plots[i].getAxis('left').setTextPen(color=text_color)
            
            if i == 2:
                self.plots[i].getAxis('bottom').setLabel('Tiempo', units='s', **styles)
                self.plots[i].getAxis('bottom').setPen(color=text_color)
                self.plots[i].getAxis('bottom').setTextPen(color=text_color)
                self.plots[i].getAxis('bottom').setHeight(60) # Aumentar altura reservada
                self.plots[i].getAxis('bottom').setStyle(tickTextOffset=10) # Ajustar margen del texto
            else:
                self.plots[i].getAxis('bottom').setPen(color=text_color)
                self.plots[i].getAxis('bottom').setTextPen(color=text_color)

            # Actualizar linea target
            self.target_lines[i].setPen(color=target_color, width=1.5, style=Qt.PenStyle.DashLine)

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
