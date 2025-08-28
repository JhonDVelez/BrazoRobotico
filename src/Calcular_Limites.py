import numpy as np
import matplotlib.pyplot as plt

def calcular_limites(L1, L2, L3, B1, B2, B3):
    l1 = L1
    l2 = L2
    l3 = L3
    beta1 = B1
    beta2 = B2
    beta3 = B3

    # Rango de ángulos en grados
    q1_deg = np.arange(-150, 151, 5)  # de -150 a 150 con paso 5
    q2_deg = np.arange(0, 181, 5)     # de 0 a 180 con paso 5
    q3_deg = np.arange(-97, 101, 5)   # de -97 a 100 con paso 5

    # Conversión a radianes
    q1_p = np.deg2rad(q1_deg)
    q2_p = np.deg2rad(q2_deg)
    q3_p = np.deg2rad(q3_deg)

    # Inicialización de listas para almacenar resultados
    X, Y, Z = [], [], []

    # Barrido de todos los valores posibles
    for q1_i in q1_p:
        for q2_j in q2_p:
            for q3_k in q3_p:
                # Ecuaciones
                x0 = (beta2 + beta3)*np.sin(q1_i) + np.cos(q1_i)*(l2*np.cos(q2_j) + l3*np.cos(q2_j + q3_k))
                y0 = -(beta2 + beta3)*np.cos(q1_i) + np.sin(q1_i)*(l2*np.cos(q2_j) + l3*np.cos(q2_j + q3_k))
                z0 = l1 + beta1 + l2*np.sin(q2_j) + l3*np.sin(q2_j + q3_k)

                # Guardar
                X.append(x0)
                Y.append(y0)
                Z.append(z0)

    # Convertir a numpy arrays para facilitar cálculos
    X = np.array(X)
    Y = np.array(Y)
    Z = np.array(Z)

    # Cálculo de límites extremos
    x_min, x_max = X.min(), X.max()
    y_min, y_max = Y.min(), Y.max()
    z_min, z_max = Z.min(), Z.max()

    # Mostrar resultados
    print(f"Límites de X: [{x_min}, {x_max}]")
    print(f"Límites de Y: [{y_min}, {y_max}]")
    print(f"Límites de Z: [{z_min}, {z_max}]")

    # Visualización 3D
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    scatter = ax.scatter(X, Y, Z, c=Z, cmap='viridis', s=10)
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")
    ax.set_title("Espacio de trabajo del efector final")
    plt.colorbar(scatter, label="Z")
    plt.show()


# Ejemplo de uso:
if __name__ == "__main__":
    calcular_limites(10, 15, 20, 5, 5, 5)
