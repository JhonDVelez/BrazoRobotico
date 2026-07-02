"""
Módulo que controla una gráfica individual de telemetría.

Este módulo define la clase PlotController, la cual actúa como el mediador
específico para un canal de datos (motor o eje cartesiano), gestionando su
configuración de escalas, visibilidad, exportación de datos y temas.

Conexiones:
    - Escucha `render_ready` del `PlotWorker` para actualizar el widget.
    - Responde a cambios de tema mediante `ThemeSignalManager`.
    - Proporciona un menú contextual para interacción directa del usuario.
"""

import numpy as np
from PyQt6.QtCore import QObject, pyqtSlot, Qt
from PyQt6.QtWidgets import QMenu, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QPushButton, QFileDialog, QMessageBox
from src.features.graph.plots.plot_widget import PlotWidget
from src.features.graph.plots.plot_worker import PlotWorker
from src.services.data.signals import ConfigSignalManager, ThemeSignalManager


class PlotController(QObject):
    """
    Controlador para una gráfica individual en el dashboard.

    Administra la sincronización entre el buffer de datos procesado por el worker
    y la representación visual en el PlotWidget, además de persistir las
    preferencias del usuario (escalas, cuadrícula).
    """

    def __init__(self, title: str, y_range: list, display_window: int, config: list, parent_widget=None):
        """
        Inicializa el controlador del plot con su configuración específica.

        Args:
            title (str): Título visible de la gráfica.
            y_range (list): Rango inicial [min, max] del eje Y.
            display_window (int): Puntos visibles en pantalla.
            config (list): Datos de configuración [índice, tipo, escalas, grid].
            parent_widget (QWidget, optional): Widget contenedor padre.
        """
        super().__init__()
        self._graph_index, self._graph_type, self._init_scale, self._grid_visible = config
        self._y_range = y_range
        self._display_window = display_window
        self._y_anchor_value = (y_range[0] + y_range[1]) / 2

        #         Buffers temporales para exportación de datos
        self._buffer_size = 10000
        self._y_sim_export = np.zeros(self._buffer_size, dtype=np.float32)
        self._y_phy_export = np.zeros(self._buffer_size, dtype=np.float32)
        self._write_index_export = 0
        self._buffer_full_export = False

        #         Configuración diferida: acumula cambios hasta flush en cierre de app
        self._pending_config = None

        # 1. Componentes de Visualizacion y Logica de Renderizado
        self._widget = PlotWidget(
            title, y_range, display_window, parent=parent_widget)
        self._worker = PlotWorker(display_window)

        # 2. Aplicar configuración inicial guardada
        self._setup_initial_config()

        # 3. Establecer conexiones
        self.__setup_connections()

    def _setup_initial_config(self):
        """
        Aplica las escalas X/Y y visibilidad de grid desde la configuración cargada.
        """
        self.set_x_scale(self._init_scale[0])
        self.set_y_scale(self._init_scale[1])
        self._widget.set_grid_visibility(self._grid_visible)

    def __setup_connections(self):
        """
        Configura las señales internas del controlador.
        """
        # Worker -> Widget (Notificación de frame de renderizado listo)
        self._worker.render_ready.connect(self._widget.set_curves_data)

        # Sincronización de Tema visual
        ThemeSignalManager.get_instance().theme_changed.connect(self._widget.apply_theme)

        # Menú contextual para interacción
        self._widget.context_menu_requested.connect(self._show_context_menu)

    # --- API de Datos ---

    def update_buffers(self, y_sim, y_phy, temp_phy, write_index, buffer_full, x_data):
        """
        Actualiza los datos del plot y notifica al worker de renderizado.

        Args:
            y_sim (np.ndarray): Buffer de datos de simulación.
            y_phy (np.ndarray): Buffer de datos físicos.
            temp_phy (str): Valor de temperatura actual.
            write_index (int): Índice de escritura actual en el buffer circular.
            buffer_full (bool): Indica si el buffer circular ya dio la vuelta.
            x_data (np.ndarray): Eje de tiempo/muestras.
        """
        # Guardar copia para exportación
        self._y_sim_export = y_sim
        self._y_phy_export = y_phy
        self._write_index_export = write_index
        self._buffer_full_export = buffer_full

        self._worker.update_visual_data(
            y_sim, y_phy, temp_phy, write_index, buffer_full)
        # El cursor necesita datos directos para interactuar con el mouse
        self._widget.update_cursor_data(x_data, y_sim, y_phy, write_index)

    # --- Gestión de UI y Escalas ---

    def set_x_scale(self, s_per_div: float):
        """
        Ajusta la escala de tiempo (Eje X) y guarda el cambio.

        Args:
            s_per_div (float): Segundos por division principal.
        """
        if s_per_div <= 0:
            return
        major = s_per_div * 10
        minor = s_per_div
        self._widget.set_tick_spacing(major, minor, None, None)

        visible_points = s_per_div * 100
        self._widget.set_view_range(x_range=[-visible_points, 0])
        self._save_config(0, s_per_div)

    def set_y_scale(self, units_per_div: float):
        """
        Ajusta la escala de magnitud (Eje Y) y guarda el cambio.

        Args:
            units_per_div (float): Unidades (grados o mm) por division.
        """
        if units_per_div <= 0:
            return
        major = units_per_div
        minor = units_per_div / 10
        self._widget.set_tick_spacing(None, None, major, minor)

        # Aplicar rango visual de 6 divisiones (3 arriba, 3 abajo del ancla)
        half_height = units_per_div * 3
        new_y_min = self._y_anchor_value - half_height
        new_y_max = self._y_anchor_value + half_height
        self._widget.set_view_range(y_range=[new_y_min, new_y_max])

        self._save_config(1, units_per_div)

    def _show_context_menu(self, pos):
        """
        Despliega el menú contextual con opciones de escala, grid y exportación.
        """
        menu = QMenu()

        grid_action = menu.addAction("Grid")
        grid_action.setCheckable(True)
        grid_action.setChecked(self._widget.get_grid_visibility())
        grid_action.triggered.connect(self.toggle_grid)
        menu.addSeparator()

        x_scale_menu = menu.addMenu("Escala X (s/div)")
        presets_x = [0.5, 1.0, 2.0, 5.0, 10.0]
        for preset in presets_x:
            action = x_scale_menu.addAction(f"{preset} s/div")
            action.triggered.connect(
                lambda checked, s=preset: self.set_x_scale(s))

        x_scale_menu.addSeparator()
        custom_x = x_scale_menu.addAction("Personalizado...")
        custom_x.triggered.connect(self._set_custom_x_scale)

        menu.addSeparator()
        y_scale_menu = menu.addMenu("Escala Y (unidades/div)")
        presets_y = [10, 20, 30, 50] if "motor" in self._widget.get_plot_title().lower() else [
            20, 50, 100, 200]
        for preset in presets_y:
            action = y_scale_menu.addAction(f"{preset}")
            action.triggered.connect(
                lambda checked, s=preset: self.set_y_scale(s))

        y_scale_menu.addSeparator()
        custom_y = y_scale_menu.addAction("Personalizado...")
        custom_y.triggered.connect(self._set_custom_y_scale)

        menu.addSeparator()
        export_action = menu.addAction("Exportar datos")
        export_action.triggered.connect(self._export_data)

        menu.exec(self._widget.mapToGlobal(pos))

    def _set_custom_x_scale(self):
        """
        Muestra un diálogo para que el usuario ingrese una escala X personalizada.
        """
        val, ok = self._show_spin_dialog(
            "Escala X personalizada", "Segundos por división (s/div):", 1, 1000)
        if ok:
            self.set_x_scale(val)

    def _set_custom_y_scale(self):
        """
        Muestra un diálogo para que el usuario ingrese una escala Y personalizada.
        """
        val, ok = self._show_spin_dialog(
            "Escala Y personalizada", "Unidades por división:", 1, 1000)
        if ok:
            self.set_y_scale(val)

    def _show_spin_dialog(self, title, label, min_v, max_v):
        """
        Crea y ejecuta un diálogo genérico con un QSpinBox.

        Args:
            title (str): Título de la ventana.
            label (str): Texto descriptivo.
            min_v (int): Valor mínimo del spin.
            max_v (int): Valor máximo del spin.

        Returns:
            tuple: (valor, aceptado) donde aceptado es bool.
        """
        dialog = QDialog(self._widget)
        dialog.setWindowTitle(title)
        layout = QVBoxLayout(dialog)
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel(label))
        spin = QSpinBox()
        spin.setRange(min_v, max_v)
        if "X" in title:
            spin.setValue(int(self._init_scale[0]))
        else:
            spin.setValue(int(self._init_scale[1]))
        h_layout.addWidget(spin)
        layout.addLayout(h_layout)

        btns = QHBoxLayout()
        ok = QPushButton("OK")
        cancel = QPushButton("Cancelar")
        ok.clicked.connect(dialog.accept)
        cancel.clicked.connect(dialog.reject)
        btns.addWidget(ok)
        btns.addWidget(cancel)
        layout.addLayout(btns)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            return spin.value(), True
        return 0, False

    def _export_data(self):
        """
        Exporta los datos acumulados en el buffer a formatos CSV, TXT o XLSX.
        """
        file_path, _ = QFileDialog.getSaveFileName(
            self._widget, "Exportar datos", "", "CSV (*.csv);;Texto (*.txt);;Excel (*.xlsx)"
        )
        if not file_path:
            return

        try:
            available_data = self._buffer_size if self._buffer_full_export else self._write_index_export
            if available_data == 0:
                QMessageBox.warning(self._widget, "Advertencia",
                                    "No hay datos para exportar")
                return

            time_points = np.arange(available_data) * 0.1
            sim_data = self._y_sim_export[:available_data]
            phy_data = self._y_phy_export[:available_data]

            if file_path.endswith('.csv') or file_path.endswith('.txt'):
                data = np.column_stack((time_points, sim_data, phy_data))
                with open(file_path, 'w') as f:
                    f.write("Tiempo (s),Simulación,Físico\n")
                    for row in data:
                        f.write(f"{row[0]:.1f},{row[1]:.4f},{row[2]:.4f}\n")
                QMessageBox.information(
                    self._widget, "Éxito", f"Datos exportados a:\n{file_path}")

            elif file_path.endswith('.xlsx'):
                try:
                    import pandas as pd
                    df = pd.DataFrame(
                        {'Tiempo (s)': time_points, 'Simulación': sim_data, 'Físico': phy_data})
                    df.to_excel(file_path, index=False, sheet_name='Datos')
                    QMessageBox.information(
                        self._widget, "Éxito", f"Datos exportados a:\n{file_path}")
                except ImportError:
                    QMessageBox.warning(
                        self._widget, "Error", "Se requiere 'openpyxl' y 'pandas' para exportar a Excel")
        except (OSError, IOError, ValueError) as e:
            print(f"[DEBUG] Error al exportar datos ({type(e).__name__}): {e}")
            QMessageBox.critical(self._widget, "Error",
                                 f"Error al exportar: {type(e).__name__}: {str(e)}")

    def toggle_grid(self):
        """
        Alterna la visibilidad de la cuadrícula de fondo del plot.
        """
        new_state = not self._widget.get_grid_visibility()
        self._widget.set_grid_visibility(new_state)
        self._save_config(2, new_state)

    def _save_config(self, index, value):
        """
        Acumula un cambio de configuración en memoria sin escribir a disco.

        Args:
            index (int): Índice del parámetro en la configuración.
            value: Valor a guardar (escala o booleano de grid).
        """
        # Cargar config completa solo cuando hay un cambio pendiente
        if self._pending_config is None:
            config_manager = ConfigSignalManager.get_instance()
            self._pending_config = config_manager.get_param(
                "graphics.json", "grid", self._graph_type)
        if self._pending_config and len(self._pending_config) > self._graph_index:
            self._pending_config[self._graph_index][index] = value

    def flush_pending_config(self):
        """
        Escribe a disco los cambios acumulados, si hay alguno pendiente.
        """
        if self._pending_config is None:
            return
        config_manager = ConfigSignalManager.get_instance()
        config_manager.request_change(
            "graphics.json", ["grid", self._graph_type], self._pending_config)
        self._pending_config = None

    def set_paused(self, paused: bool):
        """
        Pausa o reanuda el worker de renderizado asociado.

        Args:
            paused (bool): True para pausar.
        """
        self._worker.set_paused(paused)

    def set_visible(self, visible: bool):
        """
        Controla la visibilidad del widget y el worker para ahorrar CPU.

        Args:
            visible (bool): True para mostrar.
        """
        self._worker.set_visible(visible)
        if visible:
            self._widget.show()
        else:
            self._widget.hide()

    def get_widget(self):
        """
        Retorna el widget visual del plot.

        Returns:
            PlotWidget: Instancia del widget gráfico.
        """
        return self._widget
