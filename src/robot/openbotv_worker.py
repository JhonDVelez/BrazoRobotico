from calendar import c

import serial
import re
from PyQt6.QtCore import QThread, QTimer
from data import PhysicalSignalManager, GlobalTimer


class RobotSerial:
    _instance = None
    cm904 = None

    @classmethod
    def get_instance(cls, com: str):
        """ Permite obtener una única instancia del objeto evitando que se generen multiples señales
            de comunicación. En caso de que no haya ninguna instancia entonces se crea una nueva.

        Returns:
            PhysicalSignalManager: instancia única de la clase
        """
        if cls._instance is None:
            cls._instance = cls()
            cls.cm904 = serial.Serial(com, 9600, timeout=1)
        return cls._instance


class RobotWriterWorker(QThread):
    """ Hilo de trabajo para el envió y recepción de datos del openbotv v1 físico
    """

    def __init__(self, com: str):
        super().__init__()
        robot_serial = RobotSerial.get_instance(com)
        self.cm904 = robot_serial.cm904

        self.signal_manager = PhysicalSignalManager.get_instance()
        # Conectar señal de interfaz → slot local
        self.signal_manager.send_to_robot.connect(self.send_data_to_robot)
        self.signal_manager.is_connected = True

        self.sync_timer = GlobalTimer.get_instance()
        self.sync_timer.data_request_signal.connect(self.send_data_to_robot)
        self._running = True

    def run(self):
        """ Inicia el ciclo de solicitud de datos a la interfaz y el envió de datos al robot
        """
        # Crear un timer dentro del hilo
        # self.timer = QTimer()
        # self.timer.timeout.connect(self.request_data)
        # self.timer.start(20)  # cada 20 ms → 50 Hz
        # # Necesario para que el QTimer funcione dentro del QThread
        # self.exec()

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
        
        while self._running:
            try:
                if self.cm904.in_waiting > 0:
                    line = self.cm904.readline().decode('ascii', errors='ignore').strip()

                    if not line or ";" not in line:
                        continue

                    posiciones = [None] * 6
                    temperaturas = [None] * 6

                    for i, char in enumerate(['A', 'B', 'C', 'D', 'E', 'F']):
                        pos_match = re.search(rf"{char}(\d+)", line)
                        temp_match = re.search(rf"T{char}(\d+)", line)
                        if pos_match:
                            posiciones[i] = float(pos_match.group(1))
                        if temp_match:
                            temperaturas[i] = int(temp_match.group(1))

                    # Envía la señal para que inicie la solicitud de datos a pybullet
                    self.sync_timer.sync_tick.emit()
                    # Envía datos a las gráficas
                    self.signal_manager.data_received.emit(
                        posiciones, temperaturas)

            except Exception as e:
                print(f"{e}")
                break
            

    def _enviar_comando(self, index):
        """ Envío de comando uno a uno al microcontrolador, esta función hace uso de recursividad.

        Args:
            index (int): Posición actual del comando a enviar
        """
        if index < len(self.comandos):
            self.cm904.write(self.comandos[index].encode())
            # espera 5 ms y luego llama al siguiente
            QTimer.singleShot(5, lambda: self._enviar_comando(index + 1))

    def stop(self):
        """ Detiene el envío de datos al robot.
        """
        # if hasattr(self, "timer"):
        #     self.timer.stop()
        self._running = False
        self.cm904.close()
        self.signal_manager.is_connected = False
        self.quit()
        self.wait()


class RobotReaderWorker(QThread):

    def __init__(self, com: str):
        super().__init__()
        robot_serial = RobotSerial.get_instance(com)
        self.cm904 = robot_serial.cm904

        self.signal_manager = PhysicalSignalManager.get_instance()
        self.signal_manager.is_connected = True

        self.sync_timer = GlobalTimer.get_instance()
        self._running = True

    def run(self):
        """Equivalente al serial_reader_thread original"""
        while self._running:
            try:
                if self.cm904.in_waiting > 0:
                    line = self.cm904.readline().decode('ascii', errors='ignore').strip()

                    if not line or ";" not in line:
                        continue

                    posiciones = [None] * 6
                    temperaturas = [None] * 6

                    for i, char in enumerate(['A', 'B', 'C', 'D', 'E', 'F']):
                        pos_match = re.search(rf"{char}(\d+)", line)
                        temp_match = re.search(rf"T{char}(\d+)", line)
                        if pos_match:
                            posiciones[i] = float(pos_match.group(1))
                        if temp_match:
                            temperaturas[i] = int(temp_match.group(1))

                    # Envía la señal para que inicie la solicitud de datos a pybullet
                    self.sync_timer.sync_tick.emit()
                    # Envía datos a las gráficas
                    self.signal_manager.data_received.emit(
                        posiciones, temperaturas)

            except Exception as e:
                print(f"{e}")

    def stop(self):
        self._running = False
        self.cm904.close()
        self.signal_manager.is_connected = False
        self.wait()  # Espera a que el hilo termine limpiamente
