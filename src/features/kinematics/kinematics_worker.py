import numpy as np
import time
from PyQt6.QtCore import QThread, pyqtSignal, pyqtSlot

class KinematicsWorker(QThread):
    """
    Worker encargado exclusivamente del cálculo de cinemática directa, inversa 
    y control realimentado.
    """
    commands_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        # Dimensiones de los eslabones (mm) - Valores originales
        self._L1, self._L2, self._L3, self._L4 = 155, 92, 111, 155

        # Estado interno
        self._current_positions = [150.0] * 6
        self._target_pos = None
        self._start_time = None
        self._prev_positions = list(self._current_positions)
        self._is_paused = False

    # --- Métodos Matemáticos (DH y Transformaciones) ---

    def _h_dh(self, H):
        R = H[:3, :3]
        vect_d = H[:3, 3].reshape((3, 1))
        return R, vect_d, np.array([0, 0, 0]), 1

    def _hrx(self, theta):
        c, s = np.cos(theta), np.sin(theta)
        return np.array([[1, 0, 0, 0], [0, c, -s, 0], [0, s, c, 0], [0, 0, 0, 1]])

    def _hrz(self, theta):
        c, s = np.cos(theta), np.sin(theta)
        return np.array([[c, -s, 0, 0], [s, c, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])

    def _htx(self, d):
        return np.array([[1, 0, 0, d], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])

    def _htz(self, d):
        return np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, d], [0, 0, 0, 1]])

    def _t_matrices(self, t1, t2, t3, t4):
        A1 = self._hrz(t1 + np.pi) @ self._htz(self._L1) @ self._htx(0) @ self._hrx(np.pi/2)
        A2 = self._hrz(t2 + np.pi/2) @ self._htz(0) @ self._htx(self._L2) @ self._hrx(0)
        A3 = self._hrz(t3) @ self._htz(0) @ self._htx(self._L3) @ self._hrx(0)
        A4 = self._hrz(t4) @ self._htz(0) @ self._htx(self._L4) @ self._hrx(0)
        T01 = A1
        T02 = T01 @ A2
        T03 = T02 @ A3
        T04 = T03 @ A4
        return [np.identity(4), T01, T02, T03, T04]

    def cd(self, t1, t2, t3, t4):
        """ Cinemática Directa """
        T_list = self._t_matrices(t1, t2, t3, t4)
        _, P, _, _ = self._h_dh(T_list[-1])
        return P

    def ci(self, px, py, pz, phi):
        """ Cinemática Inversa (Iterativa) """
        q_limit = np.pi/2
        q_min, q_max = -q_limit, q_limit
        q = np.deg2rad(np.array([40, 60, 90, phi], dtype=float)).reshape((4, 1))
        lambda_val, tol, max_iter = 0.5, 0.1, 100
        P_deseada = np.array([[px], [py], [pz]])
        for k in range(max_iter):
            P_actual = self.cd(q[0, 0], q[1, 0], q[2, 0], q[3, 0])
            error = P_deseada - P_actual
            if np.linalg.norm(error) < tol:
                break
            J = self._jacobiano_analitico(q.flatten())
            q = q + lambda_val * (np.linalg.pinv(J) @ error)
            q = np.clip(q, q_min, q_max)
        return q, error

    def _jacobiano_analitico(self, q_flat):
        t1, t2, t3, t4 = q_flat
        T_list = self._t_matrices(t1, t2, t3, t4)
        Pn = T_list[-1][:3, 3].reshape((3, 1))
        Jv = np.zeros((3, 4))
        for j in range(4):
            T_prev = T_list[j]
            P_prev = T_prev[:3, 3].reshape((3, 1))
            Z_prev = T_prev[:3, 2].reshape((3, 1))
            vector_d = Pn - P_prev
            Jv[:, j] = np.cross(Z_prev.flatten(), vector_d.flatten())
        return Jv

    # --- Gestión de Control Realimentado ---

    @pyqtSlot(list, list)
    def update_sensor_data(self, positions, temp_data=None):
        """ Recibe telemetría del robot y recalcula el siguiente comando """
        self._current_positions = list(positions)
        if self._target_pos is None or self._is_paused:
            return

        # Detección de bloqueo
        if self._start_time is not None:
            if time.time() - self._start_time > 1.0:
                mov = sum(abs(self._current_positions[i] - self._prev_positions[i]) for i in [0, 1, 2, 4])
                if mov < 0.1:
                    print("¡Movimiento bloqueado! Abortando secuencia.")
                    self._target_pos = None
                    return
        self._prev_positions = list(self._current_positions)

        # Cálculo de control incremental
        r_deg = self._current_positions
        q_actual = np.array([
            np.deg2rad(r_deg[0] - 150.0),
            np.deg2rad(150.0 - r_deg[1]),
            np.deg2rad(150.0 - r_deg[2]),
            np.deg2rad(r_deg[4] - 150.0),
        ]).reshape((4, 1))

        P_real = self.cd(q_actual[0, 0], q_actual[1, 0], q_actual[2, 0], q_actual[3, 0])
        dist = np.linalg.norm(self._target_pos - P_real)
        
        if dist < 4.0:
            self._target_pos = None # Objetivo alcanzado
            return

        J = self._jacobiano_analitico(q_actual.flatten())
        dq = np.linalg.inv(J.T @ J + 0.15**2 * np.eye(4)) @ J.T @ (self._target_pos - P_real)
        dq = np.clip(dq, -np.deg2rad(20), np.deg2rad(20))
        q_nuevo = np.clip(q_actual + dq, np.deg2rad(-90), np.deg2rad(90))

        # Conversión a comandos de servo
        q_deg_obj = np.rad2deg(q_nuevo.flatten())
        qr = list(self._current_positions)
        qr[0] = q_deg_obj[0] + 150.0
        qr[1] = 150.0 - q_deg_obj[1]
        qr[2] = 150.0 - q_deg_obj[2]
        qr[4] = q_deg_obj[3] + 150.0
        
        qr = [max(0.0, min(300.0, x)) for x in qr]
        self.commands_ready.emit(qr)

    # --- Getters / Setters ---

    def set_target(self, px, py, pz):
        if px is None or py is None or pz is None:
            self._target_pos = None
        else:
            self._target_pos = np.array([[px], [py], [pz]])
            self._start_time = time.time()
            self._prev_positions = list(self._current_positions)
            self.update_sensor_data(self._current_positions)

    def set_paused(self, paused: bool):
        self._is_paused = paused

    def get_current_positions(self):
        return list(self._current_positions)

    def get_target_pos(self):
        return self._target_pos.copy() if self._target_pos is not None else None
