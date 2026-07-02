"""
Módulo de gestión centralizada de notificaciones.

Proporciona NotificationManager, un singleton que unifica la presentación
de mensajes al usuario mediante ToastLabels transitorios o QMessageBox
modales, segun el NotificationType especificado.
"""

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox

from src.services.data.enums.types import NotificationType

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QWidget


class NotificationManager:
    """
    Gestor centralizado de notificaciones de interfaz.

    Ruta notificaciones a ToastLabel o QMessageBox según NotificationType.
    Mantiene referencia a la ventana principal para posicionar toasts.

    Example:
        manager = NotificationManager.get_instance()
        manager.set_main_window(self)

        # Toast transitorio
        manager.notify("Camara iniciada", NotificationType.TOAST_SUCCESS)

        # Diálogo modal
        manager.notify("Desea continuar?", NotificationType.DIALOG_QUESTION)
    """

    _instance = None
    _main_window: "QWidget | None" = None

    # Estilos de toast por tipo
    _TOAST_STYLES = {
        NotificationType.TOAST_INFO: ("#2b2b2b", "white"),
        NotificationType.TOAST_SUCCESS: ("#1b5e20", "white"),
        NotificationType.TOAST_WARNING: ("#f57c00", "white"),
        NotificationType.TOAST_ERROR: ("#b71c1c", "white"),
    }

    def __init__(self):
        if NotificationManager._instance is not None:
            raise RuntimeError(
                "NotificationManager es un singleton. "
                "Use get_instance() en lugar de instanciar directamente."
            )
        self._toast_label = None

    @staticmethod
    def get_instance() -> "NotificationManager":
        """Retorna la instancia única del gestor."""
        if NotificationManager._instance is None:
            NotificationManager._instance = NotificationManager()
        return NotificationManager._instance

    def set_main_window(self, window: "QWidget") -> None:
        """Establece la referencia a la ventana principal."""
        self._main_window = window

    def notify(
        self,
        message: str,
        notification_type: NotificationType,
        parent: "QWidget | None" = None,
        duration: int = 4000,
    ) -> QMessageBox.StandardButton | None:
        """
        Muestra una notificación según el tipo especificado.

        Args:
            message: Texto a mostrar.
            notification_type: Determina el estilo de presentación.
            parent: Widget padre opcional. Usa ventana principal si es None.
            duration: Tiempo de visualización en ms para toasts.

        Returns:
            Para DIALOG_QUESTION: QMessageBox.StandardButton pulsado.
            Para otros tipos: None.
        """
        effective_parent = parent if parent is not None else self._main_window
        print(message)
        if notification_type in self._TOAST_STYLES:
            return self._show_toast(message, notification_type, effective_parent, duration)
        return self._show_dialog(message, notification_type, effective_parent)

    def _show_toast(
        self,
        message: str,
        notification_type: NotificationType,
        parent: "QWidget",
        duration: int,
    ) -> None:
        """Muestra un toast con estilo según el tipo."""
        from src.services.ui.toast_label import ToastLabel

        if self._toast_label is None or self._toast_label.parent() != parent:
            self._toast_label = ToastLabel(parent)

        bg_color, text_color = self._TOAST_STYLES[notification_type]
        self._toast_label.setStyleSheet(
            f"background-color: {bg_color}; "
            f"color: {text_color}; "
            "padding: 10px 20px; "
            "border-radius: 5px;"
        )
        self._toast_label.show_message(message, duration)

    def _show_dialog(
        self,
        message: str,
        notification_type: NotificationType,
        parent: "QWidget",
    ) -> QMessageBox.StandardButton | None:
        """Muestra un QMessageBox según el tipo."""
        dialog_mapping = {
            NotificationType.DIALOG_INFO: (
                QMessageBox.Icon.Information,
                QMessageBox.StandardButton.Ok,
            ),
            NotificationType.DIALOG_WARNING: (
                QMessageBox.Icon.Warning,
                QMessageBox.StandardButton.Ok,
            ),
            NotificationType.DIALOG_ERROR: (
                QMessageBox.Icon.Critical,
                QMessageBox.StandardButton.Ok,
            ),
            NotificationType.DIALOG_QUESTION: (
                QMessageBox.Icon.Question,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            ),
        }

        icon, buttons = dialog_mapping[notification_type]

        msg_box = QMessageBox(parent)
        msg_box.setIcon(icon)
        msg_box.setText(message)
        msg_box.setStandardButtons(buttons)
        msg_box.setWindowModality(Qt.WindowModality.ApplicationModal)

        return msg_box.exec()
