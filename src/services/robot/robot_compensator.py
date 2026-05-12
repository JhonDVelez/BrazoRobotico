"""
Clase encargada de interceptar y procesar los datos antes de ser enviados al robot.
"""


class RobotCompensator:
    def __init__(self):
        """ Inicializa el compensador de datos """
        pass

    def process_data(self, positions: list) -> list:
        """ 
        Intercepta los datos para realizar compensaciones.
        Por ahora retorna los datos sin cambios.

        Args:
            positions (list): Lista de posiciones originales (0-300)

        Returns:
            list: Lista de posiciones compensadas
        """
        # Aquí se interceptará el envío de datos en el futuro
        compensated_positions = positions.copy()

        return compensated_positions
