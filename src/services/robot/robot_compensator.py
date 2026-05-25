"""
Clase encargada de interceptar y procesar los datos antes de ser enviados al robot.

Proporciona el compensador RobotCompensator que aplica transformaciones
a las posiciones de los servos (por ejemplo, compensacion de backlash)
antes de enviarlas al hardware.
"""


class RobotCompensator:
    """Compensador de datos de posicion para el robot.

    Intercepta las posiciones objetivo y aplica correcciones antes
    del envio serial. Actualmente funciona como paso transparente
    (sin modificaciones).
    """

    def __init__(self):
        """Inicializa el compensador de datos."""
        pass

    def process_data(self, positions: list) -> list:
        """
        Intercepta los datos para realizar compensaciones.

        Por ahora retorna los datos sin cambios. En el futuro aplicara
        correcciones como compensacion de backlash, mapeo no lineal, etc.

        Args:
            positions (list): Lista de posiciones originales (0-300).

        Returns:
            list: Lista de posiciones compensadas.
        """
        compensated_positions = positions.copy()
        return compensated_positions
