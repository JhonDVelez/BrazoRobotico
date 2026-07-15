"""
Módulo que gestiona el estado lógico de los controles deslizantes (sliders).

Este módulo define la clase SlidersWorker, la cual mantiene el vector de estado
de los 6 motores del robot cuando se opera en modo manual, gestionando la
sincronización de ángulos entre la UI y el resto del sistema.

Los valores están en espacio angular (ángulos del usuario), no en espacio
absoluto del servo (0-300).
"""

from PyQt6.QtCore import QObject, pyqtSignal


class SlidersWorker(QObject):
    """
    Worker encargado de la gestión de datos de los sliders.

    Maneja el estado interno de los ángulos de los motores y actúa como la
    fuente de verdad para el modo de control manual.

    Attributes:
        status_changed (pyqtSignal): Emite la lista completa de 6 ángulos (int)
            cada vez que hay un cambio en el estado.
    """
    status_changed = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self._sliders_status = [0] * 6

    def set_sliders_state(self, values: list):
        if len(values) == 6:
            self._sliders_status = list(values)
            self.status_changed.emit(self._sliders_status)

    def get_sliders_state(self) -> list:
        return list(self._sliders_status)

    def update_single_value(self, index: int, value: int):
        if 0 <= index < 6:
            self._sliders_status[index] = value
            self.status_changed.emit(self._sliders_status)

    def reset_to_defaults(self):
        self.set_sliders_state([0] * 6)
