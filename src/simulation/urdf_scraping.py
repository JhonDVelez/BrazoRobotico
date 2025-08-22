import pybullet as p
from simulation.pybullet_env import SimulationEnv


class RobotURDF:
    """ Clase que se encarga de la obtencion del modelo a partir del urdf
    """

    def __init__(self, robot_id):
        # super().__init__()
        self.robot_id = robot_id
        self.env = SimulationEnv()
        self.get_initial_state()

    def get_initial_state(self):
        """Obtener el estado inicial del robot"""

        # Número total de cuerpos en la simulación (incluye suelo, robot, etc.)
        total_bodies = p.getNumBodies()
        print(f"Número total de cuerpos en la simulación: {total_bodies}")

        self.num_joints = p.getNumJoints(self.robot_id)
        num_links = self.num_joints + 1  # +1 para el link base
        print(f"Robot tiene {num_links} links (incluyendo link base)")

        dict_all = []   # Diccionario que almacena todos los links
        dict_link = {}  # Diccionario que almacena temporalmente el link
        # Información del link base
        base_info = p.getBodyInfo(self.robot_id)
        base_pos, base_orn = p.getBasePositionAndOrientation(self.robot_id)
        print(f"Link base: {base_info[1].decode('utf-8')}")
        print(f"Link base position: {base_pos}")
        print(f"Link base orientation: {base_orn}")

        # Información de cada joint/link
        for i in range(self.num_joints):
            joint_info = p.getJointInfo(self.robot_id, i)
            joint_name = joint_info[1].decode('utf-8')
            link_name = joint_info[12].decode('utf-8')

            # Obtener posición del link
            link_state = p.getLinkState(self.robot_id, i)

            dict_link = {"link": link_name,
                         "position": link_state[0],
                         "orientation": link_state[1]
                         }
            print(f"Joint {i}: {joint_name} -> Link: {link_name}")
            print(f"  Position: {link_state[0]}")
            print(f"  Orientation: {link_state[1]}")
            print(f"  Frame Position: {link_state[4]}")
            print(f"  Frame Orientation: {link_state[5]}")
            dict_all.append(dict_link)

        return dict_all
