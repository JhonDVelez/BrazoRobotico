from PyQt6.QtCore import pyqtSignal, QObject


class _SignalManager(QObject):
    """ Gestor centralizado de señales para comunicación entre threads
    """
    get_data_signal = pyqtSignal()
    sensor_position_signal = pyqtSignal(list)
    model_position_signal = pyqtSignal(list)
    update_robot_signal = pyqtSignal(list)
    update_graph_signal = pyqtSignal(list)
    update_pybullet_signal = pyqtSignal(list)
    update_target_signal = pyqtSignal(list)
    change_mode_signal = pyqtSignal(object)