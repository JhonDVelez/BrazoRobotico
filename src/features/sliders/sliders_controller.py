"""
Módulo que orquesta el control manual del robot mediante sliders.

Este módulo define la clase SlidersController, la cual enlaza la interacción
del usuario con los hilos de procesamiento y notifica al sistema los cambios
de posición angular deseados.

Conexiones:
    - Escucha cambios de valor en `SlidersWidget`.
    - Actualiza el estado global de control a `Modes.SLIDERS`.
    - Sincroniza el `SlidersWorker` y emite señales de actualización de objetivo.
"""

from PyQt6.QtCore import QObject
from src.features.sliders.sliders_widget import SlidersWidget
from src.features.sliders.sliders_worker import SlidersWorker
from src.services.data.enums import Modes
from src.services.data.signals import SlidersSignalManager


class SlidersController(QObject):
    """
    Controlador para el módulo de sliders manuales.

    Coordina la interacción entre la interfaz de usuario y el estado de los ángulos
    del robot, asegurando que los comandos manuales tengan prioridad sobre otros
    modos cuando el usuario interactua con ellos.

    El estado articular vigente lo mantiene el DataController (fuente de verdad
    única); este controlador solo publica intención en su bus propio.
    """

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
        # Widget -> Controlador (Acción del usuario en la UI)
        self._widget.value_changed.connect(self._on_ui_value_changed)
        
        # Worker -> Estado Compartido (Actualización lógica terminada)
        self._worker.status_changed.connect(self._update_shared_status)

    def _on_ui_value_changed(self, index, value):
        """
        Maneja el cambio de posición solicitado desde la interfaz.

        Cambia el modo de operación global a SLIDERS para habilitar el control manual.

        Args:
            index (int): Indice del motor modificado (0-5).
            value (int): Nuevo valor de angulo (0-300).
        """
        # Cambiar modo global a SLIDERS mediante el bus propio de la feature.
        # El DataController escucha y orquesta el resto del sistema.
        SlidersSignalManager.get_instance().change_mode_signal.emit(Modes.SLIDERS)
        
        # Actualizar el buffer interno del worker
        self._worker.update_single_value(index, value)

    def _update_shared_status(self, status):
        """
        Notifica al sistema el nuevo objetivo de forma reactiva.

        Args:
            status (list): Vector completo de posiciones articulares.
        """
        # Notificar el nuevo objetivo al bus propio. El DataController orquestará el resto.
        SlidersSignalManager.get_instance().update_target_signal.emit(status)

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
        Reinicia todos los controles y el estado lógico a la posición central.
        """
        self._worker.reset_to_defaults()
        self._widget.reset_ui()

    def set_external_values(self, values: list):
        """
        Actualiza los sliders desde una fuente externa (e.g. sincronización de cinemática).

        Args:
            values (list): Nuevos valores a cargar en la UI y el worker.
        """
        self._worker.set_sliders_state(values)
        self._widget.set_values(values)

