import numpy as np

def calcular_pos(q1, q2, q3, B1, B2, B3, L1, L2, L3):
    # Conversión de grados a radianes
    q1_rad = np.deg2rad(q1)
    q2_rad = np.deg2rad(q2)
    q3_rad = np.deg2rad(q3)

    Xs = (B2 + B3) * np.sin(q1_rad) + np.cos(q1_rad) * (L2 * np.cos(q2_rad) + L3 * np.cos(q2_rad + q3_rad))
    Ys = -(B2 + B3) * np.cos(q1_rad) + np.sin(q1_rad) * (L2 * np.cos(q2_rad) + L3 * np.cos(q2_rad + q3_rad))
    Zs = L1 + B1 + L2 * np.sin(q2_rad) + L3 * np.sin(q2_rad + q3_rad)

    return Xs, Ys, Zs


# Ejemplo de uso:
if __name__ == "__main__":
    X, Y, Z = calcular_pos(30, 45, 60, 5, 5, 5, 10, 15, 20)
    print(f"X = {X}, Y = {Y}, Z = {Z}")
