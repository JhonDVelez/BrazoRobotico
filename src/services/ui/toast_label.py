"""
Modulo de notificaciones emergentes (toast) para la interfaz.

Proporciona ToastLabel, un QLabel personalizado que muestra mensajes
temporales con animacion de fundido (fade in/out) en la parte inferior
de la ventana.
"""

from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QSize
from PyQt6.QtWidgets import QLabel, QGraphicsOpacityEffect
from PyQt6.QtGui import QPixmap


class ToastLabel(QLabel):
    """Etiqueta emergente temporal con animacion de fundido.

    Muestra mensajes en la parte inferior de la ventana padre con
    una animacion de entrada (fade in), una pausa configurable y
    una animacion de salida (fade out).

    Args:
        parent (QWidget, optional): Widget padre.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ToastLabel")

        self.setGraphicsEffect(QGraphicsOpacityEffect(self))
        self.opacity = self.graphicsEffect()

        self.anim = QPropertyAnimation(self.opacity, b"opacity")
        self.anim.setDuration(300)

        self.fading_out = False

        self.anim.finished.connect(self.on_animation_finished)

        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.fade_out)

        self.hide()

    def show_message(self, text, duration=2000):
        """Muestra un mensaje con animacion de fundido.

        Detiene cualquier animacion previa, posiciona el mensaje
        centrado en la parte inferior de la ventana padre e inicia
        la animacion de entrada.

        Args:
            text (str): Texto del mensaje a mostrar.
            duration (int, optional): Duracion en ms antes de
                iniciar el fundido de salida. Por defecto 2000.
        """
        self.timer.stop()
        self.anim.stop()

        self.setText(text)
        self.adjustSize()

        if self.parent():
            parent_rect = self.parent().rect()
            self.move(
                (parent_rect.width() - self.width()) // 2,
                parent_rect.height() - self.height() - 20
            )

        self.fading_out = False

        self.show()
        self.raise_()

        self.anim.setStartValue(0)
        self.anim.setEndValue(1)
        self.anim.start()

        self.timer.start(duration)

    def fade_out(self):
        """Inicia la animacion de fundido de salida."""
        self.anim.stop()

        self.fading_out = True

        self.anim.setStartValue(1)
        self.anim.setEndValue(0)
        self.anim.start()

    def on_animation_finished(self):
        """Oculta la etiqueta al finalizar la animacion de salida."""
        if self.fading_out:
            self.hide()
