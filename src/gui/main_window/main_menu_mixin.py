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
    """ Mixin encargado de definir el menu, las acciones que hará y su comportamiento con estas
    """

    def __init__(self):
        self.robot_controller = None
        self.openbotv = None

    def create_actions(self):
        """ Define las acciones que tendrá el menu asi como sus atajos, texto de la barra de estado
            e iconos utilizados como botones.
        """
        self.camera_action = QAction("Mostrar Cámara", self)
        self.camera_action.setShortcut(QKeySequence("Ctrl+j"))
        self.camera_action.setStatusTip("Mostrar/Ocultar la cámara")

        self.model_action = QAction("Ocultar Modelo 3D", self)
        self.model_action.setShortcut(QKeySequence("Ctrl+k"))
        self.model_action.setStatusTip("Mostrar/Ocultar el modelo 3D")

        self.sliders_action = QAction("Sliders", self)
        self.sliders_action.setShortcut(QKeySequence("Ctrl+t"))
        self.sliders_action.setStatusTip("Modo de control con sliders")

        self.angular_action = QAction("Angular", self)
        self.angular_action.setShortcut(QKeySequence("Ctrl+A"))
        self.angular_action.setStatusTip("Modo angular (control por ángulos)")

        self.cartesian_action = QAction("Cartesiano", self)
        self.cartesian_action.setShortcut(QKeySequence("Ctrl+X"))
        self.cartesian_action.setStatusTip("Modo cartesiano (cinemática)")

        self.simulation_action = QAction("Desactivar simulación", self)
        self.simulation_action.setShortcut(QKeySequence("Ctrl+y"))
        self.simulation_action.setStatusTip("Activar/Desactivar simulación")

        self.sun_icon = QIcon(os.path.join(
            os.path.dirname(__file__), "..", "icons", "sun.png"))
        self.moon_icon = QIcon(os.path.join(
            os.path.dirname(__file__), "..", "icons", "moon.png"))

        self.theme_action = QAction(
            self.sun_icon, "Cambiar tema", self)
        self.theme_action.setShortcut(QKeySequence("Ctrl+l"))
        self.theme_action.setStatusTip("Cambiar tema")

        self.connect_action = QAction("Conectar", self)
        self.connect_action.setEnabled(False)

        # self.com_select_action = QAction()

    def create_menu(self):
        """ Define la estructura del menu y submenus basado en las acciones definidas.
        """
        self.create_actions()
        self.menu_bar = QMenuBar()
        self.menu_bar.setFixedHeight(32)
        self.menu_bar.setContentsMargins(0, 0, 0, 0)
        self.menu_bar.adjustSize()

        # Logo en la equina izquierda
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

        # Menús normales
        self.vista_menu = self.menu_bar.addMenu("&Vista")
        self.vista_menu.addAction(self.camera_action)
        self.vista_menu.addAction(self.model_action)

        self.mode_menu = self.menu_bar.addMenu("&Modo")
        # Grupo exclusivo para seleccionar el modo
        self.mode_group = QActionGroup(self)
        self.mode_group.setExclusive(True)

        self.angular_action.setCheckable(True)
        self.cartesian_action.setCheckable(True)
        # Por defecto seleccionamos 'Angular'
        self.angular_action.setChecked(True)

        self.mode_group.addAction(self.angular_action)
        self.mode_group.addAction(self.cartesian_action)

        self.mode_menu.addAction(self.angular_action)
        self.mode_menu.addAction(self.cartesian_action)

        # Conectar acciones a handlers que emitirán el cambio de modo
        self.angular_action.triggered.connect(self._set_mode_angular)
        self.cartesian_action.triggered.connect(self._set_mode_cartesian)

        self.simulation_menu = self.menu_bar.addMenu("&Simulación")
        self.simulation_menu.addAction(self.simulation_action)

        self.robot_menu = self.menu_bar.addMenu("&Robot")
        self.com_submenu = self.robot_menu.addMenu("&Puerto")
        self.com_group = QActionGroup(self)
        self.com_group.setExclusive(True)
        self.get_com_ports()
        self.robot_menu.addAction(self.connect_action)

        self.menu_bar.setSizePolicy(
            QSizePolicy(QSizePolicy.Policy.Preferred,
                        QSizePolicy.Policy.Preferred)
        )

    def get_com_ports(self):
        """ Escanea el sistema en busca de puertos de comunicación serial y los expone como un
            submenu para que el usuario seleccione el puerto del microcontrolador del robot
        """
        available_ports = list_ports.comports()

        # limpiar menú y grupo
        self.com_submenu.clear()
        for action in list(self.com_group.actions()):
            self.com_group.removeAction(action)

        if available_ports:
            if self.stopped:
                self.com_submenu.setEnabled(False)
            else:
                self.com_submenu.setEnabled(True)
            # Agrega los puertos seriales disponibles al submenu
            for port in available_ports:
                com_action = self.com_submenu.addAction(port.description)
                com_action.setCheckable(True)
                # Define el dato que se envia con la señal de qt
                com_action.setData(port.device)
                com_action.setStatusTip(f"Conectar al puerto {port.device}")
                self.com_group.addAction(com_action)
                com_action.triggered.connect(self.com_checkable_change)

                if self.com == port.device:
                    com_action.setChecked(True)
        else:
            self.connect_action.setEnabled(False)
            self.com_submenu.setEnabled(False)
            self.com = None
            self._stop_threads()
            self.com_connected_label.setText("No conectado")

    def com_checkable_change(self, checked):
        """ Detecta cuando se selecciona un puerto de comunicación serial COM y en caso de que este
            seleccionado uno previamente detiene la conexión 
            Si el controlador y el hilo de proceso del robot no están inicializados se activa la 
            opción de realizar la conexión con ese puerto.

        Args:
            checked (bool): permite saber si al menos un puerto mostrado en la interfaz esta 
                            seleccionado
        """
        action = self.sender()
        if not self.com:
            self._stop_threads()
        if action and checked:  # Solo cuando queda seleccionado
            self.com = action.data()
            if (not getattr(self, "openbotv", None) and
                not getattr(self, "robot_controller", None) and
                    not self.stopped):
                self.connect_action.setEnabled(True)
        
    def _set_mode_angular(self, checked=False):
        """Handler para seleccionar modo Angular (SLIDERS)"""
        try:
            from data import Modes, PhysicalSignalManager, SimulationSignalManager
            try:
                PhysicalSignalManager.get_instance().change_mode_signal.emit(
                    Modes.SLIDERS)
            except Exception:
                pass
            try:
                SimulationSignalManager.get_instance().change_mode_signal.emit(
                    Modes.SLIDERS)
            except Exception:
                pass
        except Exception:
            pass

    def _set_mode_cartesian(self, checked=False):
        """Handler para seleccionar modo Cartesiano (KINEMATIC)"""
        try:
            from data import Modes, PhysicalSignalManager, SimulationSignalManager
            try:
                PhysicalSignalManager.get_instance().change_mode_signal.emit(
                    Modes.KINEMATIC)
            except Exception:
                pass
            try:
                SimulationSignalManager.get_instance().change_mode_signal.emit(
                    Modes.KINEMATIC)
            except Exception:
                pass
        except Exception:
            pass

    def _stop_threads(self):
        """ Detiene y elimina los hilos activos de forma segura
        """
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
        """ Crea la barra de estado y conecta la visualization del estado de conexión del puerto 
            serial
        """
        status_bar = QStatusBar(self)
        status_bar.addPermanentWidget(self.com_connected_label)
        self.setStatusBar(status_bar)
