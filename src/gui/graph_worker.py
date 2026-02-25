""" En este modulo se define la estructura de la distribución de las gráficas asi como su diseño y
    el comportamiento definido al actualizar una vez se reciben datos nuevos.
"""
import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import QThread, QTimer
from data import SimulationSignalManager, PhysicalSignalManager, Domains


class GraphWorker(QThread):
    """ Hilo de procesamiento de los gráficos definiendo estructura, estilo, ubicacion y 
        su nombre asi como el tipo de señal que activará la actualización.
        Actúa como un coordinador que gestiona múltiples instancias de gráficos individuales.
    """

    def __init__(self, domain, display_window=1000):
        super().__init__()
        self.display_window = display_window
        self.__setup_ui(domain)
        self.__setup_connections()

    def __setup_ui(self, domain):
        """ Configura el contenedor principal de los gráficos y las optimizaciones de rendimiento.
        """
        # Widget de alto rendimiento para el diseño de múltiples gráficas
        self.graph_widget = pg.GraphicsLayoutWidget(show=False, title="Graph")
        self.graph_widget.setContentsMargins(0, 0, 0, 0)

        # Estilo CSS para eliminar bordes y ajustar el padding negativo para maximizar espacio
        self.graph_widget.setStyleSheet("""border: none;
                                        padding: 0px 0px 0px -5px;""")

        # Desactivar antialiasing para mejorar la velocidad de renderizado (crucial en tiempo real)
        pg.setConfigOptions(antialias=False)

        # Creación de los 6 gráficos (uno por cada motor del robot) en una cuadrícula de 3 filas x 2 columnas
        self.motor_1 = upgradableGraph(self.graph_widget, "motor 1", [0, 0], self.display_window)
        self.motor_2 = upgradableGraph(self.graph_widget, "motor 2", [0, 1], self.display_window)
        self.motor_3 = upgradableGraph(self.graph_widget, "motor 3", [1, 0], self.display_window)
        self.motor_4 = upgradableGraph(self.graph_widget, "motor 4", [1, 1], self.display_window)
        self.motor_5 = upgradableGraph(self.graph_widget, "motor 5", [2, 0], self.display_window)
        self.motor_6 = upgradableGraph(self.graph_widget, "motor 6", [2, 1], self.display_window)

        # Iniciar los hilos de gestión de cada gráfico
        self.motor_1.start()
        self.motor_2.start()
        self.motor_3.start()
        self.motor_4.start()
        self.motor_5.start()
        self.motor_6.start()

        # Selección del gestor de señales (Singleton) según si es Simulación o Robot Real
        if domain is Domains.SIMULATION:
            self.signal_manager = SimulationSignalManager.get_instance()
        elif domain is Domains.PHYSICAL:
            self.signal_manager = PhysicalSignalManager.get_instance()

        # Mecanismo de Buffer: Acumula datos para procesarlos en ráfagas y reducir carga de CPU
        self.update_buffer = []
        self.batch_size = 10

        # Temporizador para procesar el buffer cada 100ms (10Hz de refresco visual)
        self.update_timer = QTimer()
        self.update_timer.setInterval(100)
        self.update_timer.timeout.connect(self._process_buffer)
        self.update_timer.start()

    def __setup_connections(self):
        """ Conecta la señal global de datos con el método de acumulación en buffer.
        """
        self.signal_manager.update_graph_signal.connect(self.buffer_update)

    def buffer_update(self, data):
        """ Slot que recibe datos y los almacena en el buffer temporal.
        """
        self.update_buffer.append(data)

    def _process_buffer(self):
        """ Vuelca los datos acumulados en los hilos de los gráficos y dispara el repintado.
        """
        if not self.update_buffer:
            return

        # Distribución de cada elemento del array de datos al motor correspondiente
        for data in self.update_buffer:
            self.motor_1.add_data(data[0])
            self.motor_2.add_data(data[1])
            self.motor_3.add_data(data[2])
            self.motor_4.add_data(data[3])
            self.motor_5.add_data(data[4])
            self.motor_6.add_data(data[5])

        self.update_buffer.clear() # Limpiar buffer para la siguiente ráfaga

        # Disparar la actualización visual de todas las curvas
        self.motor_1.update_plot()
        self.motor_2.update_plot()
        self.motor_3.update_plot()
        self.motor_4.update_plot()
        self.motor_5.update_plot()
        self.motor_6.update_plot()


class upgradableGraph(QThread):
    """ Hilo encargado de la gestión de memoria y dibujo de un solo gráfico individual.
        Implementa un buffer circular para un desplazamiento (scroll) eficiente.
    """

    def __init__(self, graph_widget, title, pos, display_window=1000):
        super().__init__()
        self.graph_widget = graph_widget

        # Configuración del buffer de datos (10,000 puntos de historial)
        self.buffer_size = 10000
        self.display_window = min(display_window, self.buffer_size)
        
        # Arrays de NumPy con precisión de punto flotante para mayor velocidad
        self.y = np.zeros(self.buffer_size, dtype=np.float32)
        self.x_data = np.arange(-self.display_window/2,
                                self.display_window/2, dtype=np.float32)

        self.write_index = 0   # Puntero de escritura para el buffer circular
        self.buffer_full = False # Bandera para saber si ya empezamos a sobreescribir datos viejos

        # Agregar el área de dibujo al widget principal en la posición indicada
        self.plot_item = self.graph_widget.addPlot(
            title=title, row=pos[0], col=pos[1])

        # Desactivar interacción innecesaria para ganar rendimiento y estabilidad visual
        self.plot_item.autoBtn.clicked.disconnect()
        self.plot_item.setMouseEnabled(x=False)  # Impedir zoom en X para mantener la escala temporal
        self.plot_item.showGrid(x=True, y=True, alpha=0.5)

        # Técnicas avanzadas de PyQtGraph para gráficos en tiempo real
        self.plot_item.setDownsampling(mode='peak') # Muestra solo los picos si hay demasiados puntos
        self.plot_item.setClipToView(True)           # No dibuja puntos fuera del área visible
        self.plot_item.enableAutoRange(axis='y', enable=False) # Rango manual para evitar saltos
        self.plot_item.enableAutoRange(axis='x', enable=False)
        self.plot_item.setRange(
            xRange=[0, self.display_window],
            yRange=[-155, 155], # Rango de amplitud (ajustado a los límites del motor)
            padding=0.0
        )

        # Definición estética de la curva (color cian y grosor 3)
        pen = pg.mkPen(color=(24, 201, 167), width=3)
        self.curve = self.plot_item.plot(pen=pen, skipFiniteCheck=True) # skipFiniteCheck ahorra CPU

    def add_data(self, data):
        """ Inserta un nuevo punto en el buffer circular.
        """
        self.y[self.write_index] = data
        self.write_index += 1

        # Reiniciar el puntero si llegamos al final (comportamiento circular)
        if self.write_index >= self.buffer_size:
            self.write_index = 0
            self.buffer_full = True

    def update_plot(self):
        """ Calcula qué porción del buffer debe mostrarse para crear el efecto de "roll" u osciloscopio.
        """
        available_data = self.buffer_size if self.buffer_full else self.write_index
        points_to_show = min(self.display_window, available_data)

        if points_to_show == 0:
            return

        if not self.buffer_full:
            # Caso 1: El buffer aún no se ha llenado por primera vez
            if self.write_index <= self.display_window:
                x_offset = self.display_window - self.write_index
                y_data = self.y[:self.write_index]
                self.curve.setData(
                    x=self.x_data[x_offset:], y=y_data, skipFiniteCheck=True)
            else:
                # La ventana de visualización se desplaza con el puntero de escritura
                start_idx = self.write_index - self.display_window
                y_data = self.y[start_idx:self.write_index]
                self.curve.setData(x=self.x_data, y=y_data, skipFiniteCheck=True)
        else:
            # Caso 2: Buffer lleno. Requiere manejar el salto del final al inicio del array.
            if self.display_window >= self.buffer_size:
                # Reconstruir el array completo uniendo las dos mitades
                temp = np.concatenate([self.y[self.write_index:], self.y[:self.write_index]])
                self.curve.setData(temp, skipFiniteCheck=True)
            else:
                if self.write_index >= self.display_window:
                    start_idx = self.write_index - self.display_window
                    y_data = self.y[start_idx:self.write_index]
                else:
                    # Concatenar el final del buffer con el nuevo inicio para un scroll suave
                    wrap_amount = self.display_window - self.write_index
                    y_data = np.concatenate([
                        self.y[-wrap_amount:], 
                        self.y[:self.write_index]
                    ])

                self.curve.setData(x=self.x_data, y=y_data, skipFiniteCheck=True)
        
        # Ajuste final del ViewBox para centrar la ventana de tiempo
        vb = self.plot_item.getViewBox()
        vb.setXRange(-self.display_window/2, self.display_window/2, padding=0)