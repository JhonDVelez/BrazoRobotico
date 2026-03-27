"""módulo de cálculo de cinemática inversa y realimentada.

   La clase KinematicsWorker implementa la misma lógica que el script
   `Codigos_test/CinematicaV2.py`: se recibe telemetría de posiciones de
   los servos (señal `PhysicalSignalManager.data_received`), se calcula la
   pose real mediante las matrices de transformación y se aplica un algoritmo
   de mínimos cuadrados amortiguados para generar incrementos de ángulo.  Los
   comandos resultantes se emiten a través de `commands_ready` y son consumidos
   por `DataFlow` para enviarlos al robot físico.

"""
import numpy as np
from PyQt6.QtCore import QThread


class KinematicsWorker(QThread):
    # señal para notificar nuevos comandos calculados en modo cinemático realimentado
    from PyQt6.QtCore import pyqtSignal
    commands_ready = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        # dimensiones de los eslabones (mm)
        self.L1, self.L2, self.L3, self.L4 = 155, 92, 111, 155

        # estado de los servos (grados tal y como los entrega el micro)
        self.current_positions = [150.0] * 6
        # objetivo cartesiano en mm (columna 3x1)
        self.target_pos = None
        # para detección de bloqueo / timeout
        self._start_time = None
        self._prev_positions = list(self.current_positions)

        # obtener gestor de señales físicas para leer telemetría
        from data import PhysicalSignalManager
        self.signal_manager = PhysicalSignalManager.get_instance()
        # conectar recepción de datos del robot al método de actualización
        self.signal_manager.data_received.connect(self.update_sensor_data)

    def h_dh(self, H):
        R = H[:3, :3]
        vect_d = H[:3, 3].reshape((3, 1))
        return R, vect_d, np.array([0, 0, 0]), 1

    def hrx(self, theta):
        c, s = np.cos(theta), np.sin(theta)
        return np.array([[1, 0, 0, 0], [0, c, -s, 0], [0, s, c, 0], [0, 0, 0, 1]])

    def hrz(self, theta):
        c, s = np.cos(theta), np.sin(theta)
        return np.array([[c, -s, 0, 0], [s, c, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])

    def htx(self, d):
        return np.array([[1, 0, 0, d], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])

    def htz(self, d):
        return np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, d], [0, 0, 0, 1]])

    def t_matrices(self, t1, t2, t3, t4, L1, L2, L3, L4):
        A1 = self.hrz(
            t1 + np.pi) @ self.htz(L1) @ self.htx(0) @ self.hrx(np.pi/2)
        A2 = self.hrz(t2 + np.pi/2) @ self.htz(0) @ self.htx(L2) @ self.hrx(0)
        A3 = self.hrz(t3) @ self.htz(0) @ self.htx(L3) @ self.hrx(0)
        A4 = self.hrz(t4) @ self.htz(0) @ self.htx(L4) @ self.hrx(0)
        T01 = A1
        T02 = T01 @ A2
        T03 = T02 @ A3
        T04 = T03 @ A4
        return [np.identity(4), T01, T02, T03, T04]

    def cd(self, t1, t2, t3, t4, L1, L2, L3, L4):
        T_list = self.t_matrices(t1, t2, t3, t4, L1, L2, L3, L4)
        _, P, _, _ = self.h_dh(T_list[-1])
        return P

    def jacobiano_analitico(self, q_flat, L1, L2, L3, L4):
        t1, t2, t3, t4 = q_flat
        T_list = self.t_matrices(t1, t2, t3, t4, L1, L2, L3, L4)
        Pn = T_list[-1][:3, 3].reshape((3, 1))
        Jv = np.zeros((3, 4))
        for j in range(4):
            T_prev = T_list[j]
            P_prev = T_prev[:3, 3].reshape((3, 1))
            Z_prev = T_prev[:3, 2].reshape((3, 1))
            vector_d = Pn - P_prev
            Jv[:, j] = np.cross(Z_prev.flatten(), vector_d.flatten())
        return Jv

    def ci(self, px, py, pz, phi):
        # algoritmo de cálculo de la solución cinemática inversa utilizado originalmente
        # en la versión de prueba de Codigos_test/CinematicaV2.py. Esta función se sigue
        # utilizando para generar una estimación inicial cuando la realimentación no
        # está activada.
        q_limit = np.pi/2
        q_min, q_max = -q_limit, q_limit
        q = np.deg2rad(np.array([40, 60, 90, phi],
                       dtype=float)).reshape((4, 1))
        lambda_val, tol, max_iter = 0.5, 0.1, 100
        P_deseada = np.array([[px], [py], [pz]])
        for k in range(max_iter):
            P_actual = self.cd(q[0, 0], q[1, 0], q[2, 0],
                               q[3, 0], self.L1, self.L2, self.L3, self.L4)
            error = P_deseada - P_actual
            if np.linalg.norm(error) < tol:
                break
            J = self.jacobiano_analitico(
                q.flatten(), self.L1, self.L2, self.L3, self.L4)
            q = q + lambda_val * (np.linalg.pinv(J) @ error)
            q = np.clip(q, q_min, q_max)
        return q, error

    # ----------------------------------------------------------
    # Métodos nuevos para cinemática realimentada con el robot
    # ----------------------------------------------------------
    def set_target(self, px, py, pz):
        """Define el objetivo cartesiano hacia el cual debe converger
           el algoritmo de realimentación. Si se le pasa None se desactiva
           la realimentación.
        """
        if px is None or py is None or pz is None:
            self.target_pos = None
        else:
            self.target_pos = np.array([[px], [py], [pz]])
            # reiniciar marcadores de tiempo / posiciones para detección de bloqueo
            import time
            self._start_time = time.time()
            self._prev_positions = list(self.current_positions)
            # forzar cálculo inmediato con la última telemetría disponible
            self.update_sensor_data(self.current_positions)

    def update_sensor_data(self, positions, temps=None):
        """Slot conectado a PhysicalSignalManager.data_received. Cada vez que
           el microcontrolador envía una traza de posiciones se recalcula el
           siguiente comando en caso de haber un objetivo definido.

           "positions" son ángulos en grados conforme los entrega el robot
           (0..300) para los seis ejes.
        """
        # almacenar última muestra
        self.current_positions = list(positions)
        if self.target_pos is None:
            return

        # comprobar condición de bloqueo similar al script original
        import time
        if self._start_time is not None:
            if time.time() - self._start_time > 1.0:
                mov = sum(abs(self.current_positions[i] - self._prev_positions[i])
                          for i in [0, 1, 2, 4])
                if mov < 0.1:
                    print("¡Movimiento bloqueado! Abortando secuencia.")
                    self.target_pos = None
                    return
        # actualizar marcas para detección de bloqueo
        self._prev_positions = list(self.current_positions)

        # construir q_actual 4x1 con el convenio utilizado en CinematicaV2
        r_deg = self.current_positions
        q_actual = np.array([
            np.deg2rad(r_deg[0] - 150.0),
            np.deg2rad(150.0 - r_deg[1]),
            np.deg2rad(150.0 - r_deg[2]),
            np.deg2rad(r_deg[4] - 150.0),
        ]).reshape((4, 1))

        # posición real en mm
        P_real = self.cd(q_actual[0, 0], q_actual[1, 0], q_actual[2, 0],
                         q_actual[3, 0], self.L1, self.L2, self.L3, self.L4)
        dist = np.linalg.norm(self.target_pos - P_real)
        if dist < 4.0:
            # objetivo alcanzado: limpiar target y emitir último comando para
            # detenerse en la posición actual
            self.target_pos = None
            # nota: no modificamos comandos pues el robot ya está en ella
            return

        # cálculo de jacobiano y paso incremental (damped least squares)
        J = self.jacobiano_analitico(q_actual.flatten(),
                                     self.L1, self.L2, self.L3, self.L4)
        dq = np.linalg.inv(J.T @ J + 0.15**2 * np.eye(4)) @ J.T @ (
            self.target_pos - P_real)
        dq = np.clip(dq, -np.deg2rad(20), np.deg2rad(20))
        q_nuevo = np.clip(q_actual + dq, np.deg2rad(-90), np.deg2rad(90))

        # convertir de nuevo a grados de servo
        q_deg_obj = np.rad2deg(q_nuevo.flatten())
        qr = list(self.current_positions)  # conservar ejes no usados
        qr[0] = q_deg_obj[0] + 150.0
        qr[1] = 150.0 - q_deg_obj[1]
        qr[2] = 150.0 - q_deg_obj[2]
        qr[4] = q_deg_obj[3] + 150.0

        # recortar valores entre 0 y 300 para evitar saturaciones
        qr = [max(0.0, min(300.0, x)) for x in qr]

        # notificar al widget/entreniveles superiores
        self.commands_ready.emit(qr)
