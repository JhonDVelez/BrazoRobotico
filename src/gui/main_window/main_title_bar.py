import sys
import ctypes
from ctypes import wintypes

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QToolButton, QStyle
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtCore import QSize, Qt


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long)]


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class MainTitleBar:
    def setup_custom_titlebar(self):
        """Agregar barra de título personalizada manteniendo la estructura original"""

        # Configurar ventana sin marco
        # self.setWindowFlags(
        #     Qt.WindowType.FramelessWindowHint |
        #     Qt.WindowType.WindowMinimizeButtonHint |
        #     Qt.WindowType.WindowSystemMenuHint
        # )
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setMinimumSize(400, 300)
        

        # CRÍTICO: Obtener el widget central Y su layout antes de modificar
        original_central = self.centralWidget()
        original_layout = original_central.layout() if original_central else None

        # Crear nuevo widget principal
        new_central = QWidget()
        self.setCentralWidget(new_central)

        # Layout principal vertical
        main_layout = QVBoxLayout(new_central)
        main_layout.setContentsMargins(1, 1, 1, 1)
        main_layout.setSpacing(0)

        # Crear y agregar barra de título personalizada
        self.custom_title_bar = CustomTitleBar(self)
        main_layout.addWidget(self.custom_title_bar)

        # Reubicar menubar si existe ANTES del contenido
        if self.menuBar() and self.menuBar().actions():
            menubar = self.menuBar()
            menubar.setParent(new_central)
            main_layout.addWidget(menubar)

        # CORRECCIÓN CLAVE: Mantener el widget original intacto
        if original_central:
            # No cambiar el parent directamente, crear un contenedor
            content_widget = QWidget()
            content_layout = QVBoxLayout(content_widget)
            content_layout.setContentsMargins(0, 0, 0, 0)

            # Si el widget original tenía layout, transferirlo
            if original_layout:
                # Transferir todos los widgets del layout original
                while original_layout.count():
                    item = original_layout.takeAt(0)
                    if item.widget():
                        content_layout.addWidget(item.widget())
                    elif item.layout():
                        content_layout.addLayout(item.layout())
            else:
                # Si no tenía layout, agregar el widget directamente
                content_layout.addWidget(original_central)

            main_layout.addWidget(content_widget)

        # Reubicar statusbar si existe
        if self.statusBar():
            statusbar = self.statusBar()
            statusbar.setParent(new_central)
            main_layout.addWidget(statusbar)

        # Configurar ventana
        self.setMinimumSize(400, 400)
        self.resize(1280, 720)

        # Estilo básico
        self.setStyleSheet("""
            QMainWindow {
                border: 1px solid #555;
                background-color: #2b2b2b;
            }
        """)


class CustomTitleBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setAutoFillBackground(True)
        self.setFixedHeight(40)

        # Variables para arrastre
        self.drag_start_position = None

        # Layout principal
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 5, 5)
        layout.setSpacing(5)

        # Título (área arrastrable)
        self.title = QLabel(
            "OpenBotv v1 - Universidad Distrital Francisco José de Caldas", self)
        self.title.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.title)

        # Espaciador
        layout.addStretch()

        # Botones de control
        self.create_control_buttons(layout)

    def create_control_buttons(self, layout):
        """Crear botones de control de ventana"""
        # Botón minimizar
        self.min_button = QToolButton(self)
        self.min_button.setText("─")
        self.min_button.setFixedSize(QSize(30, 28))
        self.min_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.min_button.clicked.connect(self.window().showMinimized)

        # Botón maximizar
        self.max_button = QToolButton(self)
        self.max_button.setText("□")
        self.max_button.setFixedSize(QSize(30, 28))
        self.max_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.max_button.clicked.connect(self.window().showMaximized)

        # Botón restaurar (inicialmente oculto)
        self.normal_button = QToolButton(self)
        self.normal_button.setText("❐")
        self.normal_button.setFixedSize(QSize(30, 28))
        self.normal_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.normal_button.clicked.connect(self.window().showNormal)
        self.normal_button.setVisible(False)

        # Botón cerrar
        self.close_button = QToolButton(self)
        self.close_button.setText("✕")
        self.close_button.setFixedSize(QSize(30, 28))
        self.close_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.close_button.setObjectName("close_button")
        self.close_button.clicked.connect(self.window().close)

        # Agregar botones al layout
        layout.addWidget(self.min_button)
        layout.addWidget(self.normal_button)
        layout.addWidget(self.max_button)
        layout.addWidget(self.close_button)

    def window_state_changed(self, state):
        """Cambiar visibilidad de botones según estado de ventana"""
        if state == Qt.WindowState.WindowMaximized:
            self.normal_button.setVisible(True)
            self.max_button.setVisible(False)
        else:
            self.normal_button.setVisible(False)
            self.max_button.setVisible(True)

    def mousePressEvent(self, event: QMouseEvent):
        """Iniciar arrastre de ventana"""
        if event.button() == Qt.MouseButton.LeftButton and not self.window().isMaximized():
            self.drag_start_position = event.globalPosition(
            ).toPoint() - self.window().frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """Arrastrar ventana"""
        if (event.buttons() == Qt.MouseButton.LeftButton and
            self.drag_start_position is not None and
                not self.window().isMaximized()):

            new_pos = event.globalPosition().toPoint() - self.drag_start_position
            self.window().move(new_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Terminar arrastre"""
        self.drag_start_position = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Maximizar/restaurar con doble clic"""
        if event.button() == Qt.MouseButton.LeftButton:
            if self.window().isMaximized():
                self.window().showNormal()
            else:
                self.window().showMaximized()
        super().mouseDoubleClickEvent(event)
