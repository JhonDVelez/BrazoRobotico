from PyQt6.QtCore import QObject, pyqtSignal
from src.features.sliders.sliders_widget import SlidersWidget
from src.features.sliders.sliders_worker import SlidersWorker
from src.services.data.enums import Modes
from src.services.data.signals import PhysicalSignalManager, SimulationSignalManager

class SlidersController(QObject):
    """
    Orquestador del feature de controles deslizantes.
    Coordina la interacción entre la UI y el estado de los ángulos del robot.
    """
    # Estado compartido para compatibilidad con servicios de datos (Legacy support)
    sliders_status = [150, 150, 150, 150, 150, 150]

    def __init__(self, parent=None):
        super().__init__()
        self._widget = SlidersWidget(parent)
        self._worker = SlidersWorker()
        
        self.__setup_connections()

    def __setup_connections(self):
        # Widget -> Controlador
        self._widget.value_changed.connect(self._on_ui_value_changed)
        
        # Worker -> Estado Compartido
        self._worker.status_changed.connect(self._update_shared_status)

    def _on_ui_value_changed(self, index, value):
        # Cambiar modo global a SLIDERS al interactuar
        PhysicalSignalManager.get_instance().change_mode_signal.emit(Modes.SLIDERS)
        SimulationSignalManager.get_instance().change_mode_signal.emit(Modes.SLIDERS)
        
        # Actualizar worker
        self._worker.update_single_value(index, value)

    def _update_shared_status(self, status):
        """ Actualiza el buffer estático y notifica al sistema de forma reactiva """
        SlidersController.sliders_status = status
        # Notificar al DataFlow de forma reactiva
        PhysicalSignalManager.get_instance().update_target_signal.emit(status)
        SimulationSignalManager.get_instance().update_target_signal.emit(status)


    # --- API Pública ---

    def get_widget(self) -> SlidersWidget:
        return self._widget

    def reset_controls(self):
        self._worker.reset_to_defaults()
        self._widget.reset_ui()

    @classmethod
    def get_sliders_state(cls) -> list:
        """ API estática requerida por DataFlow """
        return cls.sliders_status

    def set_external_values(self, values: list):
        """ Actualiza los sliders desde una fuente externa (ej. telemetría) """
        self._worker.set_sliders_state(values)
        self._widget.set_values(values)
