import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal

class SlidersWorker(QObject):
    """
    Worker encargado de la gestión de datos de los sliders.
    Maneja el estado interno de los ángulos de los motores y las transformaciones.
    """
    status_changed = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        # Estado inicial (150 es el centro para el robot, 0 para la interfaz)
        self._sliders_status = [150] * 6

    # --- API de Datos (Getters / Setters) ---

    def set_sliders_state(self, values: list):
        """ Establece el estado completo de los sliders """
        if len(values) == 6:
            self._sliders_status = list(values)
            self.status_changed.emit(self._sliders_status)

    def get_sliders_state(self) -> list:
        """ Retorna el estado actual de los sliders """
        return list(self._sliders_status)

    def update_single_value(self, index: int, value: int):
        """ Actualiza un valor individual del buffer """
        if 0 <= index < 6:
            self._sliders_status[index] = value
            self.status_changed.emit(self._sliders_status)

    def reset_to_defaults(self):
        """ Reinicia todos los valores al centro (150) """
        self.set_sliders_state([150] * 6)
