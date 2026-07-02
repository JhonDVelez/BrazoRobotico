"""
Módulo que define la clase base de señales del sistema de control.

Las señales PyQt6 habilitan la comunicación asíncrona entre hilos y
componentes separados (UI, worker, simulación, hardware) sin acoplamiento
directo.
"""

from PyQt6.QtCore import pyqtSignal, QObject


class _SignalManager(QObject):
    """
    Gestor centralizado de señales para comunicación entre threads.

    Cada atributo es una señal PyQt6 tipada que transporta listas de
    posiciones articulares, objetos de configuración o notificaciones
    simples a través de los distintos dominios del sistema.

    Signals:
        get_data_signal: Solicita lectura de datos del dispositivo activo.
        sensor_position_signal: Emite posiciones leídas por sensores/realtime.
        model_position_signal: Emite posiciones del modelo cinemático.
        update_robot_signal: Actualiza representación visual 3D del brazo.
        update_graph_signal: Actualiza gráficos de posición vs tiempo.
        update_pybullet_signal: Envía posiciones objetivo a PyBullet.
        update_target_signal: Emite posición destino deseada.
        change_mode_signal: Cambia modo de operación (SLIDERS/KINEMATIC).
    """
    get_data_signal = pyqtSignal()
    sensor_position_signal = pyqtSignal(list)
    model_position_signal = pyqtSignal(list, dict)
    update_robot_signal = pyqtSignal(list)
    update_graph_signal = pyqtSignal(list)
    update_pybullet_signal = pyqtSignal(list)
    update_target_signal = pyqtSignal(list)
    change_mode_signal = pyqtSignal(object)
