import numpy as np
from PyQt6.QtCore import QThread


class KinematicsWorker(QThread):
    def __init__(self):
        super().__init__()
        self.L1, self.L2, self.L3, self.L4 = 155, 92, 111, 155

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
