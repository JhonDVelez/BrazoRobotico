""" Modulo donde se gestiona el comportamiento de los pixmap (imágenes) presentes en la interfaz 
    cuando algún proceso no esa en funcionamiento, o cuando es detenido por el usuario, por ejemplo
    al iniciar la interfaz se muestra un brazo, una cámara y unas gráficas estas imágenes son
    son gestionadas aquí asi como su comportamiento frente al cambio de tamaño de ventana y el tema.
"""
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QSize
from PyQt6.QtWidgets import QLabel, QGraphicsOpacityEffect
from PyQt6.QtGui import QPixmap


class ToastLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ToastLabel")

        self.setGraphicsEffect(QGraphicsOpacityEffect(self))
        self.opacity = self.graphicsEffect()

        self.anim = QPropertyAnimation(self.opacity, b"opacity")
        self.anim.setDuration(300)

        # 🔥 bandera para saber qué animación está corriendo
        self.fading_out = False

        # ✅ conectar UNA sola vez
        self.anim.finished.connect(self.on_animation_finished)

        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.fade_out)

        self.hide()

    def show_message(self, text, duration=2000):
        self.timer.stop()          # 🔥 importante
        self.anim.stop()           # 🔥 importante

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

        # Fade in
        self.anim.setStartValue(0)
        self.anim.setEndValue(1)
        self.anim.start()

        self.timer.start(duration)

    def fade_out(self):
        self.anim.stop()

        self.fading_out = True

        self.anim.setStartValue(1)
        self.anim.setEndValue(0)
        self.anim.start()

    def on_animation_finished(self):
        if self.fading_out:
            self.hide()
