import time
import numpy as np
import math
from src.services.robot.robot_compensator import CartesianPidCompensator
from src.features.kinematics.coordinate_correction import apertura_de_garra

class PidService:
    def __init__(self, read_positions_func, enviar_robot_func, joint_update_signal, pid_iteration_signal):
        self._read_positions = read_positions_func
        self._enviar_robot = enviar_robot_func
        self.joint_update = joint_update_signal
        self.pid_iteration = pid_iteration_signal
        self._links = [155.0, 92.0, 111.0, 8.0, 150.0]
        self._kp = np.array([1.5, 1.0, 1.38])
        self._ki = np.array([0.25, 0.1, 0.6])  
        self._kd = np.array([0.02, 0.01, 0.04])
        self._claw_mm = 30
        self._running = True

    def set_pid_gains(self, kp, ki, kd):
        self._kp = np.array(kp, dtype=np.float64)
        self._ki = np.array(ki, dtype=np.float64)
        self._kd = np.array(kd, dtype=np.float64)

    def set_claw_value(self, value):
        self._claw_mm = value

    def _cinematica_directa(self, q):
        L = self._links
        t1, t2, t3, t4 = q
        L1, L2, L3, L4, L5 = L
        arg23 = t2 + t3
        arg234 = t2 + t3 + t4
        projection = (L4 * math.cos(arg23) + L3 * math.sin(arg23) +
                      L2 * math.sin(t2) + L5 * math.sin(arg234))
        px = math.cos(t1) * projection
        py = math.sin(t1) * projection
        pz = (L1 + L3 * math.cos(arg23) - L4 * math.sin(arg23)
              + L2 * math.cos(t2) + L5 * math.cos(arg234))
        return np.array([px, py, pz])

    def _calcular_pseudoinversa(self, q):
        L = self._links
        t1, t2, t3, t4 = q
        L1, L2, L3, L4, L5 = L
        s1, c1 = math.sin(t1), math.cos(t1)
        s2, c2 = math.sin(t2), math.cos(t2)
        s23, c23 = math.sin(t2 + t3), math.cos(t2 + t3)
        s234, c234 = math.sin(t2 + t3 + t4), math.cos(t2 + t3 + t4)
        f = L4 * c23 + L3 * s23 + L2 * s2 + L5 * s234
        df_dt2 = -L4 * s23 + L3 * c23 + L2 * c2 + L5 * c234
        df_dt3 = -L4 * s23 + L3 * c23 + L5 * c234
        df_dt4 = L5 * c234
        dz_dt2 = -L3 * s23 - L4 * c23 - L2 * s2 - L5 * s234
        dz_dt3 = -L3 * s23 - L4 * c23 - L5 * s234
        dz_dt4 = -L5 * s234
        J = np.array([
            [-s1 * f, c1 * df_dt2, c1 * df_dt3, c1 * df_dt4],
            [c1 * f, s1 * df_dt2, s1 * df_dt3, s1 * df_dt4],
            [0, dz_dt2, dz_dt3, dz_dt4]
        ])
        return np.linalg.pinv(J)

    def pid_control_loop(self, target_xyz, limites_deg, max_iter=3000):
        TS = 0.08
        tolerancias = np.array([5.0, 5.0, 5.0])
        target = np.array(target_xyz, dtype=float)
        error_acumulado = np.zeros(3)
        error_anterior = np.zeros(3)
        primera_iteracion = True
        contador_estabilidad = 0
        iteraciones_requeridas = 10
        umbral_mm = 2.5
        t_start = time.time()
        t_anterior = t_start
        
        for i in range(max_iter):
            if not self._running:
                return False
            
            t_actual = time.time()
            dt = t_actual - t_anterior
            if dt < 0.01: dt = 0.01
            
            raw_pos = self._read_positions()
            q_reales_deg = np.array(
                CartesianPidCompensator.robotang_angulos(
                    *raw_pos))
            q_actual_rad = np.radians([
                q_reales_deg[0], q_reales_deg[1],
                q_reales_deg[2], q_reales_deg[4]])
            p_actual = self._cinematica_directa(q_actual_rad)

            error_actual = target - p_actual
            error_abs = np.abs(error_actual)

            if (error_abs[0] < tolerancias[0] and
                    error_abs[1] < tolerancias[1] and
                    error_abs[2] < tolerancias[2]):
                contador_estabilidad += 1
                if contador_estabilidad >= iteraciones_requeridas:
                    return True
            else:
                contador_estabilidad = 0

            P = error_actual * self._kp
            error_acumulado += error_actual * dt
            error_acumulado = np.clip(error_acumulado, -35, 35)
            I = error_acumulado * self._ki

            if primera_iteracion:
                D = np.zeros(3)
                primera_iteracion = False
            else:
                D = (error_actual - error_anterior) / dt * self._kd
            
            v_control = P + I + D
            error_anterior = error_actual.copy()

            J_inv = self._calcular_pseudoinversa(q_actual_rad)
            dq = J_inv @ v_control

            dq_deg = np.degrees(dq)
            # Thresholding dq
            for j in range(len(dq_deg)):
                if 0 < abs(dq_deg[j]) < 0.5:
                    dq_deg[j] += np.sign(dq_deg[j]) * 0.5
            
            q_next_rad = CartesianPidCompensator.apply_physical_limits(
                q_actual_rad + np.radians(dq_deg), limites_deg)
            q_next_rad[0] = math.atan2(target[1], target[0])
            q_out_deg = np.degrees(q_next_rad)
            
            angulo_garra = apertura_de_garra(self._claw_mm)
            
            q_final = [q_out_deg[0], q_out_deg[1], q_out_deg[2],
                       0, q_out_deg[3], angulo_garra]
            
            self.joint_update.emit(q_final)
            self.pid_iteration.emit(round(t_actual - t_start, 4), p_actual.tolist(), target.tolist())
            
            servo_positions = CartesianPidCompensator.angulos_robotang(
                *q_final)
            self._enviar_robot(servo_positions)
            
            t_anterior = t_actual
            time.sleep(max(0, TS - (time.time() - t_actual)))
        
        return False
