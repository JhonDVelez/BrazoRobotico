"""
Modulo que define los componentes visuales de bajo nivel para las graficas.

Este modulo contiene clases especializadas basadas en `pyqtgraph` para
renderizar datos en tiempo real, incluyendo el manejo de ejes temporales,
cursores de medicion y el widget principal de plot optimizado.
"""

import numpy as np
import pyqtgraph as pg
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (QWidget, QLabel)
from PyQt6.QtCore import Qt, pyqtSignal


class TimeAxisItem(pg.AxisItem):
    """
    Componente para el eje X que transforma indices en tiempo (segundos).

    Sobreescribe `tickStrings` para mostrar valores de tiempo positivos
    basados en una frecuencia de muestreo de 10 Hz.
    """

    def tickStrings(self, values, scale, spacing):
        """
        Convierte los valores numericos del eje en cadenas de texto de tiempo.

        Args:
            values (list): Valores numericos de los ticks.
            scale (float): Escala actual.
            spacing (float): Espaciado entre ticks.

        Returns:
            list: Lista de etiquetas formateadas (e.g. '0.5s').
        """
        # Cada punto en X equivale a 0.1s (10 Hz).
        return [f"{-v * 0.1:g}" for v in values]


class PlotCursor:
    """
    Cursor interactivo para realizar mediciones sobre las graficas.

    Permite al usuario desplazar una linea vertical y visualizar los valores
    exactos de simulacion y hardware en un punto temporal especifico.
    """

    def __init__(self, parent_plot: pg.PlotItem) -> None:
        """
        Inicializa el cursor y lo añade al plot proporcionado.

        Args:
            parent_plot (pg.PlotItem): Grafica donde se renderizara el cursor.
        """
        self._plot_item = parent_plot
        self._view_box = parent_plot.getViewBox()
        self._x_data = None
        self._y_sim = None
        self._y_phy = None
        self._write_index = None
        self._relative_pos = 0.5
        self.__setup_cursor()

    def __setup_cursor(self, init_pos: int = -500):
        """
        Configura la linea infinita y la etiqueta de texto del cursor.
        """
        self._cursor_line = pg.InfiniteLine(
            angle=90, movable=True, span=(1, -1))
        self._cursor_label = pg.TextItem(fill=pg.mkBrush(120, 120, 120, 255))
        font = QFont()
        font.setBold(True)
        font.setPixelSize(12)
        self._cursor_label.setFont(font)

        self._cursor_line.sigPositionChanged.connect(self.update_cursor)
        self._view_box.sigRangeChanged.connect(
            self._adjust_cursor_on_range_change)

        self._cursor_line.setValue(init_pos)
        self._plot_item.addItem(self._cursor_line, ignoreBounds=True)
        self._plot_item.addItem(self._cursor_label, ignoreBounds=True)

    def update_data(self, x_data, y_sim, y_phy, write_index):
        """
        Actualiza los buffers de datos internos del cursor para busqueda.

        Args:
            x_data (np.ndarray): Datos del eje X.
            y_sim (np.ndarray): Buffer de simulacion.
            y_phy (np.ndarray): Buffer fisico.
            write_index (int): Indice de escritura circular.
        """
        self._x_data = x_data
        self._y_sim = y_sim
        self._y_phy = y_phy
        self._write_index = write_index
        self.update_cursor()

    def _adjust_cursor_on_range_change(self):
        """
        Mantiene la posicion relativa del cursor cuando se cambia el zoom o escala.
        """
        x_min, x_max = self._view_box.viewRange()[0]
        if x_max > x_min:
            new_x = x_min + self._relative_pos * (x_max - x_min)
            self._cursor_line.blockSignals(True)
            self._cursor_line.setValue(new_x)
            self._cursor_line.blockSignals(False)
            self.update_cursor()

    def update_cursor(self):
        """
        Recalcula la posicion de la etiqueta y extrae los valores bajo el cursor.
        """
        if self._x_data is None:
            return

        x_val = self._cursor_line.value()
        x_val = np.clip(x_val, self._x_data[0], self._x_data[-1])

        x_min, x_max = self._view_box.viewRange()[0]
        if x_max > x_min:
            self._relative_pos = (x_val - x_min) / (x_max - x_min)

        idx = np.argmin(np.abs(self._x_data - x_val))
        real_x = self._x_data[idx]

        # Acceso a datos circulares mediante el indice de escritura
        real_y_sim = self._y_sim[int(
            self._write_index + x_val) % len(self._y_sim)]
        real_y_phy = self._y_phy[int(
            self._write_index + x_val) % len(self._y_phy)]

        view_range = self._plot_item.getViewBox().viewRange()
        y_min, y_max = view_range[1]
        view_width = x_max - x_min
        view_height = y_max - y_min

        text = f"X: {-real_x * 0.1:.1f} s\nY sim: {real_y_sim:.2f}\nY phy: {real_y_phy:.2f}"
        self._cursor_label.setText(text)
        self._cursor_label.setPos(real_x, np.clip(real_y_sim, y_min, y_max))

        # Ajuste inteligente de ancla para evitar que la etiqueta salga del plot
        anchor_x = 1 if real_x > x_max - (view_width * 0.18) else 0
        anchor_y = 0 if real_y_sim > y_max - (view_height * 0.4) else 1
        self._cursor_label.setAnchor((anchor_x, anchor_y))

    def get_cursor_line(self):
        """
        Retorna la instancia de la linea infinita del cursor.

        Returns:
            pg.InfiniteLine: Linea vertical del cursor.
        """
        return self._cursor_line

    def get_cursor_label(self):
        """
        Retorna el item de texto de la etiqueta del cursor.

        Returns:
            pg.TextItem: Etiqueta informativa.
        """
        return self._cursor_label


class PlotWidget(pg.PlotWidget):
    """
    Widget especializado para la visualizacion de una grafica tipo osciloscopio.

    Encapsula toda la logica visual de pyqtgraph, incluyendo optimizaciones
    de downsampling, recorte de vista y manejo de temas claros/oscuros.

    Attributes:
        context_menu_requested (pyqtSignal): Emite la posicion del mouse para el menu.
    """
    context_menu_requested = pyqtSignal(object)  # pos

    def __init__(self, title: str, y_range: list, display_window: int, parent=None):
        """
        Inicializa el PlotWidget inyectando el eje de tiempo personalizado.

        Args:
            title (str): Titulo de la grafica.
            y_range (list): Limites [min, max] del eje Y.
            display_window (int): Ancho de la ventana visible.
            parent (QWidget, optional): Widget padre.
        """
        # Inyectar eje X personalizado
        self._x_axis = TimeAxisItem(orientation='bottom')
        plot_item = pg.PlotItem(title=title, axisItems={
                                'bottom': self._x_axis})
        super().__init__(parent=parent, plotItem=plot_item)

        self._title = title
        self._y_range = y_range
        self._display_window = display_window
        self._grid_visible = True

        self.__setup_ui()
        self._cursor = PlotCursor(self.getPlotItem())
        self.setObjectName("plot_widget")

    def __setup_ui(self):
        """
        Configura los parametros visuales y optimizaciones de Pyqtgraph.
        """
        self.setViewportMargins(5, 0, 5, 0)
        self.setStyleSheet("border: none; padding: 0px 0px 0px -5px;")
        self.plot_item = self.getPlotItem()
        self.view_box = self.plot_item.getViewBox()
        self._y_axis = self.plot_item.getAxis('left')

        # Configuración de interacción
        self.view_box.setMouseMode(pg.ViewBox.PanMode)
        try:
            self.plot_item.autoBtn.clicked.disconnect()
        except Exception:
            pass

        # Optimizaciones de rendimiento para hilos de alta frecuencia
        self.plot_item.setDownsampling(mode='peak')
        self.plot_item.setClipToView(True)
        self.plot_item.enableAutoRange(axis='y', enable=False)
        self.plot_item.enableAutoRange(axis='x', enable=False)
        self.plot_item.setMenuEnabled(False)  # Deshabilitar menú nativo de pg

        self.view_box.setXRange(-self._display_window, 0, padding=0)
        self.view_box.setLimits(xMin=-self._display_window * 1.05, xMax=0,
                                yMin=self._y_range[0], yMax=self._y_range[1])

        # Definicion de curvas: Simulado (Verde) y Fisico (Naranja)
        self._curve_sim = self.plot_item.plot(pen=pg.mkPen(
            color=(42, 176, 147), width=3), skipFiniteCheck=True)
        self._curve_phy = self.plot_item.plot(pen=pg.mkPen(
            color=(189, 89, 42), width=2), skipFiniteCheck=True)

        # Texto informativo de temperatura en esquina
        self._temp_text = pg.TextItem("", anchor=(1, 0))
        self.plot_item.addItem(self._temp_text)
        self.view_box.sigRangeChanged.connect(self._update_elements_pos)

        # Politica de menu contextual personalizado
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(
            self.context_menu_requested.emit)

    def wheelEvent(self, ev):
        """
        Ignora el zoom con la rueda del mouse para mantener escalas fijas calibradas.
        """
        ev.ignore()

    def _update_elements_pos(self):
        """
        Ajusta la posicion de los elementos flotantes (labels) al cambiar la vista.
        """
        x_range, y_range = self.view_box.viewRange()
        self._temp_text.setPos(x_range[1], y_range[1])

    # --- API Pública (Getters / Setters) ---

    def set_curves_data(self, x, y_sim, y_phy, temp_text=""):
        """
        Asigna nuevos datos a las curvas del plot.

        Args:
            x (np.ndarray): Eje horizontal.
            y_sim (np.ndarray): Datos de simulacion.
            y_phy (np.ndarray): Datos reales.
            temp_text (str): Texto de temperatura a mostrar.
        """
        self._curve_sim.setData(x, y_sim)
        self._curve_phy.setData(x, y_phy)
        self._temp_text.setText(temp_text)

    def update_cursor_data(self, x_data, y_sim, y_phy, write_index):
        """
        Actualiza el cursor con el estado mas reciente del buffer.

        Args:
            x_data (np.ndarray): Eje de tiempo.
            y_sim (np.ndarray): Buffer de simulacion.
            y_phy (np.ndarray): Buffer fisico.
            write_index (int): Indice de escritura circular.
        """
        self._cursor.update_data(x_data, y_sim, y_phy, write_index)

    def set_grid_visibility(self, visible: bool):
        """
        Muestra u oculta la cuadricula de fondo del plot.

        Args:
            visible (bool): True para mostrar la cuadricula.
        """
        self._grid_visible = visible
        self.plot_item.showGrid(x=visible, y=visible, alpha=0.3)

    def get_grid_visibility(self) -> bool:
        """
        Retorna True si la cuadricula esta visible.

        Returns:
            bool: Estado de visibilidad del grid.
        """
        return self._grid_visible

    def set_tick_spacing(self, x_major, x_minor, y_major, y_minor):
        """
        Configura el espaciado de las marcas de los ejes.

        Args:
            x_major (float or None): Espaciado mayor del eje X.
            x_minor (float or None): Espaciado menor del eje X.
            y_major (float or None): Espaciado mayor del eje Y.
            y_minor (float or None): Espaciado menor del eje Y.
        """
        if x_major:
            self._x_axis.setTickSpacing(major=x_major, minor=x_minor)
        if y_major:
            self._y_axis.setTickSpacing(major=y_major, minor=y_minor)

    def set_view_range(self, x_range=None, y_range=None):
        """
        Establece la ventana visual actual del plot.

        Args:
            x_range (list, optional): Limites [min, max] del eje X.
            y_range (list, optional): Limites [min, max] del eje Y.
        """
        if x_range:
            self.view_box.setXRange(x_range[0], x_range[1], padding=0)
        if y_range:
            self.view_box.setYRange(y_range[0], y_range[1], padding=0)

    def apply_theme(self, dark_t: bool):
        """
        Aplica los colores de fondo, lineas y cursor segun el tema seleccionado.

        Args:
            dark_t (bool): True para modo oscuro.
        """
        if dark_t:
            color_cursor = "#1A70E6"
            color_bg = "#191B20"
            color_line = (150, 150, 150)
            color_hover = "#6A9BD9"
            brush_fill = pg.mkBrush(10, 10, 10, 100)
        else:
            color_cursor = "#2378D5"
            color_bg = "#E6E8ED"
            color_line = (150, 150, 150)
            color_hover = "#5394E6"
            brush_fill = pg.mkBrush(180, 180, 180, 100)

        self.setBackground(pg.mkColor(color_bg))
        self._cursor.get_cursor_label().setColor(pg.mkColor(color_cursor))
        self._cursor.get_cursor_label().fill = brush_fill
        self._cursor.get_cursor_line().setPen(pg.mkPen(pg.mkColor(color_line), width=2))
        self._cursor.get_cursor_line().setHoverPen(
            pg.mkPen(pg.mkColor(color_hover), width=2))

    def get_plot_title(self) -> str:
        """
        Obtiene el titulo de la grafica.

        Returns:
            str: Titulo del plot.
        """
        return self._title
