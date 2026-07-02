"""
Módulo que gestiona el estado lógico de los controles deslizantes (sliders).

Este módulo define la clase SlidersWorker, la cual mantiene el vector de estado
de los 6 motores del robot cuando se opera en modo manual, gestionando la
sincronización de ángulos entre la UI y el resto del sistema.
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
        """
        Inicializa el worker con los motores en su posición neutral (150 grados).
        """
        super().__init__()
        # Estado inicial (150 es el centro físico para los servos AX-12/MX-28)
        self._sliders_status = [150] * 6

    # --- API de Datos (Getters / Setters) ---

    def set_sliders_state(self, values: list):
        """
        Establece el estado completo de todos los motores.

        Args:
            values (list): Lista de 6 enteros (0-300).
        """
        if len(values) == 6:
            self._sliders_status = list(values)
            self.status_changed.emit(self._sliders_status)

    def get_sliders_state(self) -> list:
        """
        Retorna una copia del estado actual de los motores.

        Returns:
            list: Lista de 6 ángulos.
        """
        return list(self._sliders_status)

    def update_single_value(self, index: int, value: int):
        """
        Actualiza el ángulo de un motor específico.

        Args:
            index (int): Indice del motor (0-5).
            value (int): Nuevo valor de ángulo.
        """
        if 0 <= index < 6:
            self._sliders_status[index] = value
            self.status_changed.emit(self._sliders_status)

    def reset_to_defaults(self):
        """
        Reinicia todos los motores a su posición central de reposo (150).
        """
        self.set_sliders_state([150] * 6)
