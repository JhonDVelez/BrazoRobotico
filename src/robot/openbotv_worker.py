import serial
from PyQt6.QtCore import QThread, QTimer
from data import PhysicalSignalManager


class RobotWorker(QThread):
    """ Hilo de trabajo para el envió y recepción de datos del openbotv v1 físico
    """

    def __init__(self, com: str):
        super().__init__()
        self.CM904 = serial.Serial(com, 9600, timeout=2)
        self.signal_manager = PhysicalSignalManager.get_instance()

        # Conectar señal de interfaz → slot local
        self.signal_manager.send_to_robot.connect(self.get_data_from_interface)

    def run(self):
        """ Inicia el ciclo de solicitud de datos a la interfaz y el envió de datos al robot
        """
        # Crear un timer dentro del hilo
        self.timer = QTimer()
        self.timer.timeout.connect(self.request_data)
        self.timer.start(20)  # cada 20 ms → 50 Hz
        # Necesario para que el QTimer funcione dentro del QThread
        self.exec()

    def request_data(self):
        """ Solicita datos a la interfaz dependiendo del modo activado
        """
        # print("[DEBUG] Emitiendo get_data_signal")
        self.signal_manager.get_data_signal.emit()

    def send_data_to_robot(self, valorm):
        """ Envía datos al robot con el formato definido con valores de entre 0 y 1023

        Args:
            valorm (list): ángulos objetivo del robot.
        """
        if all(0 <= x <= 300 for x in valorm):
            self.comandos = [
                f"A{round(valorm[0]*(1023/300))}\n",
                f"B{round(valorm[1]*(1023/300))}\n",
                f"C{round(valorm[2]*(1023/300))}\n",
                f"D{round(valorm[3]*(1023/300))}\n",
                f"E{round(valorm[4]*(1023/300))}\n",
                f"F{round(valorm[5]*(1023/300))}\n",
            ]
            self._enviar_comando(0)  # empezar desde el primero
        else:
            print("Error de envío de datos: Valores fuera de rango")

    def _enviar_comando(self, index):
        """ Envío de comando uno a uno al microcontrolador, esta función hace uso de recursividad.

        Args:
            index (int): Posición actual del comando a enviar
        """
        if index < len(self.comandos):
            self.CM904.write(self.comandos[index].encode())
            # espera 5 ms y luego llama al siguiente
            QTimer.singleShot(5, lambda: self._enviar_comando(index + 1))

    def get_data_from_interface(self, datos):
        """ Datos obtenidos de la interfaz, recibidos mediante la señal 'send_to_robot'

        Args:
            datos (list): Ángulos objetivos proporcionados por la interfaz.
        """
        # print(f"[RobotWorker] Recibido desde interfaz: {datos}")
        self.send_data_to_robot(datos)

    def stop(self):
        """ Detiene el envío de datos al robot.
        """
        if hasattr(self, "timer"):
            self.timer.stop()
        self.quit()
        self.wait()
