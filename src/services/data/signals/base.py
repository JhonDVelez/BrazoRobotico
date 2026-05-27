"""
Modulo que define la clase base de señales del sistema de control.

Las senales PyQt6 habilitan la comunicacion asincrona entre hilos y
componentes separados (UI, worker, simulacion, hardware) sin acoplamiento
directo.
"""

from PyQt6.QtCore import pyqtSignal, QObject


class _SignalManager(QObject):
    """
    Gestor centralizado de senales para comunicacion entre threads.

    Cada atributo es una senal PyQt6 tipada que transporta listas de
    posiciones articulares, objetos de configuracion o notificaciones
    simples a traves de los distintos dominios del sistema.

    Signals:
        get_data_signal: Solicita lectura de datos del dispositivo activo.
        sensor_position_signal: Emite posiciones leidas por sensores/realtime.
        model_position_signal: Emite posiciones del modelo cinematico.
        update_robot_signal: Actualiza representacion visual 3D del brazo.
        update_graph_signal: Actualiza graficos de posicion vs tiempo.
        update_pybullet_signal: Envia posiciones objetivo a PyBullet.
        update_target_signal: Emite posicion destino deseada.
        change_mode_signal: Cambia modo de operacion (SLIDERS/KINEMATIC).
    """
    get_data_signal = pyqtSignal()
    sensor_position_signal = pyqtSignal(list)
    model_position_signal = pyqtSignal(list, dict)
    update_robot_signal = pyqtSignal(list)
    update_graph_signal = pyqtSignal(list)
    update_pybullet_signal = pyqtSignal(list)
    update_target_signal = pyqtSignal(list)
    change_mode_signal = pyqtSignal(object)
