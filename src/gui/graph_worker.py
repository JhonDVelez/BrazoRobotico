""" En este modulo se define la estructura de la distribución de las gráficas asi como su diseño y
    el comportamiento definido al actualizar una vez se reciben datos nuevos.
"""
import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import QThread, QTimer
from data import SimulationSignalManager, PhysicalSignalManager, Domains


class GraphWorker(QThread):
    """ Hilo de procesamiento de los gráficos definiendo estructura, estilo, ubicacion y 
        su nombre asi como el tipo de señal que activará la actualización
    """

    def __init__(self, domain, display_window=1000):
        super().__init__()
        self.display_window = display_window
        self.__setup_ui(domain)
        self.__setup_connections()

    def __setup_ui(self, domain):
        # Crear widget de gráficos con márgenes en cero
        self.graph_widget = pg.GraphicsLayoutWidget(show=False, title="Graph")
        self.graph_widget.setContentsMargins(0, 0, 0, 0)

        # Remover bordes y márgenes del GraphicsLayoutWidget
        self.graph_widget.setStyleSheet("""border: none;
                                        padding: 0px 0px 0px -5px;""")

        # Optimizaciones globales de PyQtGraph
        pg.setConfigOptions(antialias=False)
        # pg.setConfigOption('useOpenGL', True)

        # Crear gráficos individuales
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

        self.motor_1.start()
        self.motor_2.start()
        self.motor_3.start()
        self.motor_4.start()
        self.motor_5.start()
        self.motor_6.start()

        # Configurar signal manager según dominio
        if domain is Domains.SIMULATION:
            self.signal_manager = SimulationSignalManager.get_instance()
        elif domain is Domains.PHYSICAL:
            self.signal_manager = PhysicalSignalManager.get_instance()

        # Buffer para acumular actualizaciones
        self.update_buffer = []
        self.batch_size = 10

        # Timer para actualizaciones periódicas
        self.update_timer = QTimer()
        self.update_timer.setInterval(100)
        self.update_timer.timeout.connect(self._process_buffer)
        self.update_timer.start()

    def __setup_connections(self):
        self.signal_manager.update_graph_signal.connect(self.buffer_update)

    def buffer_update(self, data):
        """Acumula datos en buffer en lugar de actualizar inmediatamente"""
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


class upgradableGraph(QThread):
    """ Hilo de procesamiento para el procesamiento y actualización de cada gráfico individual.
    """

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
