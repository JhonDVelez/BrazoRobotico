import numpy as np
import pyqtgraph as pg
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (QWidget, QGridLayout, QMenu, QSpinBox, QLabel,
                             QVBoxLayout, QHBoxLayout, QDialog, QFileDialog, QMessageBox, QPushButton)
from PyQt6.QtCore import Qt
from .main_window.main_theme_mixin import ThemeManager


class upgradableGraph:
    """
    Clase encargada de manejar el buffer circular y la visualización
    tipo osciloscopio para una señal doble (Sim + Físico) con escalas configurables.
    """

    def __init__(self, graph_widget: QWidget, title: str, pos: list, y_range: list, display_window: int = 1000):
        super().__init__()
        self.graph_widget = graph_widget
        self.title = title
        self.pos = pos
        self.y_range = y_range

        # Parámetros de escala
        self.x_scale = 10.0  # s/div (10 segundos por división)
        # unidades por división (se establecerá según el tipo de gráfico)
        self.y_scale = 1.0
        self.grid_visible = True

        self.__setup_buffers(display_window)
        self.__setup_plots(y_range, title, pos)

        self.cursor = PlotCursor(self.plot_item)
        self.cursor_line = self.cursor.get_cursor_line()
        self.cursor_label = self.cursor.get_cursor_label()

        self.theme_manager = ThemeManager().get_instance()
        self.theme_manager.theme_changed.connect(self.theme_changed)

        # Configurar menú de contexto
        self.__setup_context_menu()

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

    def __setup_plots(self, y_range: list, title, pos):
        layout = self.graph_widget.layout()
        if layout is None:
            layout = QGridLayout(self.graph_widget)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            self.graph_widget.setLayout(layout)

        # Inyectar el eje personalizado
        self.x_axis = TimeAxisItem(orientation='bottom')
        plot_item = pg.PlotItem(title=title, axisItems={'bottom': self.x_axis})

        self.plot_widget = pg.PlotWidget(plotItem=plot_item)
        self.plot_widget.setViewportMargins(5, 0, 5, 0)
        self.plot_item = self.plot_widget.getPlotItem()
        self.view_box = self.plot_item.getViewBox()
        layout.addWidget(self.plot_widget, pos[0], pos[1])

        self.y_axis = self.plot_item.getAxis('left')

        # Forzar que el arrastre del mouse sea solo pan, no zoom de eje X
        self.view_box.setMouseMode(pg.ViewBox.PanMode)

        # Configuraciones de funcionamiento
        self.plot_item.autoBtn.clicked.disconnect()

        # Optimizaciones del plot
        self.plot_item.setDownsampling(mode='peak')
        self.plot_item.setClipToView(True)
        self.plot_item.enableAutoRange(axis='y', enable=False)
        self.plot_item.enableAutoRange(axis='x', enable=False)
        self.plot_item.setRange(
            xRange=[0, self.display_window],
            yRange=y_range,
            padding=0.0
        )
        self.plot_item.setMenuEnabled(False)
        self.view_box.sigRangeChanged.connect(self.fix_x_right_limit)
        self.view_box.sigRangeChanged.connect(self._save_y_view_state)
        self.view_box.setXRange(-self.display_window, 0, padding=0)
        y_min, y_max = y_range
        # Limitar el pan del mouse
        self.view_box.setLimits(xMin=-self.display_window,
                                xMax=0, yMin=y_min, yMax=y_max)
        self.view_box.wheelEvent = lambda ev: ev.ignore()

        # Curvas independientes
        pen_sim = pg.mkPen(color=(42, 176, 147), width=3)
        pen_phy = pg.mkPen(color=(189, 89, 42), width=2)

        self.curve_sim = self.plot_item.plot(pen=pen_sim, skipFiniteCheck=True)
        self.curve_phy = self.plot_item.plot(pen=pen_phy, skipFiniteCheck=True)

        # Texto de indicador de temperatura
        self.temp_text = pg.TextItem(self.temp_phy, anchor=(1, 0))
        self.plot_item.addItem(self.temp_text)
        self.plot_item.getViewBox().sigRangeChanged.connect(self._update_text_pos)
        self._save_y_view_state(
            self.view_box, self.plot_item.getViewBox().viewRange())
        self._update_text_pos()

        # --- REEMPLAZO DE LA GRID MANUAL ---
        self.set_x_scale(10.0)  # Setea 10s/div y configura los ticks de X
        # Setea 50 unidades/div y configura los ticks de Y
        self.set_y_scale(50.0)

    # --- Actualizaciones visuales ----------------------------------------------------------------

    def _update_text_pos(self):
        vb = self.plot_item.getViewBox()
        x_range, y_range = vb.viewRange()
        x_pos = x_range[1]
        y_pos = y_range[1]
        self.temp_text.setPos(x_pos, y_pos)

    def fix_x_right_limit(self, view_box, view_range):
        """Asegura que el rango X no exceda los límites permitidos sin deformar la escala."""
        x_range, _ = view_range
        x_min, x_max = x_range
        current_width = x_max - x_min
        needs_correction = False

        limit_min = -self.display_window * 1.05
        if x_min < limit_min:
            corrected_min = limit_min
            corrected_max = corrected_min + current_width
            needs_correction = True
        elif x_max > 0:
            corrected_max = 0
            corrected_min = corrected_max - current_width
            needs_correction = True

        if needs_correction:
            view_box.blockSignals(True)
            view_box.setXRange(corrected_min, corrected_max, padding=0)
            view_box.blockSignals(False)
            self.plot_item.showGrid(
                x=self.grid_visible, y=self.grid_visible, alpha=0.5)

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

        self.cursor.update_data(self.x_data, self.y_sim,
                                self.y_phy, self.write_index)

    def show_no_data(self):
        self.curve_sim.clear()
        self.curve_phy.clear()

    def stop(self):
        self.write_index = 0
        self.y_sim = np.zeros(self.buffer_size, dtype=np.float32)
        self.y_phy = np.zeros(self.buffer_size, dtype=np.float32)

    # --- Actualización de datos en el plot -------------------------------------------------------

    def update_plot(self):
        available_data = self.buffer_size if self.buffer_full else self.write_index
        points_to_show = min(self.display_window, available_data)

        if points_to_show == 0:
            return

        if not self.buffer_full:
            if self.write_index <= self.display_window:
                x_offset = self.display_window - self.write_index
                y_sim_data = self.y_sim[:self.write_index]
                y_phy_data = self.y_phy[:self.write_index]
                self.temp_text.setText(f"{self.temp_phy}")

                self.curve_sim.setData(x=self.x_data[x_offset:], y=y_sim_data)
                self.curve_phy.setData(x=self.x_data[x_offset:], y=y_phy_data)
            else:
                start_idx = self.write_index - self.display_window
                y_sim_data = self.y_sim[start_idx:self.write_index]
                y_phy_data = self.y_phy[start_idx:self.write_index]

                self.curve_sim.setData(
                    self.x_data, y_sim_data, skipFiniteCheck=True)
                self.curve_phy.setData(
                    self.x_data, y_phy_data, skipFiniteCheck=True)
        else:
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

    # --- Manejo de tema --------------------------------------------------------------------------

    def theme_changed(self, dark_t: bool):
        if dark_t:
            self.cursor_label.setColor(pg.mkColor(241, 57, 47))
            self.cursor_line.setPen(
                pg.mkPen(pg.mkColor(150, 150, 150), width=2))
            self.cursor_line.setHoverPen(
                pg.mkPen(pg.mkColor(241, 57, 47), width=2))
            self.plot_widget.setBackground(pg.mkColor((32, 33, 36)))
        else:
            self.cursor_label.setColor(pg.mkColor(0, 129, 219))
            self.cursor_line.setPen(
                pg.mkPen(pg.mkColor(150, 150, 150), width=2))
            self.cursor_line.setHoverPen(
                pg.mkPen(pg.mkColor(0, 129, 219), width=2))
            self.plot_widget.setBackground(pg.mkColor((248, 249, 250)))

    # --- Menú de contexto personalizado ----------------------------------------------------------

    def __setup_context_menu(self):
        self.plot_widget.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu)
        self.plot_widget.customContextMenuRequested.connect(
            self._show_context_menu)

    def _show_context_menu(self, pos):
        menu = QMenu(self.plot_widget)
        grid_action = menu.addAction("Grid")
        grid_action.setCheckable(True)
        grid_action.setChecked(self.grid_visible)
        grid_action.triggered.connect(self._toggle_grid)
        menu.addSeparator()

        x_scale_menu = menu.addMenu("Escala X (s/div)")
        presets_x = [0.5, 1.0, 2.0, 5.0, 10.0]
        for preset in presets_x:
            action = x_scale_menu.addAction(f"{preset} s/div")
            action.triggered.connect(
                lambda checked, s=preset: self.set_x_scale(s))

        x_scale_menu.addSeparator()
        custom_x_action = x_scale_menu.addAction("Personalizado...")
        custom_x_action.triggered.connect(self._set_custom_x_scale)

        menu.addSeparator()
        y_scale_menu = menu.addMenu("Escala Y (unidades/div)")
        if "motor" in self.title.lower():
            presets_y = [10, 20, 30, 50, 75, 100, 150]
        else:
            presets_y = [50, 100, 200, 500, 1000]

        for preset in presets_y:
            action = y_scale_menu.addAction(f"{preset}")
            action.triggered.connect(
                lambda checked, s=preset: self.set_y_scale(s))

        y_scale_menu.addSeparator()
        custom_y_action = y_scale_menu.addAction("Personalizado...")
        custom_y_action.triggered.connect(self._set_custom_y_scale)

        menu.addSeparator()
        export_action = menu.addAction("Exportar datos")
        export_action.triggered.connect(self._export_data)
        menu.exec(self.plot_widget.mapToGlobal(pos))

    def _toggle_grid(self):
        self.grid_visible = not self.grid_visible
        self.plot_item.showGrid(x=self.grid_visible,
                                y=self.grid_visible, alpha=0.5)

    # --- IMPLEMENTACIÓN DE SET_TICK_SPACING NATIVO ---

    def set_x_scale(self, s_per_div: float):
        """Cambia la escala X usando el motor interno de pyqtgraph."""
        if s_per_div <= 0:
            return
        self.x_scale = s_per_div

        # 1 segundo = 10 puntos en X. Por lo tanto, el salto principal es (s_per_div * 10)
        major_step = s_per_div * 10
        minor_step = s_per_div  # Subdivisión visual

        self.x_axis.setTickSpacing(major=major_step, minor=minor_step)

        # Actualizar rango visible para mantener las 10 divisiones de ancho
        visible_points = s_per_div * 100
        self.view_box.setXRange(-visible_points, 0, padding=0)
        self.plot_item.showGrid(x=self.grid_visible,
                                y=self.grid_visible, alpha=0.5)

    def set_y_scale(self, units_per_div: float):
        """Cambia la escala Y usando el motor interno de pyqtgraph."""
        if units_per_div <= 0:
            return
        self.y_scale = units_per_div

        major_step = units_per_div
        minor_step = units_per_div / 10

        self.y_axis.setTickSpacing(major=major_step, minor=minor_step)
        self._apply_y_scale()

    def _save_y_view_state(self, view_box, view_range):
        _, y_range = view_range
        y_min, y_max = y_range
        self.y_anchor_value = (y_min + y_max) / 2

    def _apply_y_scale(self):
        if not hasattr(self, 'y_anchor_value'):
            y_min, y_max = self.plot_item.getViewBox().viewRange()[1]
            self.y_anchor_value = (y_min + y_max) / 2

        new_height = self.y_scale * 6
        half_height = new_height / 2
        new_y_min = self.y_anchor_value - half_height
        new_y_max = self.y_anchor_value + half_height
        self.view_box.setYRange(new_y_min, new_y_max, padding=0)
        self.plot_item.showGrid(x=self.grid_visible,
                                y=self.grid_visible, alpha=0.5)

    def _set_custom_x_scale(self):
        dialog = QDialog(self.plot_widget)
        dialog.setWindowTitle("Escala X personalizada")
        layout = QVBoxLayout()
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel("Segundos por división (s/div):"))
        spinbox = QSpinBox()
        spinbox.setMinimum(1)
        spinbox.setMaximum(1000)
        spinbox.setValue(int(self.x_scale))
        spinbox.setSuffix(" s")
        h_layout.addWidget(spinbox)
        layout.addLayout(h_layout)

        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancelar")
        ok_button.clicked.connect(
            lambda: (self.set_x_scale(spinbox.value()), dialog.accept()))
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        dialog.exec()

    def _set_custom_y_scale(self):
        dialog = QDialog(self.plot_widget)
        dialog.setWindowTitle("Escala Y personalizada")
        layout = QVBoxLayout()
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel("Unidades por división:"))
        spinbox = QSpinBox()
        spinbox.setMinimum(1)
        spinbox.setMaximum(1000)
        spinbox.setValue(int(self.y_scale))
        h_layout.addWidget(spinbox)
        layout.addLayout(h_layout)

        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancelar")
        ok_button.clicked.connect(
            lambda: (self.set_y_scale(spinbox.value()), dialog.accept()))
        cancel_button.clicked.connect(dialog.reject)
        button_layout = QHBoxLayout()
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        dialog.exec()

    def _export_data(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self.plot_widget, "Exportar datos", "", "CSV (*.csv);;Texto (*.txt);;Excel (*.xlsx)"
        )
        if not file_path:
            return

        try:
            available_data = self.buffer_size if self.buffer_full else self.write_index
            if available_data == 0:
                QMessageBox.warning(
                    self.plot_widget, "Advertencia", "No hay datos para exportar")
                return

            time_points = np.arange(available_data) * 0.1

            if file_path.endswith('.csv') or file_path.endswith('.txt'):
                sim_data = self.y_sim[:available_data]
                phy_data = self.y_phy[:available_data]
                data = np.column_stack((time_points, sim_data, phy_data))

                with open(file_path, 'w') as f:
                    f.write("Tiempo (s),Simulación,Físico\n")
                    for row in data:
                        f.write(f"{row[0]:.1f},{row[1]:.4f},{row[2]:.4f}\n")

                QMessageBox.information(
                    self.plot_widget, "Éxito", f"Datos exportados correctamente a:\n{file_path}")

            elif file_path.endswith('.xlsx'):
                try:
                    import pandas as pd
                    sim_data = self.y_sim[:available_data]
                    phy_data = self.y_phy[:available_data]
                    df = pd.DataFrame(
                        {'Tiempo (s)': time_points, 'Simulación': sim_data, 'Físico': phy_data})
                    df.to_excel(file_path, index=False, sheet_name='Datos')
                    QMessageBox.information(
                        self.plot_widget, "Éxito", f"Datos exportados correctamente a:\n{file_path}")
                except ImportError:
                    QMessageBox.warning(
                        self.plot_widget, "Error", "Se requiere 'openpyxl' y 'pandas' para exportar a Excel")
        except Exception as e:
            QMessageBox.critical(self.plot_widget, "Error",
                                 f"Error al exportar: {str(e)}")


# --- Cursor personalizado para mediciones --------------------------------------------------------

class PlotCursor:
    def __init__(self, parent: pg.PlotItem) -> None:
        self.plot_item = parent
        self.view_box = parent.getViewBox()
        self.x_data = None
        self.y_sim = None
        self.y_phy = None
        self.write_index = None
        self.relative_pos = 0.5
        self.__setup_cursor()

    def get_cursor_line(self):
        return self.cursor_line

    def get_cursor_label(self):
        return self.cursor_label

    def __setup_cursor(self, init_pos: int = -500):
        self.cursor_line = pg.InfiniteLine(
            angle=90, movable=True, span=(1, -1))
        self.cursor_label = pg.TextItem(fill=pg.mkBrush(120, 120, 120, 50))
        font = QFont()
        font.setBold(True)
        font.setPixelSize(12)
        self.cursor_label.setFont(font)
        self.cursor_line.sigPositionChanged.connect(self.update_cursor)
        self.view_box.sigRangeChanged.connect(
            self.adjust_cursor_on_range_change)
        self.cursor_line.setValue(init_pos)
        self.plot_item.addItem(self.cursor_line, ignoreBounds=True)
        self.plot_item.addItem(self.cursor_label, ignoreBounds=True)

    def update_data(self, x_data, y_sim, y_phy, write_index):
        self.x_data = x_data
        self.y_sim = y_sim
        self.y_phy = y_phy
        self.write_index = write_index
        self.update_cursor()

    def adjust_cursor_on_range_change(self):
        x_min, x_max = self.view_box.viewRange()[0]
        new_x = x_min + self.relative_pos * (x_max - x_min)
        self.cursor_line.blockSignals(True)
        self.cursor_line.setValue(new_x)
        self.cursor_line.blockSignals(False)
        self.update_cursor()

    def update_cursor(self):
        if self.x_data is None:
            return

        x_val = self.cursor_line.value()
        x_val = np.clip(x_val, self.x_data[0], self.x_data[-1])

        x_min, x_max = self.view_box.viewRange()[0]
        if x_max > x_min:
            self.relative_pos = (x_val - x_min) / (x_max - x_min)

        real_x = self.x_data[np.argmin(np.abs(self.x_data - x_val))]
        real_y_sim = self.y_sim[int(self.write_index + x_val)]
        real_y_phy = self.y_phy[int(self.write_index + x_val)]

        [x_min, x_max], [y_min, y_max] = self.plot_item.getViewBox().viewRange()

        view_width = x_max - x_min
        view_height = y_max - y_min

        # MULTIPLICAMOS X POR -0.1 AQUÍ TAMBIÉN PARA QUE EL TEXTO COINCIDA CON LA ESCALA EN SEGUNDOS
        text = f"X: {-real_x * 0.1:.1f} s\nY sim: {real_y_sim:.2f}\nY phy: {real_y_phy:.2f}"

        self.cursor_label.setText(text)
        self.cursor_label.setPos(real_x, np.clip(real_y_sim, y_min, y_max))

        self.cursor_label.setAnchor((1 if real_x > x_max - (view_width * 0.18)
                                    else 0, 0 if real_y_sim > y_max - (view_height * 0.4) else 1))


# --- CLASE PARA EJE X (Transforma puntos a segundos y positivos) ---------------------------------


class TimeAxisItem(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):
        # Cada punto en X equivale a 0.1s (10 Hz).
        # Multiplicamos por -0.1 para mostrar segundos positivos
        return [f"{-v * 0.1:g}" for v in values]
