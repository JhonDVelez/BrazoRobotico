import serial
import time
import numpy as np
import matplotlib.pyplot as plt
import control as ctrl

# ---------------- CONFIGURACIÓN SERIAL ----------------
CM904 = serial.Serial('COM6', 9600, timeout=2)

# ---------------- DECLARACIÓN DE VARIABLES ----------------
q1r, q2r, q3r, q4r, q5r, q6r = [], [], [], [], [], []
q1rf, q2rf, q3rf, q4rf, q5rf, q6rf = [], [], [], [], [], []

# ---------------- FILTRO ----------------
Ts = 0.1235
fc = 1
wc = 2 * np.pi * fc
num = [1]
den = [1/wc, 1]

G = ctrl.tf(num, den)
Gd = ctrl.c2d(G, Ts)

# obtener coeficientes discretos
numz, denz = ctrl.tfdata(Gd)

numz = numz[0][0]   # saca el vector [b0, b1, ...]
denz = denz[0][0]   # saca el vector [a0, a1, ...]

# Extraer el segundo coeficiente (índice 1 en Python)
a1 = numz[1] if len(numz) > 1 else 0
b1 = denz[1] if len(denz) > 1 else 0

print("Coeficientes filtro: a1 =", a1, " b1 =", b1)

# ---------------- PROGRAMA ----------------
start_time = time.time()
cont = 0

while cont == 0:
    print("Revisar que este en la posición inicial, si no resetear en el micro")
    print("Sujetar la base del brazo cuando empiece el movimiento")

    valorm1 = float(input("Ingrese valor final en grados motor 1 (50 a 250): "))
    valorm2 = float(input("Ingrese valor final en grados motor 2 (70 a 200): "))
    valorm3 = float(input("Ingrese valor final en grados motor 3 (50 a 200): "))
    valorm4 = float(input("Ingrese valor final en grados motor 4 (50 a 250): "))
    valorm5 = float(input("Ingrese valor final en grados motor 5 (150 a 250): "))
    valorm6 = float(input("Ingrese valor final en grados motor 6 (38 a 171): "))

    # enviar datos al micro
    CM904.write(f"A{int(valorm1*(1023/300))}\n".encode())
    CM904.write(f"B{int(valorm2*(1023/300))}\n".encode())
    CM904.write(f"C{int(valorm3*(1023/300))}\n".encode())
    CM904.write(f"D{int(valorm4*(1023/300))}\n".encode())
    CM904.write(f"E{int(valorm5*(1023/300))}\n".encode())
    CM904.write(f"F{int(valorm6*(1023/300))}\n".encode())

    # ---------------- LECTURA SERIAL ----------------
    while True:
        p = CM904.readline().decode().strip()
        if not p:
            continue  # no recibió nada
        # print("Recibido:", p)

        if p == "END":
            break

        tokens = p.split(";")
        for t in tokens:
            t = t.strip()
            if len(t) > 1:
                M, val = t[0], float(t[1:])

                if M == "A":
                    q1r.append(val * 300/1023)
                    if len(q1r) > 1:
                        q1rf.append(a1*q1r[-2] - b1*q1rf[-1])
                    else:
                        q1rf.append(q1r[-1])

                elif M == "B":
                    q2r.append(val * 300/1023)
                    if len(q2r) > 1:
                        q2rf.append(a1*q2r[-2] - b1*q2rf[-1])
                    else:
                        q2rf.append(q2r[-1])

                elif M == "C":
                    q3r.append(val * 300/1023)
                    if len(q3r) > 1:
                        q3rf.append(a1*q3r[-2] - b1*q3rf[-1])
                    else:
                        q3rf.append(q3r[-1])

                elif M == "D":
                    q4r.append(val * 300/1023)
                    if len(q4r) > 1:
                        q4rf.append(a1*q4r[-2] - b1*q4rf[-1])
                    else:
                        q4rf.append(q4r[-1])

                elif M == "E":
                    q5r.append(val * 300/1023)
                    if len(q5r) > 1:
                        q5rf.append(a1*q5r[-2] - b1*q5rf[-1])
                    else:
                        q5rf.append(q5r[-1])

                elif M == "F":
                    q6r.append(val * 300/1023)
                    if len(q6r) > 1:
                        q6rf.append(a1*q6r[-2] - b1*q6rf[-1])
                    else:
                        q6rf.append(q6r[-1])

    salir = int(input("Digite 1 para salir y graficar, o 0 para seguir realizando cambios: "))
    if salir == 1:
        cont = 1
    else:
        cont = 0

tfinal = time.time() - start_time

# ---------------- GRAFICAR ----------------
def graficar(qr, qrf, titulo, subplot_pos):
    N = len(qr)
    Ts = tfinal / N
    t = np.arange(1, N+1) * Ts
    plt.subplot(3,2,subplot_pos)
    plt.plot(t, qr, '-o', label=f'{titulo}')
    #plt.plot(t, qrf, '-', label=f'{titulo}f') No funciona correctamente el filtro
    plt.xlabel("t(s)")
    plt.ylabel("deg")
    plt.grid(True)
    plt.legend()

plt.figure(figsize=(10,8))
graficar(q1r, q1rf, "q1", 1)
graficar(q2r, q2rf, "q2", 2)
graficar(q3r, q3rf, "q3", 3)
graficar(q4r, q4rf, "q4", 4)
graficar(q5r, q5rf, "q5", 5)
graficar(q6r, q6rf, "q6", 6)
plt.tight_layout()
plt.show()
import sys
sys.exit()