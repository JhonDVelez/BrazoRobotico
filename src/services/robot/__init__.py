"""
Paquete de servicios de comunicación y control del robot.

Proporciona las clases RobotController (interfaz principal),
RobotWorker (comunicación serial) y RobotCompensator
(procesamiento de datos de salida).

Señales:
    - RobotWorker.data_received: Emitida al recibir telemetría válida
      desde la placa OpenCM9.04.
    - PhysicalSignalManager.is_connected: Estado de la conexión serial.
    - PhysicalSignalManager.data_received: Datos de telemetría recibidos.
"""

from .robot_controller import RobotController

__all__ = ['RobotController']
