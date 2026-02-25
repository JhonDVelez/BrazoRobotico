""" Este modulo Se encarga de la estructura y comportamiento de la barra de titulo donde se 
    integra el menu, el titulo del programa y los botones de control de ventana.
"""
from PyQt6.QtWidgets import QHBoxLayout, QWidget, QToolButton, QLabel, QSizePolicy
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont
from qframelesswindow import TitleBarBase


class MainTitleBarMixin(TitleBarBase):
    """ Barra de titulo personalizada basada en qframelesswindow.
        Permite un diseño "sin bordes" (frameless) donde los controles de la ventana
        se integran directamente en el diseño de la aplicación.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.parent_class = parent

        # Crear layout base horizontal para organizar los elementos de la barra
        self.title_layout = QHBoxLayout(self)
        self.title_layout.setContentsMargins(0, 0, 0, 0)
        self.title_layout.setSpacing(0)

        # === CONTENEDOR IZQUIERDO ===
        # Alberga el menú principal (Vista, Modo, Simulación, etc.)
        self.left_container = QWidget()
        self.left_layout = QHBoxLayout(self.left_container)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_layout.setSpacing(0)

        # Inserción del menu_bar definido en MainMenuMixin
        self.left_layout.addWidget(self.parent_class.menu_bar)

        # === LABEL CENTRAL ===
        # Texto identificador de la aplicación posicionado en el centro
        self.title_label = QLabel(
            "OpenBotV Control Lab")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Configuración estética de la fuente del título
        font = QFont()
        font.setPointSize(8)
        self.title_label.setFont(font)

        # Inicialización de los botones de control (Minimizar, Maximizar, Cerrar)
        self._create_window_buttons()

        # === CONFIGURAR POLÍTICAS DE TAMAÑO ===
        # El contenedor izquierdo ocupa el espacio mínimo necesario para el menú
        self.left_container.setSizePolicy(
            QSizePolicy.Policy.Minimum,
            QSizePolicy.Policy.Fixed
        )
        # El frame de botones (derecha) tiene un tamaño fijo y no se expande
        self.buttons_frame.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed
        )
        # El label del título se expande para llenar el espacio sobrante y centrarse
        self.title_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        # Agregación de los componentes al layout principal de la barra
        self.title_layout.addWidget(self.left_container)
        self.title_layout.addWidget(self.title_label, 1) # Factor de estiramiento 1
        self.title_layout.addWidget(self.buttons_frame)

        # Uso de un Timer de disparo único para equilibrar la interfaz tras el renderizado inicial
        QTimer.singleShot(0, self.balance_containers)

    def _create_window_buttons(self):
        """ Crea el contenedor derecho que incluye los botones de control de ventana
            y el acceso rápido al cambio de tema.
        """
        self.buttons_frame = QWidget()
        self.buttons_frame.setFixedHeight(32)

        controls_layout = QHBoxLayout(self.buttons_frame)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(0)
        controls_layout.addStretch(1) # Empuja los botones hacia la derecha absoluta

        # Botón de acceso rápido para alternar entre tema Claro y Oscuro
        theme_button = QToolButton()
        theme_button.setDefaultAction(
            self.parent_class.theme_action) 
        theme_button.setAutoRaise(True)  # Elimina el borde del botón para un look limpio
        theme_button.setFixedSize(24, 24)
        controls_layout.addWidget(theme_button)

        # Integración de los botones nativos de qframelesswindow
        controls_layout.addWidget(self.minBtn)
        controls_layout.addWidget(self.maxBtn)
        controls_layout.addWidget(self.closeBtn)

    def balance_containers(self):
        """ Fuerza la actualización de la geometría para equilibrar los anchos laterales.
        """
        self.left_container.updateGeometry()

        # Se ejecuta en el siguiente ciclo de eventos para asegurar que los anchos sean calculados
        QTimer.singleShot(0, self._balance_widths)

    def _balance_widths(self):
        """ Calcula el ancho del contenedor izquierdo para intentar mantener la simetría 
            del título central respecto a los botones de la derecha.
        """
        left_width = self.left_container.sizeHint().width()

        # Establece un ancho mínimo basado en el contenido real del menú
        self.left_container.setMinimumWidth(left_width)

    def resizeEvent(self, event):
        """ Evento disparado al cambiar el tamaño de la ventana. 
            Asegura que el título permanezca centrado dinámicamente.
        """
        super().resizeEvent(event)
        # Recalcula los equilibrios de ancho en cada redimensionamiento
        QTimer.singleShot(0, self._balance_widths)

    def set_title(self, title):
        """ Método público para actualizar dinámicamente el nombre mostrado en la barra.
        """
        self.title_label.setText(title)