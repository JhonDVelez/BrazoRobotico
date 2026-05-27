"""
Modulo que orquesta el control manual del robot mediante sliders.

Este modulo define la clase SlidersController, la cual enlaza la interaccion
del usuario con los hilos de procesamiento y notifica al sistema los cambios
de posicion angular deseados.

Conexiones:
    - Escucha cambios de valor en `SlidersWidget`.
    - Actualiza el estado global de control a `Modes.SLIDERS`.
    - Sincroniza el `SlidersWorker` y emite señales de actualizacion de objetivo.
"""

from PyQt6.QtCore import QObject
from src.features.sliders.sliders_widget import SlidersWidget
from src.features.sliders.sliders_worker import SlidersWorker
from src.services.data.enums import Modes
from src.services.data.signals import SimulationSignalManager


class SlidersController(QObject):
    """
    Controlador para el modulo de sliders manuales.

    Coordina la interaccion entre la interfaz de usuario y el estado de los angulos
    del robot, asegurando que los comandos manuales tengan prioridad sobre otros
    modos cuando el usuario interactua con ellos.

    Attributes:
        sliders_status (list): Estado compartido de los 6 motores.
    """
    # Estado compartido para compatibilidad con servicios de datos reactivos
    sliders_status = [150, 150, 150, 150, 150, 150]

    def __init__(self, parent=None):
        """
        Inicializa el controlador de sliders y sus componentes.

        Args:
            parent (QWidget, optional): Widget padre para la UI.
        """
        super().__init__()
        self._widget = SlidersWidget(parent)
        self._worker = SlidersWorker()
        
        self.__setup_connections()

    def __setup_connections(self):
        """
        Configura las conexiones de señales entre el widget, el worker y el sistema.
        """
        # Widget -> Controlador (Accion del usuario en la UI)
        self._widget.value_changed.connect(self._on_ui_value_changed)
        
        # Worker -> Estado Compartido (Actualizacion logica terminada)
        self._worker.status_changed.connect(self._update_shared_status)

    def _on_ui_value_changed(self, index, value):
        """
        Maneja el cambio de posicion solicitado desde la interfaz.

        Cambia el modo de operacion global a SLIDERS para habilitar el control manual.

        Args:
            index (int): Indice del motor modificado (0-5).
            value (int): Nuevo valor de angulo (0-300).
        """
        # Cambiar modo global a SLIDERS mediante el manager de simulación (actúa como bus de UI)
        SimulationSignalManager.get_instance().change_mode_signal.emit(Modes.SLIDERS)
        
        # Actualizar el buffer interno del worker
        self._worker.update_single_value(index, value)

    def _update_shared_status(self, status):
        """
        Actualiza el buffer estatico y notifica al sistema de forma reactiva.

        Args:
            status (list): Vector completo de posiciones articulares.
        """
        SlidersController.sliders_status = status
        # Notificar el nuevo objetivo al bus global. El DataController orquestará el resto.
        SimulationSignalManager.get_instance().update_target_signal.emit(status)

    # --- API Pública ---

    def get_widget(self) -> SlidersWidget:
        """
        Retorna la vista de sliders asociada.

        Returns:
            SlidersWidget: Instancia del widget.
        """
        return self._widget

    def reset_controls(self):
        """
        Reinicia todos los controles y el estado logico a la posicion central.
        """
        self._worker.reset_to_defaults()
        self._widget.reset_ui()

    @classmethod
    def get_sliders_state(cls) -> list:
        """
        API estática para obtener el estado actual de los sliders.

        Returns:
            list: Posiciones actuales.
        """
        return cls.sliders_status

    def set_external_values(self, values: list):
        """
        Actualiza los sliders desde una fuente externa (e.g. sincronizacion de cinematica).

        Args:
            values (list): Nuevos valores a cargar en la UI y el worker.
        """
        self._worker.set_sliders_state(values)
        self._widget.set_values(values)

