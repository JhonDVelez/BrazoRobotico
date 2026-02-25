import serial
import re
import time
from PyQt6.QtCore import QThread
from data import PhysicalSignalManager

class RobotWorker(QThread):
    """ Hilo de trabajo dedicado a la comunicación serial y llenado de telemetría. """

    def __init__(self, com: str, telemetry_dict: dict):
        super().__init__()
        # Guardamos solo la configuración. NO abrimos el puerto aquí.
        self.com_port = com
        self.telemetry = telemetry_dict 
        self.CM904 = None
        
        # Acceso al gestor de señales
        self.signal_manager = PhysicalSignalManager.get_instance()
        self.signal_manager.send_to_robot.connect(self.get_data_from_interface)
        
        self.running_telemetry = True

    def run(self):
        """ Bucle principal del hilo. Se ejecuta en el hilo secundario. """
        # Intentamos abrir el puerto serie dentro del contexto del hilo secundario
        try:
            self.CM904 = serial.Serial(self.com_port, 9600, timeout=1)
            print(f"Conexión exitosa en {self.com_port}")
        except Exception as e:
            print(f"Error crítico al abrir puerto {self.com_port}: {e}")
            self.CM904 = None
            return # Finaliza el hilo si no hay acceso

        while self.running_telemetry:
            # 1. Pedir datos a la interfaz
            self.signal_manager.get_data_signal.emit()

            # 2. Leer telemetría
            try:
                if self.CM904.in_waiting > 0:
                    line = self.CM904.readline().decode('ascii', errors='ignore').strip()
                    if ";" in line:
                        self._procesar_linea_telemetria(line)
            except Exception as e:
                print(f"Error de lectura serial: {e}")
                break # Sale del bucle si se pierde la conexión física

            # 3. Control de frecuencia
            self.msleep(20) 

        # Al salir del bucle while, aseguramos la limpieza
        self._limpiar_recursos()

    def _procesar_linea_telemetria(self, line):
        """ Extrae datos y actualiza la bolsa de telemetría de forma segura. """
        posiciones = [0]*6
        temperaturas = [0]*6
        
        with self.telemetry['lock']:
            for i, char in enumerate(['A', 'B', 'C', 'D', 'E', 'F']):
                pos_match = re.search(rf"{char}(\d+)", line)
                temp_match = re.search(rf"T{char}(\d+)", line)
                
                if pos_match:
                    val_pos = int(pos_match.group(1))
                    posiciones[i] = val_pos
                    self.telemetry['history_pos'][i].append(val_pos)
                
                if temp_match:
                    val_temp = int(temp_match.group(1))
                    temperaturas[i] = val_temp
                    self.telemetry['history_temp'][i].append(val_temp)

                if len(self.telemetry['history_pos'][i]) > 100:
                    self.telemetry['history_pos'][i].pop(0)
                    self.telemetry['history_temp'][i].pop(0)

        self.signal_manager.telemetry_updated.emit(posiciones, temperaturas)

    def send_data_to_robot(self, valorm):
        """ Envía comandos al robot si el puerto está disponible. """
        if not self.CM904 or not self.CM904.is_open:
            return

        if all(0 <= x <= 300 for x in valorm):
            # Mapeo de 0-300 grados a 0-1023 (Protocolo Dynamixel/CM904)
            self.comandos = [f"{c}{round(v*(1023/300))}\n" for c, v in zip('ABCDEF', valorm)]
            self._enviar_comando_secuencial(0) 

    def _enviar_comando_secuencial(self, index):
        if index < len(self.comandos):
            try:
                self.CM904.write(self.comandos[index].encode())
                time.sleep(0.005) 
                self._enviar_comando_secuencial(index + 1)
            except:
                pass

    def get_data_from_interface(self, datos):
        self.send_data_to_robot(datos)

    def _limpiar_recursos(self):
        """ Libera el puerto serie. """
        if self.CM904 and self.CM904.is_open:
            self.CM904.close()
            print(f"Puerto {self.com_port} liberado correctamente.")

    def stop(self):
        """ Detiene el hilo de forma segura. """
        self.running_telemetry = False
        self.quit()
        self.wait()