"""
Módulo que define la barra de título personalizada de la aplicación.

Integra la barra de menú, el título del programa y los botones de control
de ventana (minimizar, maximizar, cerrar) en una interfaz sin bordes
(frameless) basada en qframelesswindow.
"""

from PyQt6.QtWidgets import QHBoxLayout, QWidget, QToolButton, QLabel, QSizePolicy
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont, QPainter, QPixmap
from qframelesswindow import TitleBarBase
from src.services.data.signals import ThemeSignalManager


class MainTitleBarMixin(TitleBarBase):
    """
    Barra de título personalizada para ventanas frameless.

    Organiza el menú a la izquierda, el título centrado y los botones
    de ventana (min/max/close) y tema a la derecha, con balanceo
    automático de anchos laterales.
    """

    def __init__(self, parent, title="OpenBotV Control Lab"):
        """
        Inicializa la barra de título con el layout y controles de ventana.

        Args:
            parent (QWidget): Ventana padre.
            title (str): Título a mostrar centrado.
        """
        super().__init__(parent)
        self.parent_class = parent
        self._theme_signal = ThemeSignalManager.get_instance()
        # self._theme_signal.theme_changed.connect(self._on_theme_changed)

        self.title_layout = QHBoxLayout(self)
        self.title_layout.setContentsMargins(0, 0, 0, 0)
        self.title_layout.setSpacing(0)

        # Contenedor izquierdo con el menu
        self.left_container = QWidget()
        self.left_layout = QHBoxLayout(self.left_container)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_layout.setSpacing(0)

        self.left_layout.addWidget(self.parent_class.menu_bar)

        # Label central con el titulo
        self.title_label = QLabel(title)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        font = QFont()
        font.setPointSize(8)
        self.title_label.setFont(font)

        # Controles a la derecha
        self._create_window_buttons()

        # Políticas de tamaño
        self.left_container.setSizePolicy(
            QSizePolicy.Policy.Minimum,
            QSizePolicy.Policy.Fixed
        )
        self.buttons_frame.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed
        )
        self.title_label.setSizePolicy(
            QSizePolicy.Policy.Minimum,
            QSizePolicy.Policy.Expanding
        )

        self.title_layout.addWidget(self.left_container, 0)
        self.title_layout.addStretch(1)
        self.title_layout.addWidget(self.title_label, 0)
        self.title_layout.addStretch(1)
        self.title_layout.addWidget(self.buttons_frame, 0)

        QTimer.singleShot(0, self.balance_containers)

        self.title_label.setObjectName("title_label")
        self.left_container.setObjectName("left_container")
        self.buttons_frame.setObjectName("buttons_frame")
        self.minBtn.setObjectName("title_bar_min_btn")
        self.maxBtn.setObjectName("title_bar_max_btn")
        self.closeBtn.setObjectName("title_bar_close_btn")

    def _create_window_buttons(self):
        """
        Crea el contenedor de botones de control de ventana y tema.
        """
        self.buttons_frame = QWidget()
        self.buttons_frame.setFixedHeight(32)

        controls_layout = QHBoxLayout(self.buttons_frame)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(0)
        controls_layout.addStretch(1)

        theme_button = QToolButton()
        if hasattr(self.parent_class, 'theme_action'):
            theme_button.setDefaultAction(
                self.parent_class.theme_action)
        theme_button.setAutoRaise(True)
        theme_button.setFixedSize(24, 24)
        controls_layout.addWidget(theme_button)

        controls_layout.addWidget(self.minBtn)
        controls_layout.addWidget(self.maxBtn)
        controls_layout.addWidget(self.closeBtn)

    def balance_containers(self):
        """
        Equilibra el ancho de los contenedores laterales.

        Fuerza la actualización de geometría y agenda el balanceo fino
        para el siguiente ciclo del event loop.
        """
        self.left_container.updateGeometry()

        QTimer.singleShot(0, self._balance_widths)

    def _balance_widths(self):
        """
        Ajusta los anchos mínimos de contenedores izquierdo y derecho
        para que tengan el mismo tamaño y el título quede centrado.
        """
        left_width = self.left_container.sizeHint().width()
        buttons_width = self.buttons_frame.width()

        max_width = max(left_width, buttons_width)
        self.left_container.setMinimumWidth(max_width)
        self.buttons_frame.setMinimumWidth(max_width)

    def resizeEvent(self, event):
        """
        Re-equilibra los contenedores laterales en cada redimensionamiento.

        Args:
            event (QResizeEvent): Evento de redimensionamiento.
        """
        super().resizeEvent(event)
        QTimer.singleShot(0, self._balance_widths)
