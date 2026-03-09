import numpy as np
import serial
import time
import threading
import re
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

# ==========================================================================
#                         PARÁMETROS Y CINEMÁTICA
# ==========================================================================

def HRx(theta):
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[1, 0, 0, 0], [0, c, -s, 0], [0, s, c, 0], [0, 0, 0, 1]])

def HRz(theta):
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, -s, 0, 0], [s, c, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])

def HTx(d):
    return np.array([[1, 0, 0, d], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])

def HTz(d):
    return np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, d], [0, 0, 0, 1]])

def T_Matrices(q, L1, L2, L3, L4):
    t1, t2, t3, t4 = q.flatten()
    A1 = HRz(t1 + np.pi) @ HTz(L1) @ HRx(np.pi/2)
    A2 = HRz(t2 + np.pi/2) @ HTx(L2)
    A3 = HRz(t3) @ HTx(L3)
    A4 = HRz(t4) @ HTx(L4)
    T01 = A1; T02 = T01 @ A2; T03 = T02 @ A3; T04 = T03 @ A4
    return [np.identity(4), T01, T02, T03, T04]

def CD(q, L1, L2, L3, L4):
    T_list = T_Matrices(q, L1, L2, L3, L4)
    return T_list[-1][:3, 3].reshape((3, 1))

def JacobianoAnalitico(q, L1, L2, L3, L4):
    T_list = T_Matrices(q, L1, L2, L3, L4)
    Pn = T_list[-1][:3, 3].reshape((3, 1))
    Jv = np.zeros((3, 4))
    for j in range(4):
        T_prev = T_list[j]; P_prev = T_prev[:3, 3].reshape((3, 1)); Z_prev = T_prev[:3, 2].reshape((3, 1))
        Jv[:, j] = np.cross(Z_prev.flatten(), (Pn - P_prev).flatten())
    return Jv

# ==========================================================================
#                         SISTEMA DE TELEMETRÍA
# ==========================================================================

telemetry = {
    'current_pos': [150.0] * 6,
    'current_temp': [0.0] * 6,
    'target_pos': np.array([[0.0], [0.0], [0.0]]),
    'stuck_detected': False,
    'lock': threading.Lock(),
    'running': True
}

def serial_reader_thread(ser):
    pattern = re.compile(r"([A-F])(\d+\.?\d*)T[A-F](\d+)")
    while telemetry['running']:
        try:
            if ser.in_waiting > 0:
                line = ser.readline().decode('ascii', errors='ignore').strip()
                matches = pattern.findall(line)
                with telemetry['lock']:
                    for motor_char, pos_val, temp_val in matches:
                        idx = ord(motor_char) - ord('A')
                        telemetry['current_pos'][idx] = float(pos_val)
                        telemetry['current_temp'][idx] = int(temp_val)
        except: break

# ==========================================================================
#                      DASHBOARD OPTIMIZADO
# ==========================================================================

class RobotDashboard:
    def __init__(self):
        plt.ion()
        self.fig = plt.figure(figsize=(15, 9))
        self.fig.canvas.manager.set_window_title('Dashboard de Control Brazo Robótico')
        gs = GridSpec(6, 2, figure=self.fig, width_ratios=[1, 1.2])
        
        self.start_time = time.time()
        self.t_data = []
        self.max_points = 150 
        
        # --- Lado Izquierdo: Osciloscopios de Motores ---
        self.ax_motors = [self.fig.add_subplot(gs[i, 0]) for i in range(6)]
        self.motor_lines = []
        self.motor_texts = []
        labels = ['A (Base)', 'B (Hombro)', 'C (Codo)', 'D (Aux)', 'E (Pitch)', 'F (Roll)']
        
        for i in range(6):
            self.ax_motors[i].set_ylim(-110, 110)
            self.ax_motors[i].grid(True, ls='--', alpha=0.4)
            line, = self.ax_motors[i].plot([], [], label=labels[i], color=plt.cm.viridis(i/6), lw=1.2)
            self.motor_lines.append(line)
            txt = self.ax_motors[i].text(0.01, 0.65, '', transform=self.ax_motors[i].transAxes, fontsize=9, fontweight='bold')
            self.motor_texts.append(txt)
            self.ax_motors[i].legend(loc='upper right', fontsize='6', frameon=False)

        # --- Lado Derecho: Trayectoria Cartesiana ---
        self.ax_cart = self.fig.add_subplot(gs[0:4, 1])
        self.ax_cart.set_title("Trayectoria en Espacio de Trabajo (mm)", fontsize=12, fontweight='bold')
        self.ax_cart.set_ylim(-350, 350)
        
        colores = ['#FF3131', '#39FF14', '#1F51FF'] # Neon RGB
        self.cart_lines_r = [self.ax_cart.plot([], [], color=colores[i], label=f'{n} Real', lw=2)[0] for i, n in enumerate(['X', 'Y', 'Z'])]
        self.cart_lines_t = [self.ax_cart.plot([], [], '--', color=colores[i], alpha=0.4, label=f'{n} Obj')[0] for i, n in enumerate(['X', 'Y', 'Z'])]
        
        self.target_label = self.ax_cart.text(0.5, 0.05, '', transform=self.ax_cart.transAxes, 
                                             ha='center', fontsize=11, color='white', fontweight='bold',
                                             bbox=dict(facecolor='#222222', alpha=0.9, boxstyle='round,pad=0.5'))
        
        self.ax_cart.grid(True, alpha=0.3)
        self.ax_cart.legend(loc='upper right', ncol=3, fontsize='9')

        self.angles_hist = [[] for _ in range(6)]
        self.pos_r_hist = [[] for _ in range(3)]
        self.pos_t_hist = [[] for _ in range(3)]
        
        plt.tight_layout()

    def update(self, angles, temps, p_real, p_target, is_stuck):
        t = time.time() - self.start_time
        self.t_data.append(t)
        
        if len(self.t_data) > self.max_points:
            self.t_data.pop(0)
            for i in range(6): self.angles_hist[i].pop(0)
            for i in range(3): 
                self.pos_r_hist[i].pop(0)
                self.pos_t_hist[i].pop(0)

        t_min, t_max = max(0, t-8), t+0.5

        for i in range(6):
            self.angles_hist[i].append(angles[i] - 150.0)
            self.motor_lines[i].set_data(self.t_data, self.angles_hist[i])
            self.motor_texts[i].set_text(f"{int(temps[i])}°C" + (" [STUCK]" if is_stuck and i in [1,2] else ""))
            self.motor_texts[i].set_color('red' if temps[i] > 55 or is_stuck else '#2ECC71')
            self.ax_motors[i].set_xlim(t_min, t_max)

        for i in range(3):
            self.pos_r_hist[i].append(p_real[i, 0])
            self.pos_t_hist[i].append(p_target[i, 0])
            self.cart_lines_r[i].set_data(self.t_data, self.pos_r_hist[i])
            self.cart_lines_t[i].set_data(self.t_data, self.pos_t_hist[i])
        
        self.ax_cart.set_xlim(t_min, t_max)
        self.target_label.set_text(f"TARGET >> X: {p_target[0,0]:>6.1f} | Y: {p_target[1,0]:>6.1f} | Z: {p_target[2,0]:>6.1f}")
        
        self.fig.canvas.flush_events()

# ==========================================================================
#                   HILOS DE REFRESH Y CONTROL
# ==========================================================================

def dashboard_refresher(dash, L_dims):
    while telemetry['running']:
        with telemetry['lock']:
            r_deg = list(telemetry['current_pos'])
            r_temp = list(telemetry['current_temp'])
            target_pos = np.copy(telemetry['target_pos'])
            stuck = telemetry['stuck_detected']
        
        q_actual = np.array([np.deg2rad(r_deg[0]-150), np.deg2rad(150-r_deg[1]), 
                             np.deg2rad(150-r_deg[2]), np.deg2rad(r_deg[4]-150)]).reshape((4,1))
        P_real = CD(q_actual, *L_dims)
        dash.update(r_deg, r_temp, P_real, target_pos, stuck)
        time.sleep(0.04)

def enviar_y_esperar_veloz(q_objetivo_rad, ser, tolerancia_deg=2.5, timeout=1.0):
    q_deg_obj = np.rad2deg(q_objetivo_rad.flatten())
    qr = [150.0] * 6
    qr[0], qr[1], qr[2], qr[4] = q_deg_obj[0]+150, 150-q_deg_obj[1], 150-q_deg_obj[2], q_deg_obj[3]+150
    
    for i, char in enumerate(['A', 'B', 'C', 'E']):
        idx = i if i < 3 else 4
        val_pwm = int(round(max(0, min(1023, qr[idx] * (1023.0/300.0)))))
        ser.write(f"{char}{val_pwm}\n".encode())

    t_inicio = time.time()
    pos_previa = [0.0] * 6
    while (time.time() - t_inicio) < timeout:
        with telemetry['lock']: pos_actual = list(telemetry['current_pos'])
        err = [abs(pos_actual[i]-qr[i if i<3 else 4]) for i in [0,1,2,4]]
        if all(e < tolerancia_deg for e in err): 
            with telemetry['lock']: telemetry['stuck_detected'] = False
            return "OK"
        
        if (time.time() - t_inicio) > 1:
            mov = sum([abs(pos_actual[i] - pos_previa[i]) for i in [0,1,2,4]])
            if mov < 0.1: 
                with telemetry['lock']: telemetry['stuck_detected'] = True
                return "STUCK"
        
        pos_previa = pos_actual[:]
        time.sleep(0.04)
    return "TIMEOUT"

# ==========================================================================
#                                   MAIN
# ==========================================================================

def main():
    L_dims = (155, 92, 111, 156)
    dash = RobotDashboard()
    
    try:
        # CAMBIA 'COM7' POR TU PUERTO REAL
        CM904 = serial.Serial('COM7', 9600, timeout=0.05)
        threading.Thread(target=serial_reader_thread, args=(CM904,), daemon=True).start()
        time.sleep(2) 

        # Posición inicial real -> Objetivo inicial
        with telemetry['lock']:
            r_ini = list(telemetry['current_pos'])
            q_ini = np.array([np.deg2rad(r_ini[0]-150), np.deg2rad(150-r_ini[1]), 
                              np.deg2rad(150-r_ini[2]), np.deg2rad(r_ini[4]-150)]).reshape((4,1))
            telemetry['target_pos'] = CD(q_ini, *L_dims)

        threading.Thread(target=dashboard_refresher, args=(dash, L_dims), daemon=True).start()

        while True:
            try:
                print("\n--- Esperando Coordenadas ---")
                tx = float(input("X: ")); ty = float(input("Y: ")); tz = float(input("Z: "))
                with telemetry['lock']:
                    telemetry['target_pos'] = np.array([[tx], [ty], [tz]])
                target_pos = telemetry['target_pos']
            except ValueError: break

            for i in range(15):
                with telemetry['lock']: r_deg = list(telemetry['current_pos'])
                q_actual = np.array([np.deg2rad(r_deg[0]-150), np.deg2rad(150-r_deg[1]), 
                                     np.deg2rad(150-r_deg[2]), np.deg2rad(r_deg[4]-150)]).reshape((4,1))
                P_real = CD(q_actual, *L_dims)
                dist = np.linalg.norm(target_pos - P_real)
                
                if dist < 4.0: 
                    print(f"Llegada confirmada: {dist:.1f}mm")
                    break

                J = JacobianoAnalitico(q_actual, *L_dims)
                # Pseudo-inversa con amortiguamiento (Damped Least Squares)
                dq = np.linalg.inv(J.T @ J + 0.15**2 * np.eye(4)) @ J.T @ (target_pos - P_real)
                dq = np.clip(dq, -np.deg2rad(20), np.deg2rad(20))
                q_nuevo = np.clip(q_actual + dq, np.deg2rad(-90), np.deg2rad(90))

                res = enviar_y_esperar_veloz(q_nuevo, CM904)
                if res == "STUCK": 
                    print("¡Movimiento bloqueado! Abortando secuencia.")
                    break
                
    except KeyboardInterrupt: pass
    finally: 
        telemetry['running'] = False
        CM904.close()
        print("\nConexión cerrada.")

if __name__ == "__main__":
    main()