""" En este modulo se define la estructura de la distribución de las gráficas asi como su diseño y
    el comportamiento definido al actualizar una vez se reciben datos nuevos.
"""
import numpy as np
import pyqtgraph as pg
from PyQt6.QtGui import QFont
from PyQt6.QtCore import QThread, QTimer
from data import SimulationSignalManager, PhysicalSignalManager
from .kinematics_worker import KinematicsWorker
from .main_window.main_theme_mixin import ThemeManager


class GraphWorker(QThread):
    """ Hilo de procesamiento de los gráficos definiendo estructura, estilo, ubicación y
        conexiones con los managers de señales.
    """

    def __init__(self, display_window: int = 1000, graphs_amount: int = 6):
        super().__init__()
        self.display_window = display_window
        self.graphs_amount = graphs_amount
        self.is_paused = False

        self.__setup_ui()
        self.__setup_connections()

    def __setup_ui(self):
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
        self.motors = []

        # Etiquetas por cantidad
        labels = [f"motor {i+1}" for i in range(self.graphs_amount)]
        if self.graphs_amount == 3:
            labels = ["X", "Y", "Z"]

        for i in range(self.graphs_amount):
            if self.graphs_amount == 3:
                row = i
                col = 0
            else:
                row = i // 2
                col = i % 2

            motor = upgradableGraph(
                self.graph_widget,
                labels[i],
                [row, col],
                self.display_window
            )
            self.motors.append(motor)

        # Managers independientes
        self.sim_signal_manager = SimulationSignalManager.get_instance()
        self.phy_signal_manager = PhysicalSignalManager.get_instance()

        # Buffer para acumular actualizaciones
        self.sim_update_buffer = []
        self.phy_update_buffer = []
        self.phy_temp_data = []

        # Timer para actualizaciones periódicas
        self.update_timer = QTimer()
        self.update_timer.setInterval(100)
        self.update_timer.timeout.connect(self._process_buffer)
        self.update_timer.start()

        self.kinematics_worker = KinematicsWorker()

    def __setup_connections(self):
        if self.graphs_amount == 6:
            self.sim_signal_manager.update_graph_signal.connect(
                self.sim_angular_buffer_update)
            self.phy_signal_manager.data_received.connect(
                self.phy_angular_buffer_update)
        elif self.graphs_amount == 3:
            self.sim_signal_manager.update_graph_signal.connect(
                self.sim_cartesian_buffer_update)
            self.phy_signal_manager.data_received.connect(
                self.phy_cartesian_buffer_update)

    def sim_angular_buffer_update(self, data):
        if self.is_paused:
            return
        data[1] *= -1
        data[2] *= -1
        self.sim_update_buffer.append(data)

    def phy_angular_buffer_update(self, pos_data, temp_data):
        if self.is_paused:
            return
        pos_data[0] -= 150
        pos_data[1] = -pos_data[1] + 150
        pos_data[2] = -pos_data[2] + 150
        pos_data[3] -= 150
        pos_data[4] -= 150
        pos_data[5] -= 150

        self.phy_update_buffer.append(pos_data)
        self.phy_temp_data.append(temp_data)

    def sim_cartesian_buffer_update(self, data):
        if self.is_paused:
            return
        data_rad = np.array([
            np.deg2rad(data[0]),
            np.deg2rad(-data[1]),
            np.deg2rad(-data[2]),
            np.deg2rad(data[4]),
        ]).reshape((4, 1))
        pos = self.kinematics_worker.cd(
            data_rad[0, 0], data_rad[1, 0], data_rad[2, 0], data_rad[3, 0])
        self.sim_update_buffer.append(pos)

    def phy_cartesian_buffer_update(self, pos_data, temp_data):
        if self.is_paused:
            return
        data_rad = np.array([
            np.deg2rad(pos_data[0] - 150.0),
            np.deg2rad(150.0 - pos_data[1]),
            np.deg2rad(150.0 - pos_data[2]),
            np.deg2rad(pos_data[4] - 150.0),
        ]).reshape((4, 1))
        cartesian_pos = self.kinematics_worker.cd(
            data_rad[0, 0], data_rad[1, 0], data_rad[2, 0], data_rad[3, 0])
        self.phy_update_buffer.append(cartesian_pos)
        self.phy_temp_data.append(temp_data)

    def _process_buffer(self):
        if self.is_paused:
            return

        # Si no hay datos de ningún tipo
        if not self.sim_update_buffer and not self.phy_update_buffer:
            for motor in self.motors:
                motor.show_no_data()
            return

        # Procesar simulación
        for sim_data in self.sim_update_buffer:
            for motor, value in zip(self.motors, sim_data):
                motor.add_sim(value)

        # Procesar físico (si existe)
        for phy_data, temp_data in zip(self.phy_update_buffer, self.phy_temp_data):
            for motor, pos_value, temp_value in zip(self.motors, phy_data, temp_data):
                motor.add_phy(pos_value, temp_value)

        # Actualizar visualización
        for motor in self.motors:
            motor.update_plot()

        self.sim_update_buffer.clear()
        self.phy_update_buffer.clear()

    def start(self):
        self.is_paused = False

    def pause(self):
        """ Pausa la actualización de los valores guardados.
        """
        self.is_paused = not self.is_paused

    def stop(self):
        """ Detiene el proceso de actualización y limpia los valores guardados
        """
        self.is_paused = True
        for motor in self.motors:
            motor.stop()


class upgradableGraph:
    """
    Clase encargada de manejar el buffer circular y la visualización
    tipo osciloscopio para una señal doble (Sim + Físico).
    """

    def __init__(self, graph_widget, title: str, pos, display_window: int = 1000):
        super().__init__()
        self.graph_widget = graph_widget

        self.__setup_buffers(display_window)
        self.__setup_plots(title, pos)
        self.__setup_cursor()

        self.theme_manager = ThemeManager().get_instance()
        self.theme_manager.theme_changed.connect(self.theme_changed)

    # --- Setup ----------------------------------------------------------------------------------

    def __setup_buffers(self, display_window: int):
        # Parámetros de buffer
        self.buffer_size = 10000
        self.display_window = min(display_window, self.buffer_size)

        # Buffers independientes
        self.y_sim = np.zeros(self.buffer_size, dtype=np.float32)
        self.y_phy = np.zeros(self.buffer_size, dtype=np.float32)
        self.temp_phy = ""

        # Eje X fijo centrado (comportamiento osciloscopio)
        self.x_data = np.arange(
            -self.display_window,
            0,
            dtype=np.float32
        )

        self.write_index = 0
        self.buffer_full = False

    def __setup_plots(self, title, pos):
        # Crea eje X con etiquetas personalizadas para que los valores de tiempo sean positivos
        custom_x_axis = CustomAxisItem(orientation='bottom')

        # Crear plot
        self.plot_item = self.graph_widget.addPlot(
            title=title, row=pos[0], col=pos[1], axisItems={'bottom': custom_x_axis})

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

        # Curvas independientes
        pen_sim = pg.mkPen(color=(42, 176, 147), width=3)
        pen_phy = pg.mkPen(color=(189, 89, 42), width=2)

        self.curve_sim = self.plot_item.plot(
            pen=pen_sim, skipFiniteCheck=True)
        self.curve_phy = self.plot_item.plot(
            pen=pen_phy, skipFiniteCheck=True)

        # Texto de indicador de temperatura del robot físico
        self.temp_text = pg.TextItem(self.temp_phy, anchor=(1, 0))
        self.plot_item.addItem(self.temp_text)
        self.plot_item.getViewBox().sigRangeChanged.connect(self._update_text_pos)
        self._update_text_pos()

    def __setup_cursor(self):
        self.cursor_line = pg.InfiniteLine(
            angle=90, movable=True)
        self.plot_item.addItem(self.cursor_line)
        self.cursor_label = pg.TextItem(fill=pg.mkBrush(120, 120, 120, 50))
        font = QFont()
        font.setBold(True)
        font.setPixelSize(12)
        self.cursor_label.setFont(font)
        self.plot_item.addItem(self.cursor_label)
        self.cursor_line.sigPositionChanged.connect(self.update_cursor)
        self.cursor_line.setValue(-500)

    # --- Actualizaciones visuales ----------------------------------------------------------------

    def update_cursor(self):
        x_val = self.cursor_line.value()
        x_val = np.clip(x_val, self.x_data[0], self.x_data[-1])

        real_x = self.x_data[np.argmin(np.abs(self.x_data - x_val))]
        real_y = self.y_sim[int(self.write_index + x_val)]

        [x_min, x_max], [y_min, y_max] = self.plot_item.getViewBox().viewRange()

        # Calcular el ancho y alto visible actualmente
        view_width = x_max - x_min
        view_height = y_max - y_min

        # Definir texto y orientación de la etiqueta
        text = f"X: {-real_x:.1f}\nY: {real_y:.3f}"
        self.cursor_label.setText(text)
        self.cursor_label.setPos(real_x, np.clip(real_y, y_min, y_max))

        # Aplicamos el anclaje dinámico
        self.cursor_label.setAnchor((1 if real_x > x_max - (view_width * 0.15)
                                    else 0, 0 if real_y > y_max - (view_height * 0.15) else 1))

    def _update_text_pos(self):
        vb = self.plot_item.getViewBox()
        x_range, y_range = vb.viewRange()
        # Posicionar en esquina superior derecha con un pequeño margen
        x_pos = x_range[1]  # extremo derecho
        y_pos = y_range[1]  # extremo superior
        self.temp_text.setPos(x_pos, y_pos)

    # --- Manejo de datos entrantes ---------------------------------------------------------------

    def add_phy(self, pos_value, temp_value):
        self.y_phy[self.write_index] = pos_value
        self.temp_phy = temp_value

    def add_sim(self, value):
        self.y_sim[self.write_index] = value

        self.write_index += 1

        if self.write_index >= self.buffer_size:
            self.write_index = 0
            self.buffer_full = True

        self.update_cursor()

    # Mostrar mensaje cuando no hay ejecución
    def show_no_data(self):
        self.curve_sim.clear()
        self.curve_phy.clear()

    def stop(self):
        self.write_index = 0
        self.y_sim = np.zeros(self.buffer_size, dtype=np.float32)
        self.y_phy = np.zeros(self.buffer_size, dtype=np.float32)

    # --- Actualización de datos en el plot -------------------------------------------------------

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

                y_sim_data = self.y_sim[:self.write_index]
                y_phy_data = self.y_phy[:self.write_index]
                self.temp_text.setText(f"{self.temp_phy}")

                self.curve_sim.setData(
                    x=self.x_data[x_offset:], y=y_sim_data)
                # print(len(self.x_data[x_offset:]), len(y_sim_data))
                self.curve_phy.setData(
                    x=self.x_data[x_offset:], y=y_phy_data)

            else:
                start_idx = self.write_index - self.display_window

                y_sim_data = self.y_sim[start_idx:self.write_index]
                y_phy_data = self.y_phy[start_idx:self.write_index]

                self.curve_sim.setData(
                    self.x_data, y_sim_data, skipFiniteCheck=True)
                self.curve_phy.setData(
                    self.x_data, y_phy_data, skipFiniteCheck=True)

        else:
            # Buffer lleno: extraer los últimos display_window puntos

            if self.write_index >= self.display_window:
                start_idx = self.write_index - self.display_window

                y_sim_data = self.y_sim[start_idx:self.write_index]
                y_phy_data = self.y_phy[start_idx:self.write_index]

            else:
                wrap_amount = self.display_window - self.write_index

                y_sim_data = np.concatenate([
                    self.y_sim[-wrap_amount:],
                    self.y_sim[:self.write_index]
                ])
                y_phy_data = np.concatenate([
                    self.y_phy[-wrap_amount:],
                    self.y_phy[:self.write_index]
                ])

            self.curve_sim.setData(self.x_data, y_sim_data)
            self.curve_phy.setData(self.x_data, y_phy_data)

        # Mantener eje centrado (efecto osciloscopio)
        vb = self.plot_item.getViewBox()
        vb.setXRange(
            -self.display_window,
            0,
            padding=0
        )

    # --- Manejo de tema --------------------------------------------------------------------------

    def theme_changed(self, dark_t: bool):
        if dark_t:
            self.cursor_label.setColor(pg.mkColor(241, 57, 47))
            self.cursor_line.setPen(
                pg.mkPen(pg.mkColor(150, 150, 150), width=2))
            self.cursor_line.setHoverPen(
                pg.mkPen(pg.mkColor(241, 57, 47), width=2))
        else:
            self.cursor_label.setColor(pg.mkColor(0, 129, 219))
            self.cursor_line.setPen(
                pg.mkPen(pg.mkColor(150, 150, 150), width=2))
            self.cursor_line.setHoverPen(
                pg.mkPen(pg.mkColor(0, 129, 219), width=2))


class CustomAxisItem(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):
        # 'values' es la lista de puntos en X que pyqtgraph decide mostrar en ese momento
        # Multiplicamos por -1 para hacerlos positivos y usamos :g para un formato limpio
        return [f"{-v:g}" for v in values]
