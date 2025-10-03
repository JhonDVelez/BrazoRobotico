import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import QObject, QTimer, QElapsedTimer
from data.control_utils import SimulationSignalManager, PhysicalSignalManager, domains
from gui.main_window.theme_stylesheet import dark, light


class GraphWidget(QObject):
    def __init__(self, domain, display_window=10000):
        super().__init__()
        self.display_window = display_window  # Cantidad de puntos visibles
        self.__setup_ui(domain)
        self.__setup_connections()

    def __setup_ui(self, domain):
        self.graph_widget = pg.GraphicsLayoutWidget(show=False, title="Graph")

        # Optimizaciones globales de PyQtGraph
        pg.setConfigOptions(antialias=False)  # Desactiva antialiasing
        pg.setConfigOption('useOpenGL', True)  # Usa OpenGL si está disponible
        pg.setConfigOption('enableExperimental', True)

        self.motor_1 = upgradableGraph(self.graph_widget, "motor 1", [
                                       0, 0], self.display_window)
        self.motor_2 = upgradableGraph(self.graph_widget, "motor 2", [
                                       0, 1], self.display_window)
        self.motor_3 = upgradableGraph(self.graph_widget, "motor 3", [
                                       1, 0], self.display_window)
        self.motor_4 = upgradableGraph(self.graph_widget, "motor 4", [
                                       1, 1], self.display_window)
        self.motor_5 = upgradableGraph(self.graph_widget, "motor 5", [
                                       2, 0], self.display_window)
        self.motor_6 = upgradableGraph(self.graph_widget, "motor 6", [
                                       2, 1], self.display_window)

        if domain is domains.SIMULATION:
            self.signal_manager = SimulationSignalManager.get_instance()
        elif domain is domains.PHYSICAL:
            self.signal_manager = PhysicalSignalManager.get_instance()

        # Buffer para acumular actualizaciones
        self.update_buffer = []
        self.batch_size = 10  # Actualizar cada N muestras

        # Timer para actualizaciones periódicas (en lugar de cada dato)
        self.update_timer = QTimer()
        self.update_timer.setInterval(50)  # 50ms = ~20 FPS
        self.update_timer.timeout.connect(self._process_buffer)
        self.update_timer.start()

        # self.timer = QElapsedTimer()
        # self.timer.start()

    def set_display_window(self, window_size):
        """Cambia el tamaño de la ventana visible dinámicamente"""
        self.display_window = min(window_size, 30000)  # No más que el buffer
        self.motor_1.set_display_window(self.display_window)
        self.motor_2.set_display_window(self.display_window)
        self.motor_3.set_display_window(self.display_window)
        self.motor_4.set_display_window(self.display_window)
        self.motor_5.set_display_window(self.display_window)
        self.motor_6.set_display_window(self.display_window)

    def __setup_connections(self):
        self.signal_manager.update_graph_signal.connect(self.buffer_update)

    def buffer_update(self, data):
        """Acumula datos en buffer en lugar de actualizar inmediatamente"""
        # print(self.timer.elapsed())
        self.update_buffer.append(data)

    def _process_buffer(self):
        """Procesa el buffer acumulado"""
        if not self.update_buffer:
            return

        for data in self.update_buffer:
            self.motor_1.add_data(data[0])
            self.motor_2.add_data(data[1])
            self.motor_3.add_data(data[2])
            self.motor_4.add_data(data[3])
            self.motor_5.add_data(data[4])
            self.motor_6.add_data(data[5])

        self.update_buffer.clear()

        self.motor_1.update_plot()
        self.motor_2.update_plot()
        self.motor_3.update_plot()
        self.motor_4.update_plot()
        self.motor_5.update_plot()
        self.motor_6.update_plot()


class upgradableGraph(QObject):
    def __init__(self, graph_widget, title, pos, display_window=10000):
        super().__init__()
        self.graph_widget = graph_widget

        self.buffer_size = 30000
        self.display_window = min(display_window, self.buffer_size)
        self.y = np.zeros(self.buffer_size, dtype=np.float16)
        self.write_index = 0
        self.buffer_full = False

        self.graph_widget.setBackground('k')

        # Crear plot
        self.plot_item = self.graph_widget.addPlot(
            title=title, row=pos[0], col=pos[1])

        # Optimizaciones del plot
        self.plot_item.setDownsampling(mode='peak')
        self.plot_item.setClipToView(True)
        self.plot_item.enableAutoRange(axis='y', enable=False)
        self.plot_item.enableAutoRange(axis='x', enable=False)
        self.plot_item.setRange(
            xRange=[0, self.display_window], yRange=[-155, 155])
        self.plot_item.showGrid(x=True, y=True, alpha=0.5)

        pen = pg.mkPen(color=(200, 200, 200), width=1)

        self.curve = self.plot_item.plot(pen=pen, skipFiniteCheck=True)

    def set_display_window(self, window_size):
        """ Cambia el tamaño de la ventana visible
        """
        self.display_window = min(window_size, self.buffer_size)
        self.plot_item.setRange(xRange=[0, self.display_window], yRange=None)

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
                x_data = np.arange(
                    x_offset, self.display_window, dtype=np.float32)
                y_data = self.y[:self.write_index]
                self.curve.setData(x=x_data, y=y_data, skipFiniteCheck=True)
            else:
                start_idx = self.write_index - self.display_window
                y_data = self.y[start_idx:self.write_index]
                self.curve.setData(y_data, skipFiniteCheck=True)
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

                self.curve.setData(y_data, skipFiniteCheck=True)
