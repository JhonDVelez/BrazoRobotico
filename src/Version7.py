import numpy as np
import matplotlib.pyplot as plt
import serial
import time
from control.matlab import tf, c2d, bode

# Importar tus funciones personalizadas
from Calcular_Limites import calcular_limites
from Calcular_Qs import calcular_qs


# --------------------- MENÚ DE ENTRADA ----------------------
print("Revisar que esté en la posición inicial, si no resetear en el micro")

entrar4B = float(input("Ingrese valor final en grados motor 4 (-150 a 150): "))
while entrar4B < -150 or entrar4B > 150:
    print("Valor fuera de rango. Intente nuevamente.")
    entrar4B = float(input("Ingrese valor final en grados motor 4 (-150 a 150): "))

entrar5B = float(input("Ingrese valor final en grados motor 5 (-97 a 100): "))
while entrar5B < -97 or entrar5B > 100:
    print("Valor fuera de rango. Intente nuevamente.")
    entrar5B = float(input("Ingrese valor final en grados motor 5 (-97 a 100): "))

entrar6B = float(input("Ingrese valor final en grados motor 6 (5 a 142): "))
while entrar6B < 5 or entrar6B > 142:
    print("Valor fuera de rango. Intente nuevamente.")
    entrar6B = float(input("Ingrese valor final en grados motor 6 (5 a 142): "))


# ------------------- Cálculo de límites ----------------------
B1, B2, B3 = 26, 12.5, 0
L1, L2, L3 = 53, 94, 70
calcular_limites(L1, L2, L3, B1, B2, B3)


# ------------------- Variables iniciales ----------------------
print("Ingresa valores iniciales")
q1, q2, q3 = calcular_qs(B2, B3, L2, L3)
q1o, q2o, q3o = q1, q2, q3

while q1o < -150 or q1o > 150:
    print("Valor (q1) fuera de rango. Intente nuevamente.")
    q1, q2, q3 = calcular_qs(B2, B3, L2, L3)
    q1o, q2o, q3o = q1, q2, q3

while q2o < 0 or q2o > 180:
    print("Valor (q2) fuera de rango. Intente nuevamente.")
    q1, q2, q3 = calcular_qs(B2, B3, L2, L3)
    q1o, q2o, q3o = q1, q2, q3

while q3o < -97 or q3o > 100:
    print("Valor (q3) fuera de rango. Intente nuevamente.")
    q1, q2, q3 = calcular_qs(B2, B3, L2, L3)
    q1o, q2o, q3o = q1, q2, q3


print("Ingresa valores finales")
q1, q2, q3 = calcular_qs(B2, B3, L2, L3)
q1e, q2e, q3e = q1, q2, q3


# ------------------- Tiempo de trabajo ----------------------
TimeIn = float(input("Ingrese el tiempo de trabajo en segundos: "))
print("Espere unos segundos a que inicie el programa")


# ------------------- Control discreto ----------------------
Ts = 0.1235
fc = 1
wc = 2 * np.pi * fc
G = tf([1], [1/wc, 1])
Gd = c2d(G, Ts)

a1 = Gd.num[0][0][1]
b1 = Gd.den[0][0][1]

# ------------------- Comunicación Serial ----------------------
CM904 = serial.Serial("COM7", 9600, timeout=1)
time.sleep(2)  # espera a que arranque el puerto


# ------------------- Bucle principal ----------------------
q1r, q2r, q3r, q4r, q5r, q6r = [], [], [], [], [], []
q1rf, q2rf, q3rf, q4rf, q5rf, q6rf = [], [], [], [], [], []

cont = 0
tini = time.time()

while (time.time() - tini) < TimeIn:

    if cont < 500:
        entrar1, entrar2, entrar3 = q1o, q2o, q3o
        entrar4, entrar5, entrar6 = 100, 100, 100
    elif 500 <= cont < 1000:
        entrar1, entrar2, entrar3 = q1e, q2e, q3e
        entrar4, entrar5, entrar6 = entrar4B, entrar5B, entrar6B
    else:
        cont = 0

    cont += 1

    # Transformaciones (como en MATLAB)
    q1_val = int(entrar1 * (63 / 150) + 63)
    q2_val = int(entrar2 * (63 / 150) + 26)
    q3_val = int(entrar3 * (63 / 150) + 63)
    q4_val = int(entrar4 * (63 / 150) + 63)
    q5_val = int(entrar5 * (63 / 150) + 63)
    q6_val = int(72 - entrar6 * (63 / 150))

    # Enviar datos por serial
    CM904.write(bytes([q1_val]))
    CM904.write(bytes([q2_val]))
    CM904.write(bytes([q3_val]))
    CM904.write(bytes([q4_val]))
    CM904.write(bytes([q5_val]))
    CM904.write(bytes([q6_val]))

    # Lectura del puerto serial
    if CM904.in_waiting > 0:
        p = CM904.readline().decode(errors="ignore").strip()
        if len(p) > 1:
            M = p[0]
            try:
                num = float(p[1:])
            except ValueError:
                continue

            if M == "A":
                q1r.append((num - 63) * 150 / 63)
            elif M == "B":
                q2r.append((num - 26) * 150 / 63)
            elif M == "C":
                q3r.append((num - 63) * 150 / 63)
            elif M == "D":
                q4r.append((num - 63) * 150 / 63)
            elif M == "E":
                q5r.append((num - 63) * 150 / 63)
            elif M == "F":
                q6r.append(-(num - 72) * 150 / 63)


# ------------------- Gráficas ----------------------
tfinal = time.time() - tini
N = len(q1r)
t = np.linspace(0, tfinal, N)

plt.figure()
plt.subplot(3, 2, 1)
plt.plot(t, q1r, "-o", label="q1")
plt.grid(True)
plt.legend()

plt.subplot(3, 2, 2)
plt.plot(t, q2r, "-o", label="q2")
plt.grid(True)
plt.legend()

plt.subplot(3, 2, 3)
plt.plot(t, q3r, "-o", label="q3")
plt.grid(True)
plt.legend()

plt.subplot(3, 2, 4)
plt.plot(t, q4r, "-o", label="q4")
plt.grid(True)
plt.legend()

plt.subplot(3, 2, 5)
plt.plot(t, q5r, "-o", label="q5")
plt.grid(True)
plt.legend()

plt.subplot(3, 2, 6)
plt.plot(t, q6r, "-o", label="q6")
plt.grid(True)
plt.legend()

plt.show()

