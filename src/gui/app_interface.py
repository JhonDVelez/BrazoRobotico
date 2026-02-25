import os
import time
from ctypes import wintypes
from qframelesswindow import FramelessMainWindow
from PyQt6.QtWidgets import QMessageBox, QVBoxLayout, QWidget, QLabel, QApplication
from PyQt6.QtCore import QAbstractNativeEventFilter, QCoreApplication, QTimer
from .main_window import (MainInitMixin, MainActionsMixin, ThemeManager,
                         MainMenuMixin, MainThemeMixin, MainTitleBarMixin)

# --- IMPORTS PARA TELEMETRÍA ---
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.animation import FuncAnimation
import matplotlib.pyplot as plt
from robot.openbotv_worker import RobotWorker 

# Constantes de la API de Windows para detectar hardware
WM_DEVICECHANGE = 0x0219
DBT_DEVICEARRIVAL = 0x8000
DBT_DEVICEREMOVECOMPLETE = 0x8004

os.environ["QT_LOGGING_RULES"] = "qt.qpa.window=false"

class MainInterface(FramelessMainWindow, MainInitMixin, MainActionsMixin, MainMenuMixin,
                    MainThemeMixin):
    """ Ventana principal orquestadora del sistema. """

    def __init__(self, quick3d, robot_id, telemetry_data): 
        super().__init__()
        # Datos desde Splash Screen / Main
        self.preloaded_data = quick3d
        self.robot_id = robot_id
        self.telemetry = telemetry_data 
        
        # Estado inicial
        self.simulation_interface = None
        self.stopped = True
        self.camera_paused = False
        self.hab_simulation = True
        self.dark_theme = True
        self.ani = None # Referencia para evitar Garbage Collector
        
        self.theme_manager = ThemeManager.get_instance()
        
        # Estado de la conexión
        self.com = None
        self.com_connected_label = QLabel('No conectado')
        self.connected_to_robot = False
        self.worker = None # Inicializamos la referencia del hilo

        # --- CONSTRUCCIÓN DE LA UI ---
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.create_menu()
        self.title_bar = MainTitleBarMixin(self)
        self.setTitleBar(self.title_bar)
        layout.addWidget(self.title_bar)

        self.central_widget = QWidget()
        self.setup_ui(self.central_widget)
        layout.addWidget(self.central_widget)

        # Inicialización de módulos
        self.create_status_bar()
        self.init_camera()
        self.init_controls()
        self.init_simulation()
        self.init_graphics() 
        
        # Configuración de Gráficos y Eventos
        self.setup_telemetry_canvas()
        self.setup_connections()

        # Tema
        self.actual_theme = QApplication.instance().styleHints().colorScheme()
        self.update_theme(self.actual_theme)
        QApplication.instance().styleHints().colorSchemeChanged.connect(self.update_theme)

        self.setCentralWidget(container)
        self.resize(1280, 720)
        self.center_window()

        # Filtro de hardware (Windows)
        self._dev_filter = DeviceEventFilter(self.get_com_ports)
        QCoreApplication.instance().installNativeEventFilter(self._dev_filter)

    def setup_telemetry_canvas(self):
        """ Inicializa el lienzo de Matplotlib y lo integra en la UI. """
        plt.style.use('dark_background')
        self.fig, (self.ax_pos, self.ax_temp) = plt.subplots(2, 1, figsize=(5, 7))
        self.canvas = FigureCanvas(self.fig)
        self.fig.patch.set_facecolor('#1e1e1e') 
        
        if hasattr(self, 'graphLayout'):
            self.graphLayout.addWidget(self.canvas)
        
        self.canvas.hide()

        # Líneas y etiquetas
        self.lines_pos = [self.ax_pos.plot([], [], 'o-', label=f'M{i+1}', markersize=3)[0] for i in range(6)]
        self.lines_temp = [self.ax_temp.plot([], [], 'd-', label=f'M{i+1}', markersize=3)[0] for i in range(6)]
        self.temp_labels = [self.ax_temp.text(0, 0, "", fontweight='bold', fontsize=9) for _ in range(6)]

        self.ax_pos.set_title("Posición Real (Grados)", fontsize=10)
        self.ax_pos.set_ylim(-5, 305)
        self.ax_temp.set_title("Temperatura Real (°C)", fontsize=10)
        self.ax_temp.set_ylim(20, 80)
        self.ax_pos.grid(True, alpha=0.1)
        self.ax_temp.grid(True, alpha=0.1)
        plt.tight_layout()

    def connect_robot(self):
        """ Inicia el hilo Worker de forma segura. """
        if not self.com:
            QMessageBox.warning(self, "Puerto COM", "Seleccione un puerto serial válido primero.")
            return

        try:
            # Si el hilo ya existe, detenerlo correctamente antes de reiniciar
            if self.worker and self.worker.isRunning():
                self.worker.stop()
                self.worker.wait() 

            # Instanciar nuevo hilo con el puerto seleccionado
            self.worker = RobotWorker(self.com, self.telemetry)

            self.worker.signal_manager.send_to_robot.connect(self.worker.get_data_from_interface)
            
            # Conexión de señales de actualización de UI
            if hasattr(self, 'update_telemetry_labels'):
                self.worker.signal_manager.telemetry_updated.connect(self.update_telemetry_labels)
            
            self.worker.start()
            self.connected_to_robot = True
            self.com_connected_label.setText(f"Conectado: {self.com}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error de Conexión", f"No se pudo establecer la conexión: {e}")

    def manage_telemetry_lifecycle(self, checked):
        """ Gestiona la visibilidad y actualización de las gráficas. """
        if checked:
            # Solo permitir si el hilo está activo
            if self.worker and self.worker.isRunning():
                self.graph_interface.phy_graph_widget.hide()
                self.canvas.show()
                
                if self.ani is None:
                    self.ani = FuncAnimation(self.fig, self.update_telemetry_frame, 
                                           interval=100, cache_frame_data=False)
                else:
                    self.ani.event_source.start()
            else:
                self.robot_radio.blockSignals(True)
                self.robot_radio.setChecked(False)
                self.simulation_radio.setChecked(True)
                self.robot_radio.blockSignals(False)
                QMessageBox.warning(self, "Hardware", "El robot no está conectado o el hilo no ha iniciado.")
        else:
            if self.ani:
                self.ani.event_source.stop()
            self.canvas.hide()
            self.graph_interface.phy_graph_widget.show()

    def update_telemetry_frame(self, frame):
        """ Loop de actualización de gráficos (Matplotlib). """
        with self.telemetry['lock']:
            if not self.telemetry['history_pos'][0]:
                return self.lines_pos + self.lines_temp

            for i in range(6):
                p_data = self.telemetry['history_pos'][i]
                t_data = self.telemetry['history_temp'][i]

                if not t_data: continue

                x_vals = range(len(p_data))
                self.lines_pos[i].set_data(x_vals, p_data)
                self.lines_temp[i].set_data(x_vals, t_data)

                # Alerta visual de temperatura
                temp_val = t_data[-1]
                color = "#2ecc71" if temp_val < 55 else ("#f1c40f" if temp_val < 65 else "#e74c3c")
                
                self.temp_labels[i].set_text(f"{temp_val}°C")
                self.temp_labels[i].set_color(color)
                self.temp_labels[i].set_position((len(t_data)-1, temp_val + 2))

            # Ajuste de ventana de visualización (últimos 50 puntos)
            l_data = len(self.telemetry['history_pos'][0])
            self.ax_pos.set_xlim(max(0, l_data-50), l_data+5)
            self.ax_temp.set_xlim(max(0, l_data-50), l_data+5)
            
        self.canvas.draw_idle() 

    def setup_connections(self):
        """ Vincula los eventos de la UI con los métodos lógicos. """
        if hasattr(self, 'start_button'): self.start_button.clicked.connect(self.start)
        if hasattr(self, 'stop_button'): self.stop_button.clicked.connect(self.stop)
        
        # Conexión vital para el menú "Robot -> Conectar"
        if hasattr(self, 'connect_action'): 
            self.connect_action.triggered.connect(self.connect_robot)
        
        # Selectores de modo
        if hasattr(self, 'graph_interface'):
            self.robot_radio = self.graph_interface.phy_radio_button
            self.simulation_radio = self.graph_interface.sim_radio_button
            self.robot_radio.toggled.connect(self.manage_telemetry_lifecycle)

    def closeEvent(self, event):
        """ Cierre limpio garantizado para liberar el puerto COM. """
        reply = QMessageBox.question(
            self, "Salir", "¿Cerrar OpenBotv? (La conexión serial se perderá)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            print("Iniciando cierre de seguridad...")
            self.telemetry['running'] = False
            
            if self.ani:
                self.ani.event_source.stop()
            
            if self.worker and self.worker.isRunning():
                self.worker.stop() # Esto ahora cierra el puerto CM904 internamente
            
            event.accept()
        else:
            event.ignore()

class DeviceEventFilter(QAbstractNativeEventFilter):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def nativeEventFilter(self, eventType, message):
        msg = wintypes.MSG.from_address(message.__int__())
        if msg.message == WM_DEVICECHANGE:
            if msg.wParam in (DBT_DEVICEARRIVAL, DBT_DEVICEREMOVECOMPLETE):
                QTimer.singleShot(500, self.callback) # Delay de 500ms para que el SO registre el puerto
        return False, 0