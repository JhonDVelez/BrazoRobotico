""" Este modulo Se encarga de la estructura y comportamiento de la barra de titulo donde se 
    integra el menu, el titulo del programa y los botones de control de ventana.
"""
from PyQt6.QtWidgets import QHBoxLayout, QWidget, QToolButton, QLabel, QSizePolicy, QToolBar
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont
from qframelesswindow import TitleBarBase


class MainTitleBarMixin(TitleBarBase):
    """ Barra de titulo personalizada basado qframelesswindow
    """

    def __init__(self, parent, title="OpenBotV Control Lab"):
        super().__init__(parent)
        self.parent_class = parent

        # crear layout base para la barra
        self.title_layout = QHBoxLayout(self)
        self.title_layout.setContentsMargins(0, 0, 0, 0)
        self.title_layout.setSpacing(0)

        # === CONTENEDOR IZQUIERDO ===
        self.left_container = QWidget()
        self.left_layout = QHBoxLayout(self.left_container)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_layout.setSpacing(0)

        # menú a la izquierda
        self.left_layout.addWidget(self.parent_class.menu_bar)

        # === LABEL CENTRAL ===
        self.title_label = QLabel(
            title)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Configurar fuente del título
        font = QFont()
        font.setPointSize(8)
        self.title_label.setFont(font)

        # Controles a la derecha
        self._create_window_buttons()

        # === CONFIGURAR POLÍTICAS DE TAMAÑO ===
        self.left_container.setSizePolicy(
            QSizePolicy.Policy.Minimum,
            QSizePolicy.Policy.Fixed
        )
        self.buttons_frame.setSizePolicy(
            QSizePolicy.Policy.Fixed,  # Cambiar de Minimum a Fixed
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

        # Equilibrar contenedores después de la inicialización
        QTimer.singleShot(0, self.balance_containers)

        self.title_label.setObjectName("title_label")
        self.left_container.setObjectName("left_container")
        self.buttons_frame.setObjectName("buttons_frame")
        self.minBtn.setObjectName("title_bar_min_btn")
        self.maxBtn.setObjectName("title_bar_max_btn")
        self.closeBtn.setObjectName("title_bar_close_btn")

    def _create_window_buttons(self):
        self.buttons_frame = QWidget()
        self.buttons_frame.setFixedHeight(32)

        controls_layout = QHBoxLayout(self.buttons_frame)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(0)
        controls_layout.addStretch(1)

        theme_button = QToolButton()
        if hasattr(self.parent_class, 'theme_action'):
            theme_button.setDefaultAction(
                self.parent_class.theme_action)  # tu QAction aquí
        theme_button.setAutoRaise(True)  # estilo plano
        theme_button.setFixedSize(24, 24)
        controls_layout.addWidget(theme_button)

        # usar los botones propios de TitleBarBase
        controls_layout.addWidget(self.minBtn)
        controls_layout.addWidget(self.maxBtn)
        controls_layout.addWidget(self.closeBtn)

    def balance_containers(self):
        """ Equilibra el ancho de los contenedores laterales
        """
        # Forzar actualización de tamaños
        self.left_container.updateGeometry()

        # Usar timer para equilibrar después del resize
        QTimer.singleShot(0, self._balance_widths)

    def _balance_widths(self):
        """ Equilibra los anchos de los contenedores laterales
        """
        left_width = self.left_container.sizeHint().width()
        buttons_width = self.buttons_frame.width()

        # Hacer que ambos contenedores tengan el mismo ancho
        max_width = max(left_width, buttons_width)
        self.left_container.setMinimumWidth(max_width)
        self.buttons_frame.setMinimumWidth(max_width)

    def resizeEvent(self, event):
        """ Re-equilibrar en cada resize
        """
        super().resizeEvent(event)
        QTimer.singleShot(0, self._balance_widths)
