""" En este modulo se define el menu que se integrara a la barra de titulo y como se comporta.
"""
import os
from PyQt6.QtGui import QAction, QKeySequence, QIcon, QPixmap, QActionGroup
from PyQt6.QtWidgets import QMenuBar, QSizePolicy, QLabel, QStatusBar
from PyQt6.QtCore import Qt
from serial.tools import list_ports
from robot.openbotv_worker import RobotWorker
from data import DataFlow


class MainMenuMixin:
    """ Mixin encargado de definir el menu, las acciones que hará y su comportamiento con estas.
        Centraliza la gestión de comandos del usuario y la detección de hardware (puertos COM).
    """

    def __init__(self):
        # Referencias a los controladores de datos y comunicación con el hardware
        self.robot_controller = None
        self.openbotv = None

    def create_actions(self):
        """ Define las acciones (QAction) que tendrá el menu asi como sus atajos, 
            texto de la barra de estado e iconos utilizados como botones.
        """
        # --- Acciones de Visibilidad ---
        self.camera_action = QAction("Ocultar Cámara", self)
        self.camera_action.setShortcut(QKeySequence("Ctrl+j"))
        self.camera_action.setStatusTip("Mostrar/Ocultar la cámara")

        self.model_action = QAction("Ocultar Modelo 3D", self)
        self.model_action.setShortcut(QKeySequence("Ctrl+k"))
        self.model_action.setStatusTip("Mostrar/Ocultar el modelo 3D")

        # --- Acciones de Control y Simulación ---
        self.sliders_action = QAction("Sliders", self)
        self.sliders_action.setShortcut(QKeySequence("Ctrl+t"))
        self.sliders_action.setStatusTip("Modo de control con sliders")

        self.simulation_action = QAction("Desactivar simulación", self)
        self.simulation_action.setShortcut(QKeySequence("Ctrl+y"))
        self.simulation_action.setStatusTip("Activar/Desactivar simulación")

        # --- Gestión de Apariencia (Temas) ---
        self.sun_icon = QIcon(os.path.join(
            os.path.dirname(__file__), "..", "icons", "sun.png"))
        self.moon_icon = QIcon(os.path.join(
            os.path.dirname(__file__), "..", "icons", "moon.png"))

        self.theme_action = QAction(
            self.sun_icon, "Cambiar tema", self)
        self.theme_action.setShortcut(QKeySequence("Ctrl+l"))
        self.theme_action.setStatusTip("Cambiar tema")

        # --- Acción de Conexión Serial ---
        self.connect_action = QAction("Conectar", self)
        self.connect_action.setEnabled(False) # Deshabilitado hasta que se elija un puerto válido

    def create_menu(self):
        """ Define la estructura del menu y submenus basado en las acciones definidas.
            Organiza las opciones en categorías lógicas (Vista, Modo, Simulación, Robot).
        """
        self.create_actions()
        self.menu_bar = QMenuBar()
        self.menu_bar.setFixedHeight(32)
        self.menu_bar.setContentsMargins(0, 0, 0, 0)
        self.menu_bar.adjustSize()

        # Configuración del Logo en la esquina izquierda de la barra de menú
        self.logo_label = QLabel()
        self.laser_w = QPixmap(os.path.join(
            os.path.dirname(__file__), "..",
            "img", "laser_w.png")).scaledToHeight(20, Qt.TransformationMode.SmoothTransformation)
        self.laser_b = QPixmap(os.path.join(
            os.path.dirname(__file__), "..",
            "img", "laser_b.png")).scaledToHeight(20, Qt.TransformationMode.SmoothTransformation)
        self.logo_label.setPixmap(self.laser_w)
        self.logo_label.setContentsMargins(8, 0, 5, 0)

        self.menu_bar.setCornerWidget(self.logo_label, Qt.Corner.TopLeftCorner)

        # --- Construcción de la jerarquía de Menús ---
        self.vista_menu = self.menu_bar.addMenu("&Vista")
        self.vista_menu.addAction(self.camera_action)
        self.vista_menu.addAction(self.model_action)

        self.mode_menu = self.menu_bar.addMenu("&Modo")
        self.mode_menu.addAction(self.sliders_action)

        self.simulation_menu = self.menu_bar.addMenu("&Simulación")
        self.simulation_menu.addAction(self.simulation_action)

        # Menú de Robot con Submenú dinámico para puertos COM
        self.robot_menu = self.menu_bar.addMenu("&Robot")
        self.com_submenu = self.robot_menu.addMenu("&Puerto")
        
        # QActionGroup permite que solo un puerto pueda estar seleccionado a la vez
        self.com_group = QActionGroup(self)
        self.com_group.setExclusive(True)
        
        self.get_com_ports() # Población inicial de puertos
        self.robot_menu.addAction(self.connect_action)

        self.menu_bar.setSizePolicy(
            QSizePolicy(QSizePolicy.Policy.Preferred,
                        QSizePolicy.Policy.Preferred)
        )

    def get_com_ports(self):
        """ Escanea el sistema en busca de puertos de comunicación serial y los expone como un
            submenu para que el usuario seleccione el puerto del microcontrolador del robot.
        """
        available_ports = list_ports.comports()

        # Limpieza previa del menú y del grupo de acciones para evitar duplicados
        self.com_submenu.clear()
        for action in list(self.com_group.actions()):
            self.com_group.removeAction(action)

        if available_ports:
            # Control de habilitación del submenú según el estado de la aplicación
            if self.stopped:
                self.com_submenu.setEnabled(False)
            else:
                self.com_submenu.setEnabled(True)
                
            # Iteración sobre puertos detectados por el sistema operativo
            for port in available_ports:
                com_action = self.com_submenu.addAction(port.description)
                com_action.setCheckable(True)
                # Almacenamos el identificador del dispositivo (ej. COM3) en el Data de la acción
                com_action.setData(port.device)
                com_action.setStatusTip(f"Conectar al puerto {port.device}")
                self.com_group.addAction(com_action)
                # Conexión de la señal al cambiar la selección
                com_action.triggered.connect(self.com_checkable_change)

                # Si el puerto coincide con el ya seleccionado, marcarlo como activo
                if self.com == port.device:
                    com_action.setChecked(True)
        else:
            # Estado de fallback si no hay dispositivos conectados
            self.connect_action.setEnabled(False)
            self.com_submenu.setEnabled(False)
            self.com = None
            self._stop_threads()
            self.com_connected_label.setText("No conectado")

    def com_checkable_change(self, checked):
        """ Slot que detecta cuando el usuario selecciona un puerto COM en la UI.
            Gestiona la transición de estados entre una conexión previa y una nueva.

        Args:
            checked (bool): Indica si el puerto ha sido marcado.
        """
        action = self.sender()
        if not self.com:
            self._stop_threads()
            
        if action and checked:
            self.com = action.data() # Obtiene el puerto (ej. "COM5")
            # Habilita el botón "Conectar" solo si no hay procesos corriendo actualmente
            if (not getattr(self, "openbotv", None) and
                not getattr(self, "robot_controller", None) and
                    not self.stopped):
                self.connect_action.setEnabled(True)

    def _stop_threads(self):
        """ Detiene y elimina los hilos activos de forma segura.
            Implementa un cierre limpio (exit -> wait -> deleteLater) para evitar fugas de memoria
            o cierres inesperados al cambiar de puerto.
        """
        # Finalización segura del controlador de flujo de datos
        if getattr(self, "robot_controller", None):
            try:
                if isinstance(self.robot_controller, DataFlow):
                    self.robot_controller.exit()
                    self.robot_controller.wait()
                    self.robot_controller.deleteLater()
            except RuntimeError:
                pass
            finally:
                self.robot_controller = None

        # Finalización segura del hilo de comunicación serial del robot
        if getattr(self, "openbotv", None):
            try:
                if isinstance(self.openbotv, RobotWorker):
                    self.openbotv.exit()
                    self.openbotv.wait()
                    self.openbotv.deleteLater()
            except RuntimeError:
                pass
            finally:
                self.openbotv = None

    def create_status_bar(self):
        """ Crea la barra de estado (QStatusBar) en la parte inferior de la ventana.
            Integra un widget permanente para mostrar el estado actual del puerto serial.
        """
        status_bar = QStatusBar(self)
        # com_connected_label debe estar definido en el Mixin de inicialización
        status_bar.addPermanentWidget(self.com_connected_label)
        self.setStatusBar(status_bar)