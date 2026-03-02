import numpy as np


def H_DH(H):
    R = H[:3, :3]
    vect_d = H[:3, 3].reshape((3, 1))
    return R, vect_d, np.array([0, 0, 0]), 1


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


def T_Matrices(t1, t2, t3, t4, L1, L2, L3, L4):
    A1 = HRz(t1 + np.pi) @ HTz(L1) @ HTx(0) @ HRx(np.pi/2)
    A2 = HRz(t2 + np.pi/2) @ HTz(0) @ HTx(L2) @ HRx(0)
    A3 = HRz(t3) @ HTz(0) @ HTx(L3) @ HRx(0)
    A4 = HRz(t4) @ HTz(0) @ HTx(L4) @ HRx(0)
    T01 = A1
    T02 = T01 @ A2
    T03 = T02 @ A3
    T04 = T03 @ A4
    return [np.identity(4), T01, T02, T03, T04]


def CD(t1, t2, t3, t4, L1, L2, L3, L4):
    T_list = T_Matrices(t1, t2, t3, t4, L1, L2, L3, L4)
    _, P, _, _ = H_DH(T_list[-1])
    return P


def JacobianoAnalitico(q_flat, L1, L2, L3, L4):
    t1, t2, t3, t4 = q_flat
    T_list = T_Matrices(t1, t2, t3, t4, L1, L2, L3, L4)
    Pn = T_list[-1][:3, 3].reshape((3, 1))
    Jv = np.zeros((3, 4))
    for j in range(4):
        T_prev = T_list[j]
        P_prev = T_prev[:3, 3].reshape((3, 1))
        Z_prev = T_prev[:3, 2].reshape((3, 1))
        vector_d = Pn - P_prev
        Jv[:, j] = np.cross(Z_prev.flatten(), vector_d.flatten())
    return Jv


def CI(px, py, pz, phi, L1, L2, L3, L4):
    q_limit = np.pi/2
    q_min, q_max = -q_limit, q_limit
    q = np.deg2rad(np.array([40, 60, 90, phi], dtype=float)).reshape((4, 1))
    lambda_val, tol, max_iter = 0.5, 0.1, 100
    P_deseada = np.array([[px], [py], [pz]])
    for k in range(max_iter):
        P_actual = CD(q[0, 0], q[1, 0], q[2, 0], q[3, 0], L1, L2, L3, L4)
        error = P_deseada - P_actual
        if np.linalg.norm(error) < tol:
            break
        J = JacobianoAnalitico(q.flatten(), L1, L2, L3, L4)
        q = q + lambda_val * (np.linalg.pinv(J) @ error)
        q = np.clip(q, q_min, q_max)
    return q, error


def main():
    L1, L2, L3, L4 = 155, 92, 111, 155

    while True:
        print("\n" + "="*50)
        print("         INGRESE NUEVAS COORDENADAS")
        print("="*50)

        try:
            px = float(input("X (mm): "))
            py = float(input("Y (mm): "))
            pz = float(input("Z (mm): "))
        except ValueError:
            print("Entrada inválida.")
            continue
        except KeyboardInterrupt:
            print("\nSaliendo.")
            break

        best_q, error = CI(px, py, pz, 0, L1, L2, L3, L4)
        q_deg = np.rad2deg(best_q.flatten())

        p_alcanzada = CD(best_q[0, 0], best_q[1, 0],
                         best_q[2, 0], best_q[3, 0], L1, L2, L3, L4)
        ax, ay, az = p_alcanzada.flatten()

        qr = [0.0] * 6
        qr[0] = np.abs(q_deg[0] + 150.0)
        qr[1] = np.abs(q_deg[1] - 150.0)
        qr[2] = np.abs(q_deg[2] - 150.0)
        qr[3] = 150.0
        qr[4] = np.abs(q_deg[3] + 150.0)
        qr[5] = 171

        pwms = [round(qr[i] * (1023/300)) for i in range(6)]
        angulos = [round(pwms[i] * 300/1023) for i in range(6)]

        print("\n" + "-"*50)
        print(f"POSICIÓN ALCANZADA : X:{ax:.2f}  Y:{ay:.2f}  Z:{az:.2f}")
        print(f"ERROR DE PRECISIÓN : {np.linalg.norm(error):.4f} mm")
        print(
            f"ÁNGULOS (°)        : M1:{q_deg[0]:.2f}  M2:{q_deg[1]:.2f}  M3:{q_deg[2]:.2f}  M4:{q_deg[3]:.2f}")
        print(
            f"QR MAPEADOS (°)    : M1:{angulos[0]}  M2:{angulos[1]}  M3:{angulos[2]}  M4:{angulos[3]}  M5:{angulos[4]}  M6:{angulos[5]}")
        print(
            f"PWM ENVIADOS       : M1:{pwms[0]}  M2:{pwms[1]}  M3:{pwms[2]}  M4:{pwms[3]}  M5:{pwms[4]}  M6:{pwms[5]}")
        print("-"*50)


if __name__ == "__main__":
    main()
