import pybullet as p


class SimulationEnv:
    """ Clase para manejar una unica instancia de pybullet y evitar la generacion de multiples 
    simulaciones innecesarias

    Returns:
        SimulationEnv: retorna la instancia de esta clase
    """
    _instance = None

    def __new__(cls):
        # Singleton: garantiza que solo se cree una vez
        if cls._instance is None:
            cls._instance = super(SimulationEnv, cls).__new__(cls)
            cls._instance.cid = p.connect(p.DIRECT)
        return cls._instance

    def reset(self):
        """ Reinicia la simulacion de pybullet
        """
        p.resetSimulation()
        p.setGravity(0, 0, -9.8)

    def step(self):
        """ Ejecuta un paso en la simulacion permite definir la frecuencia de actualizacion
        """
        p.stepSimulation()

    def disconnect(self):
        """ Desconecta el cliente de pybullet deteninendo la simulacion
        """
        p.disconnect()
