import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import QThread
from gui.main_window.theme_stylesheet import dark, light


class upgradableGraph(QThread):
    def __init__(self, graph_widget, title, pos, display_window=1000):
        super().__init__()
        self.graph_widget = graph_widget

        self.buffer_size = 10000
        self.display_window = min(display_window, self.buffer_size)
        self.y = np.zeros(self.buffer_size, dtype=np.float32)
        self.x_data = np.arange(-self.display_window/2,
                                self.display_window/2, dtype=np.float32)

        self.write_index = 0
        self.buffer_full = False

        # Crear plot
        self.plot_item = self.graph_widget.addPlot(
            title=title, row=pos[0], col=pos[1])

        # Configuraciones de funcionamiento
        # Se desconecta el boton de ajuste automatico
        self.plot_item.autoBtn.clicked.disconnect()
        self.plot_item.setMouseEnabled(x=False)  # Se evita el zoom en el eje x
        self.plot_item.showGrid(x=True, y=True, alpha=0.5)

        # Optimizaciones del plot
        self.plot_item.setDownsampling(mode='peak')
        self.plot_item.setClipToView(True)
        self.plot_item.enableAutoRange(axis='y', enable=False)
        self.plot_item.enableAutoRange(axis='x', enable=False)
        self.plot_item.setRange(
            xRange=[0, self.display_window],
            yRange=[-155, 155],
            padding=0.0
        )

        pen = pg.mkPen(color=(24, 201, 167), width=3)

        self.curve = self.plot_item.plot(pen=pen, skipFiniteCheck=True)

    def add_data(self, data):
        """ Agrega un dato al buffer circular
        """
        self.y[self.write_index] = data
        self.write_index += 1

        if self.write_index >= self.buffer_size:
            self.write_index = 0
            self.buffer_full = True

    def update_plot(self):
        """ Actualiza la visualización en modo roll
        """
        # Determinar cuántos datos realmente tenemos
        available_data = self.buffer_size if self.buffer_full else self.write_index
        # Usar solo los últimos display_window puntos
        points_to_show = min(self.display_window, available_data)

        if points_to_show == 0:
            return

        if not self.buffer_full:
            # Buffer parcialmente lleno
            if self.write_index <= self.display_window:
                x_offset = self.display_window - self.write_index

                y_data = self.y[:self.write_index]
                self.curve.setData(
                    x=self.x_data[x_offset:], y=y_data, skipFiniteCheck=True)
            else:
                start_idx = self.write_index - self.display_window
                y_data = self.y[start_idx:self.write_index]
                self.curve.setData(x=self.x_data, y=y_data,
                                   skipFiniteCheck=True)
        else:
            # Buffer lleno: extraer los últimos display_window puntos

            if self.display_window >= self.buffer_size:
                # Mostrar todo el buffer
                temp = np.concatenate([
                    self.y[self.write_index:],
                    self.y[:self.write_index]
                ])
                self.curve.setData(temp, skipFiniteCheck=True)
            else:
                # Calcular el índice de inicio en el buffer circular
                if self.write_index >= self.display_window:
                    start_idx = self.write_index - self.display_window
                    y_data = self.y[start_idx:self.write_index]
                else:
                    # Ventana cruza el límite del buffer circular
                    wrap_amount = self.display_window - self.write_index
                    y_data = np.concatenate([
                        self.y[-wrap_amount:],  # Final del buffer
                        self.y[:self.write_index]  # Inicio del buffer
                    ])

                self.curve.setData(x=self.x_data, y=y_data,
                                   skipFiniteCheck=True)
        vb = self.plot_item.getViewBox()
        vb.setXRange(-self.display_window/2, self.display_window/2, padding=0)
