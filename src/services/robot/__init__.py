"""
Paquete de servicios de comunicacion y control del robot.

Proporciona las clases RobotController (interfaz principal),
RobotWorker (comunicacion serial) y RobotCompensator
(procesamiento de datos de salida).

Señales:
    - RobotWorker.data_received: Emitida al recibir telemetria valida
      desde la placa OpenCM9.04.
    - PhysicalSignalManager.is_connected: Estado de la conexion serial.
    - PhysicalSignalManager.data_received: Datos de telemetria recibidos.
"""

from .robot_controller import RobotController

__all__ = ['RobotController']
