"""
Modulo que define el KinematicsWorker para el calculo de cinematica.

Este modulo contiene la logica para el calculo de cinematica directa (CD) e
inversa (CI) de un brazo robotico, ademas de gestionar el control
realimentado mediante el uso de hilos (QThread).

Conexiones:
    - Emite `commands_ready` cuando se calcula un nuevo comando de posicion.
    - Emite `error_occurred` en caso de fallos en el calculo.
    - Se conecta con `RobotWorker` (indirectamente a traves de señales) para
      recibir telemetria y enviar comandos.
"""

import time
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal, pyqtSlot


class KinematicsWorker(QThread):
    """
    Worker encargado exclusivamente del calculo de cinematica y control.

    Esta clase implementa algoritmos de cinematica directa e inversa iterativa
    para controlar un brazo robotico de 4 grados de libertad (DOF) activos.

    Attributes:
        commands_ready (pyqtSignal): Señal que envia una lista de posiciones
            (float) para los servos del robot.
        error_occurred (pyqtSignal): Señal que envia un mensaje de error (str)
            en caso de fallas criticas.
    """
    commands_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self):
        """
        Inicializa el worker de cinematica con las dimensiones del robot.

        Define las longitudes de los eslabones y establece el estado inicial
        del sistema de control.
        """
        super().__init__()
        # Dimensiones de los eslabones (mm) - Valores originales
        self._L1, self._L2, self._L3, self._L4 = 155, 92, 111, 155

        # Estado interno
        self._current_positions = [150.0] * 6
        self._target_pos = None
        self._start_time = None
        self._prev_positions = list(self._current_positions)
        self._is_paused = False

    # --- Metodos Matematicos (DH y Transformaciones) ---

    def _h_dh(self, H):
        """
        Extrae la rotacion y traslacion de una matriz de transformacion homogenea.

        Args:
            H (np.ndarray): Matriz de transformacion homogenea de 4x4.

        Returns:
            tuple: Contiene (R, vect_d, zero_array, scale) donde:
                - R (np.ndarray): Matriz de rotacion 3x3.
                - vect_d (np.ndarray): Vector de traslacion 3x1.
                - zero_array (np.ndarray): Array de ceros para compatibilidad.
                - scale (int): Factor de escala (siempre 1).
        """
        R = H[:3, :3]
        vect_d = H[:3, 3].reshape((3, 1))
        return R, vect_d, np.array([0, 0, 0]), 1

    def _hrx(self, theta):
        """
        Genera una matriz de rotacion en el eje X.

        Args:
            theta (float): Angulo de rotacion en radianes.

        Returns:
            np.ndarray: Matriz de transformacion de 4x4.
        """
        c, s = np.cos(theta), np.sin(theta)
        return np.array([[1, 0, 0, 0], [0, c, -s, 0], [0, s, c, 0], [0, 0, 0, 1]])

    def _hrz(self, theta):
        """
        Genera una matriz de rotacion en el eje Z.

        Args:
            theta (float): Angulo de rotacion en radianes.

        Returns:
            np.ndarray: Matriz de transformacion de 4x4.
        """
        c, s = np.cos(theta), np.sin(theta)
        return np.array([[c, -s, 0, 0], [s, c, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])

    def _htx(self, d):
        """
        Genera una matriz de traslacion en el eje X.

        Args:
            d (float): Distancia de traslacion.

        Returns:
            np.ndarray: Matriz de transformacion de 4x4.
        """
        return np.array([[1, 0, 0, d], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])

    def _htz(self, d):
        """
        Genera una matriz de traslacion en el eje Z.

        Args:
            d (float): Distancia de traslacion.

        Returns:
            np.ndarray: Matriz de transformacion de 4x4.
        """
        return np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, d], [0, 0, 0, 1]])

    def _t_matrices(self, t1, t2, t3, t4):
        """
        Calcula las matrices de transformacion sucesivas para cada eslabon.

        Utiliza los parametros DH (Denavit-Hartenberg) personalizados para el robot.

        Args:
            t1 (float): Angulo de la articulacion 1 (Base) en radianes.
            t2 (float): Angulo de la articulacion 2 (Hombro) en radianes.
            t3 (float): Angulo de la articulacion 3 (Codo) en radianes.
            t4 (float): Angulo de la articulacion 4 (Muñeca) en radianes.

        Returns:
            list: Lista de 5 matrices np.ndarray (4x4) desde la base hasta el efector final.
        """
        # A1: Base a Hombro
        A1 = self._hrz(t1 + np.pi) @ self._htz(self._L1) @ self._htx(0) @ self._hrx(np.pi/2)
        # A2: Hombro a Codo
        A2 = self._hrz(t2 + np.pi/2) @ self._htz(0) @ self._htx(self._L2) @ self._hrx(0)
        # A3: Codo a Muñeca
        A3 = self._hrz(t3) @ self._htz(0) @ self._htx(self._L3) @ self._hrx(0)
        # A4: Muñeca a Pinza
        A4 = self._hrz(t4) @ self._htz(0) @ self._htx(self._L4) @ self._hrx(0)

        T01 = A1
        T02 = T01 @ A2
        T03 = T02 @ A3
        T04 = T03 @ A4
        return [np.identity(4), T01, T02, T03, T04]

    def cd(self, t1, t2, t3, t4):
        """
        Calcula la cinematica directa para obtener la posicion del efector final.

        Args:
            t1 (float): Angulo articular 1 en radianes.
            t2 (float): Angulo articular 2 en radianes.
            t3 (float): Angulo articular 3 en radianes.
            t4 (float): Angulo articular 4 en radianes.

        Returns:
            np.ndarray: Vector de posicion [x, y, z]^T de 3x1.
        """
        T_list = self._t_matrices(t1, t2, t3, t4)
        _, P, _, _ = self._h_dh(T_list[-1])
        return P

    def ci(self, px, py, pz, phi):
        """
        Calcula la cinematica inversa iterativa para alcanzar una posicion.

        Utiliza el metodo de Newton-Raphson con el Jacobiano analitico para
        encontrar los angulos articulares que minimizan el error de posicion.

        Args:
            px (float): Posicion deseada en X (mm).
            py (float): Posicion deseada en Y (mm).
            pz (float): Posicion deseada en Z (mm).
            phi (float): Angulo de aproximacion inicial para la muñeca (grados).

        Returns:
            tuple: Contiene (q, error) donde:
                - q (np.ndarray): Vector de angulos articulares 4x1 en radianes.
                - error (np.ndarray): Vector de error de posicion residual 3x1.
        """
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
            # Actualizacion mediante la pseudoinversa de Moore-Penrose
            q = q + lambda_val * (np.linalg.pinv(J) @ error)
            q = np.clip(q, q_min, q_max)
        return q, error

    def _jacobiano_analitico(self, q_flat):
        """
        Calcula el Jacobiano analitico del robot para la posicion actual.

        El Jacobiano relaciona las velocidades articulares con las velocidades
        lineales del efector final (Jv).

        Args:
            q_flat (array-like): Angulos articulares actuales [t1, t2, t3, t4] en radianes.

        Returns:
            np.ndarray: Matriz Jacobiana de 3x4.
        """
        t1, t2, t3, t4 = q_flat
        T_list = self._t_matrices(t1, t2, t3, t4)
        Pn = T_list[-1][:3, 3].reshape((3, 1))
        Jv = np.zeros((3, 4))
        for j in range(4):
            T_prev = T_list[j]
            P_prev = T_prev[:3, 3].reshape((3, 1))
            Z_prev = T_prev[:3, 2].reshape((3, 1))
            vector_d = Pn - P_prev
            # Jv_j = z_{j-1} x (P_n - P_{j-1}) para articulaciones de revolucion
            Jv[:, j] = np.cross(Z_prev.flatten(), vector_d.flatten())
        return Jv

    # --- Gestion de Control Realimentado ---

    @pyqtSlot(list, list)
    def update_sensor_data(self, positions, temp_data=None):
        """
        Recibe telemetria del robot y recalcula el siguiente comando de control.

        Este metodo implementa un esquema de control incremental (Damped Least Squares)
        para mover el robot hacia el objetivo definido en `set_target`. Tambien
        incluye deteccion de bloqueos mecanicos.

        Args:
            positions (list): Posiciones actuales de los servos (0-300 grados).
            temp_data (list, optional): Datos de temperatura de los motores.
        """
        self._current_positions = list(positions)
        if self._target_pos is None or self._is_paused:
            return

        # Deteccion de bloqueo: Si ha pasado mas de 1s y el movimiento es minimo
        if self._start_time is not None:
            if time.time() - self._start_time > 1.0:
                mov = sum(abs(self._current_positions[i] - self._prev_positions[i]) for i in [0, 1, 2, 4])
                if mov < 0.1:
                    print("¡Movimiento bloqueado! Abortando secuencia.")
                    self._target_pos = None
                    return
        self._prev_positions = list(self._current_positions)

        # Mapeo de grados de servos a coordenadas articulares (radianes)
        # Se ajustan los offsets y direcciones segun el ensamblaje fisico
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

        # Control mediante Minimos Cuadrados Amortiguados (DLS)
        J = self._jacobiano_analitico(q_actual.flatten())
        dq = np.linalg.inv(J.T @ J + 0.15**2 * np.eye(4)) @ J.T @ (self._target_pos - P_real)
        dq = np.clip(dq, -np.deg2rad(20), np.deg2rad(20)) # Limite de velocidad por tick
        q_nuevo = np.clip(q_actual + dq, np.deg2rad(-90), np.deg2rad(90))

        # Re-mapeo a comandos de servo (grados)
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
        """
        Define un nuevo objetivo cartesiano para el robot.

        Args:
            px (float): Objetivo X en mm.
            py (float): Objetivo Y en mm.
            pz (float): Objetivo Z en mm.
        """
        if px is None or py is None or pz is None:
            self._target_pos = None
        else:
            self._target_pos = np.array([[px], [py], [pz]])
            self._start_time = time.time()
            self._prev_positions = list(self._current_positions)
            self.update_sensor_data(self._current_positions)

    def set_paused(self, paused: bool):
        """
        Pausa o reanuda el proceso de control.

        Args:
            paused (bool): True para pausar, False para reanudar.
        """
        self._is_paused = paused

    def get_current_positions(self):
        """
        Obtiene las ultimas posiciones conocidas de los servos.

        Returns:
            list: Lista de 6 flotantes (grados).
        """
        return list(self._current_positions)

    def get_target_pos(self):
        """
        Obtiene el objetivo cartesiano actual.

        Returns:
            np.ndarray: Vector 3x1 o None si no hay objetivo.
        """
        return self._target_pos.copy() if self._target_pos is not None else None
