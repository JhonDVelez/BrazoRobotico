"""
Modulo que define el widget de visualizacion de la simulacion 3D.

Este modulo contiene la clase SimulationWidget, la cual integra una vista
de QtQuick (QML) dentro de un widget de PyQt6, permitiendo mostrar tanto una
imagen estatica de placeholder como el modelo 3D interactivo.

Conexiones:
    - Emite `theme_needed` para solicitar ajustes de color en la escena 3D.
    - Utiliza `ImageHandler` para gestionar los iconos de carga y placeholders.
"""

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtQuick import QQuickView
from PyQt6.QtWidgets import QVBoxLayout, QLabel, QSizePolicy, QWidget
from src.services.ui.image_handler import ImageHandler


class SimulationWidget(QWidget):
    """
    Widget encargado de la interfaz de visualizacion del robot 3D.

    Gestiona el contenedor de ventana (`windowContainer`) necesario para incrustar
    contenido QML/Quick3D en un entorno de widgets estandares, facilitando el
    intercambio visual entre la simulacion activa y el estado de reposo.

    Attributes:
        theme_needed (pyqtSignal): Emite True si se requiere aplicar un tema oscuro.
    """
    theme_needed = pyqtSignal(bool)

    def __init__(self, preloaded_container, pybullet_callback):
        """
        Inicializa el widget utilizando recursos previamente cargados.

        Args:
            preloaded_container (PreloadedContainer): Objeto con la vista y contenedor pre-listos.
            pybullet_callback (callable): Funcion a ejecutar tras la integracion visual exitosa.
        """
        super().__init__()
        self.preloaded_container = preloaded_container
        self.pybullet_callback = pybullet_callback
        self._root_object = None

        if preloaded_container and preloaded_container.is_ready:
            self.quick_view = preloaded_container.quick_view
            self.window_container = preloaded_container.window_container
        else:
            print("Warning: No hay contenedor precargado disponible")

        self.process_running = False

        # Configurar layout principal
        if not self.layout():
            self.v_layout = QVBoxLayout(self)
            self.v_layout.setContentsMargins(0, 0, 0, 0)
            self.setLayout(self.v_layout)

        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)
        self.setMinimumSize(160, 120)

        # Configurar imagen estática (Placeholder)
        self.__setup_static_image()

        # Integrar contenedor pre-cargado en la jerarquia de widgets
        self.__integrate_preloaded_container()

    def __setup_static_image(self):
        """
        Configura la etiqueta de imagen que se muestra cuando la simulacion esta apagada.
        """
        self.image_path_l = "img:robotArm_l.svg"
        self.image_path_d = "img:robotArm_d.svg"
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.image_label.setMinimumSize(160, 120)
        self.layout().addWidget(self.image_label)

        self.image_handler = ImageHandler(
            self.image_label, self.image_path_d, self.image_path_l
        )
        self.image_handler.set_static_image()

    def __integrate_preloaded_container(self):
        """
        Realiza la integracion tecnica de la ventana QQuickView en el widget de PyQt.
        """
        try:
            if not self.quick_view:
                print("Error: No hay vista precargada")
                return

            self.window_container = QWidget.createWindowContainer(
                self.quick_view,
                self,
                Qt.WindowType.Widget
            )

            self.window_container.setParent(self)

            # Configurar políticas de tamaño para que ocupe todo el espacio
            self.window_container.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Expanding
            )
            self.window_container.setMinimumSize(160, 120)

            # Agregar al layout de la interfaz
            self.layout().addWidget(self.window_container)

            # Ocultar inicialmente para mostrar el placeholder
            self.window_container.hide()

            # Configurar flags de la vista Quick3D
            if self.quick_view:
                self.quick_view.setFlags(
                    Qt.WindowType.Widget | Qt.WindowType.FramelessWindowHint
                )
                self.quick_view.setResizeMode(
                    QQuickView.ResizeMode.SizeRootObjectToView)
            else:
                print("Error de configuracion de vista")

            # Inicializar comunicacion con el objeto raiz QML
            self._root_object = self.quick_view.rootObject()
            if self._root_object:
                self.pybullet_callback(self._root_object)
            else:
                print("Error de inicializacion del worker")

        except Exception as e:
            print(f"Error integrando contenedor precargado: {e}")

    def get_simulation_widget(self):
        """
        Retorna la instancia del widget (self) para compatibilidad de API.

        Returns:
            SimulationWidget: Esta instancia.
        """
        return self

    def image_show(self):
        """Muestra la imagen estatica de placeholder."""
        self.image_label.show()

    def image_hide(self):
        """Oculta la imagen estatica de placeholder."""
        self.image_label.hide()

    def container_show(self):
        """Muestra el contenedor de la ventana 3D."""
        self.window_container.show()

    def container_hide(self):
        """Oculta el contenedor de la ventana 3D."""
        self.window_container.hide()

    def quick_show(self):
        """Hace visible la vista de Quick3D."""
        self.quick_view.show()

    def quick_hide(self):
        """Oculta la vista de Quick3D."""
        self.quick_view.hide()

    def quick_update(self):
        """Fuerza una actualizacion de renderizado en la vista 3D."""
        self.quick_view.update()

    def change_theme(self, dark_t: bool):
        """
        Actualiza el tema visual del widget y la escena 3D.

        Args:
            dark_t (bool): True para tema oscuro.
        """
        self.image_handler.update_theme(dark_t)
        self.theme_needed.emit(dark_t)
