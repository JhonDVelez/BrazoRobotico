import numpy as np
import pandas as pd

def calcular_qs(B2, B3, L2, L3):
    # Pedir valores al usuario
    X = float(input("Ingrese valor de X (mm): "))
    Y = float(input("Ingrese valor de Y (mm): "))
    Z = float(input("Ingrese valor de Z (mm): "))

    # ------------------------------
    # Ecuación (5.30): q3
    num_q3 = (2 * L2 * L3) ** 2 - (X**2 + Y**2 + Z**2 - L2**2 - L3**2) ** 2
    den_q3 = X**2 + Y**2 + Z**2 - L2**2 - L3**2

    if num_q3 < 0:
        raise ValueError("No existe solución real para q3.")

    q3 = np.rad2deg(np.arctan2(np.sqrt(num_q3), den_q3))

    # ------------------------------
    # Ecuación (5.29): q2
    raiz_xy = np.sqrt(X**2 + Y**2)
    num_q2 = (L2 + L3 * np.cos(np.deg2rad(q3))) * Z - L3 * np.sin(np.deg2rad(q3)) * raiz_xy
    den_q2 = raiz_xy * (L2 + L3 * np.cos(np.deg2rad(q3))) + Z * L3 * np.sin(np.deg2rad(q3))

    if den_q2 == 0:
        raise ZeroDivisionError("División por cero al calcular q2.")

    q2 = np.rad2deg(np.arctan2(num_q2, den_q2))

    # ------------------------------
    # Ecuación (5.28): q1
    r = np.sqrt(X**2 + Y**2)
    if r <= (B2 + B3):
        raise ValueError("Error en q1: posición fuera del alcance (r muy pequeño).")

    q1 = np.rad2deg(np.arctan2(Y, X)) - np.rad2deg(np.arctan2((B2 + B3), np.sqrt(r**2 - (B2 + B3) ** 2)))

    # ------------------------------
    # Tablas de Datos con pandas
    T = pd.DataFrame([[X, Y, Z]], columns=["X", "Y", "Z"])
    Pos2 = pd.DataFrame([[q1, q2, q3]], columns=["q1_1", "q2_1", "q3_1"])

    print("\nTabla de coordenadas:")
    print(T)
    print("\nTabla de ángulos:")
    print(Pos2)

    return q1, q2, q3


# Ejemplo de uso
if __name__ == "__main__":
    q1, q2, q3 = calcular_qs(5, 5, 15, 20)
    print(f"\nResultados finales: q1 = {q1:.2f}°, q2 = {q2:.2f}°, q3 = {q3:.2f}°")
