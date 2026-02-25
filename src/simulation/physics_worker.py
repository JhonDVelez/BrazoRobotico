from PyQt6.QtCore import QThread, QTimer, pyqtSignal, pyqtSlot
from data import SimulationSignalManager
from .physics_pybullet import RobotArmPhysics


class PhysicsWorker(QThread):
    """ Worker encargado de gestionar el hilo de ejecución para actualizar la simulación de PyBullet.
        Se encarga de la lógica de control, temporización y sincronización con la interfaz.
    """

    # Señal para notificar cambios en el modelo (usada para sincronizar la vista 3D)
    update_model = pyqtSignal(list)

    def __init__(self, robot_id) -> None:
        super().__init__()
        # Almacena la última posición objetivo para evitar cálculos innecesarios si no hay cambios
        self.target_position_prev = [1, 0, 0, 0, 0, 0]
        self.model_ogl = None
        self.physic = None
        self.timer = None
        # Banderas de estado para el control del hilo
        self._running = False
        self._paused = False
        self.max_velocity = None
        
        # Obtiene la instancia del gestor de señales para comunicación entre componentes
        self.signal_manager = SimulationSignalManager.get_instance()
        # Conecta la señal de actualización proveniente de la interfaz con el slot local
        self.signal_manager.update_pybullet_signal.connect(
            self.update_simulation)

        # Inicializa el motor de física y carga el robot mediante su ID único
        self.physic = RobotArmPhysics()
        self.physic.robot_loaded.connect(self.get_data)
        self.physic.load_models(robot_id)

    def set_max_velocity(self, max_vel):
        """ Define la velocidad máxima de los motores en la simulación.

        Args:
            max_vel (float): velocidad máxima en radianes por segundo.
        """
        if max_vel > 0:
            self.max_velocity = max_vel
        else:
            # Fallback de seguridad en caso de ingresar un valor inválido
            print("La velocidad maxima debe ser mayor a 0, "
                  "usando la velocidad maxima por defecto: 1 rad/s")
            self.max_velocity = 1.2

    def run(self):
        """ Ciclo principal del subproceso. Se ejecuta al llamar a .start().
            Configura los parámetros iniciales y lanza la primera petición de datos.
        """
        self._running = True
        self.set_max_velocity(5.55) # Configura una velocidad de operación
        
        # Gestión de reanudación si el hilo estaba en pausa
        if self._paused:
            self._paused = False

        # Inicia la cadena de eventos solicitando el estado inicial de la interfaz
        self.get_data()

    def pause(self):
        """ Detiene temporalmente el procesamiento de la simulación. """
        self._running = False
        self._paused = True

    def stop(self):
        """ Detiene la simulación y reinicia el robot a su estado original. """
        self.physic.reset_simulation()
        self._running = False
        self._paused = False

    def get_data(self):
        """ Emite una señal que solicita datos de posición de los motores a la interfaz.
            Este es el 'disparador' que mantiene el bucle de actualización vivo.
        """
        self.signal_manager.get_data_signal.emit()

    @pyqtSlot(list)
    def update_simulation(self, target_positions):
        """ Procesa los nuevos ángulos objetivo y ejecuta un paso de simulación física.
            Incluye lógica de compensación de offset y optimización de cómputo.
        """
        # Aplica un offset constante para alinear el sistema de coordenadas de la UI con el de PyBullet
        target_positions = [
            pos - 2.6179938779914944 for pos in target_positions]
            
        if self._running:
            # Verifica que el paquete de datos sea íntegro respecto al número de motores
            if len(target_positions) == len(self.physic.joint_indices):
                # Obtiene posiciones reales actuales desde el motor de física
                actual_positions = self.physic.get_joint_positions()
                # Reporta la posición actual al gestor de señales (para gráficas y telemetría)
                self.signal_manager.actual_position_signal.emit(
                    actual_positions)
                
                # OPTIMIZACIÓN: Solo envía nuevos comandos al motor si la posición objetivo cambió
                if not all(x == y for x, y in zip(target_positions, self.target_position_prev)):
                    self.physic.set_joint_positions(
                        target_positions, self.max_velocity)
                    self.target_position_prev = target_positions
                
                # UMBRAL DE MOVIMIENTO: Solo ejecuta el paso de simulación si hay una diferencia 
                # significativa (0.01 rad) entre donde está el robot y donde debería estar.
                # Esto ahorra recursos de CPU cuando el robot está estático o ya llegó a su meta.
                if any(abs(x - y) >= 0.01 for x, y in zip(target_positions, actual_positions)):
                    self.physic.step_simulation()
                
                # Programa la siguiente actualización en 16ms (aprox. 60 FPS)
                # Crea un bucle recursivo asíncrono que no bloquea el hilo
                QTimer.singleShot(16, self.get_data)