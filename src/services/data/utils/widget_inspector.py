"""Runtime widget size inspector. Ctrl+click any widget to print its size info."""

from PyQt6.QtCore import QObject, QEvent, Qt
from PyQt6.QtWidgets import QApplication, QToolTip


class WidgetInspector(QObject):
    """Event filter that reports widget sizes on Ctrl+click."""

    def eventFilter(self, obj, event):
        if (event.type() == QEvent.Type.MouseButtonPress
                and event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            w = QApplication.widgetAt(event.globalPosition().toPoint())
            if w:
                info = (
                    f"─── {w.objectName() or type(w).__name__} ───\n"
                    f"  minimumSize:     {w.minimumSize().width()}×{w.minimumSize().height()}\n"
                    f"  minimumSizeHint: {w.minimumSizeHint().width()}×{w.minimumSizeHint().height()}\n"
                    f"  sizeHint:        {w.sizeHint().width()}×{w.sizeHint().height()}\n"
                    f"  current size:    {w.width()}×{w.height()}\n"
                    f"  maximumSize:     {w.maximumSize().width()}×{w.maximumSize().height()}\n"
                    f"  sizePolicy:      H={w.sizePolicy().horizontalPolicy().name} "
                    f"V={w.sizePolicy().verticalPolicy().name}"
                )
                print(info)
                QToolTip.showText(
                    event.globalPosition().toPoint(),
                    info.replace(" ", "").replace("───", "—"),
                    w
                )
            return True
        return super().eventFilter(obj, event)

    @staticmethod
    def install(app: QApplication):
        """Call once after QApplication is created."""
        inspector = WidgetInspector(app)
        app.installEventFilter(inspector)
