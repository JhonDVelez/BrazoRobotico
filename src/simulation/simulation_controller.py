from simulation.physics_worker import PhysicsWorker
from simulation.urdf_scraping import RobotURDF


class SimController:
    """ Clase que actua como controlador de la simulacion facilitando la instanciacion de las clases
    """

    def __init__(self, sim_interface):
        self.sim_interface = sim_interface
        self.worker = PhysicsWorker(self)
        self.urdf = RobotURDF(self.worker.get_robot_id())
        initial_states = self.urdf.get_initial_state()
        self.worker.set_max_velocity(1.2)

    def start_simulation(self):
        """ Da inicio a la ejecucion de la simulacion o la vuelve a poner en curso si fue pausada
        """
        self.worker.start()

    def stop_simulation(self):
        """ Detiene el ciclo de procesamiento del hilo pausando la ejecucion de la simulacion
        """
        self.worker.stop()
        self.worker.exit()
