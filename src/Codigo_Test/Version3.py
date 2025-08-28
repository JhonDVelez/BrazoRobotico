import serial
import time
import numpy as np
import matplotlib.pyplot as plt
from control.matlab import tf, c2d, bode

# ------------------- Parámetros iniciales -------------------
entrar1A = int(input("Ingrese valor inicial en grados motor 1 (-150 a 150): "))
entrar1B = int(input("Ingrese valor final en grados motor 1 (-150 a 150): "))

entrar2A = int(input("Ingrese valor inicial en grados motor 2 (30 a 190): "))
entrar2B = int(input("Ingrese valor final en grados motor 2 (30 a 190): "))

entrar3A = int(input("Ingrese valor inicial en grados motor 3 (-97 a 100): "))
entrar3B = int(input("Ingrese valor final en grados motor 3 (-97 a 100): "))

entrar4A = int(input("Ingrese valor inicial en grados motor 4 (-150 a 150): "))
entrar4B = int(input("Ingrese valor final en grados motor 4 (-150 a 150): "))

entrar5A = int(input("Ingrese valor inicial en grados motor 5 (-97 a 100): "))
entrar5B = int(input("Ingrese valor final en grados motor 5 (-97 a 100): "))

entrar6A = int(input("Ingrese valor inicial en grados motor 6 (5 a 142): "))
entrar6B = int(input("Ingrese valor final en grados motor 6 (5 a 142): "))

TimeIn = int(input("Ingrese el tiempo de trabajo en segundos: "))

# ------------------- Filtro discreto -------------------
Ts = 0.1235
fc = 1
wc = 2 * np.pi * fc
num = [1]
den = [1 / wc, 1]
G = tf(num, den)
Gd = c2d(G, Ts)

# Visualización bode
plt.figure()
bode(G)
bode(Gd)
plt.grid(True)
plt.show(block=False)

numz, denz = Gd.num[0][0], Gd.den[0][0]
a1 = numz[1]
b1 = denz[1]

# ------------------- Puerto serie -------------------
CM904 = serial.Serial("COM7", 9600, timeout=1)  # ⚠️ Ajustar COM según tu PC
time.sleep(2)  # Esperar inicialización

# Buffers de datos
q1r, q2r, q3r, q4r, q5r, q6r = [], [], [], [], [], []
q1rf, q2rf, q3rf, q4rf, q5rf, q6rf = [], [], [], [], [], []

cont = 0
tini = time.time()

while (time.time() - tini) < TimeIn:
    # Selección de posiciones inicial/final
    if cont < 500:
        entrar1, entrar2, entrar3 = entrar1A, entrar2A, entrar3A
        entrar4, entrar5, entrar6 = entrar4A, entrar5A, entrar6A
    elif 500 <= cont < 1000:
        entrar1, entrar2, entrar3 = entrar1B, entrar2B, entrar3B
        entrar4, entrar5, entrar6 = entrar4B, entrar5B, entrar6B
    else:
        cont = 0
    cont += 1

    # ------------------- Enviar comandos -------------------
    q1 = int(entrar1 * (63 / 150) + 63)
    q2 = int(entrar2 * (63 / 150) + 26)
    q3 = int(entrar3 * (63 / 150) + 63)
    q4 = int(entrar4 * (63 / 150) + 63)
    q5 = int(entrar5 * (63 / 150) + 63)
    q6 = int(72 - entrar6 * (63 / 150))

    for cmd in [q1, q2, q3, q4, q5, q6]:
        CM904.write(chr(cmd).encode())

    # ------------------- Leer respuesta -------------------
    try:
        line = CM904.readline().decode().strip()
        if not line:
            continue
        M, num = line[0], int(line[1:])

        if M == "A":
            val = (num - 63) * 150 / 63
            q1r.append(val)
            q1rf.append(0 if len(q1r) == 1 else a1 * q1r[-2] - b1 * q1rf[-1])

        elif M == "B":
            val = (num - 26) * 150 / 63
            q2r.append(val)
            q2rf.append(0 if len(q2r) == 1 else a1 * q2r[-2] - b1 * q2rf[-1])

        elif M == "C":
            val = (num - 63) * 150 / 63
            q3r.append(val)
            q3rf.append(0 if len(q3r) == 1 else a1 * q3r[-2] - b1 * q3rf[-1])

        elif M == "D":
            val = (num - 63) * 150 / 63
            q4r.append(val)
            q4rf.append(0 if len(q4r) == 1 else a1 * q4r[-2] - b1 * q4rf[-1])

        elif M == "E":
            val = (num - 63) * 150 / 63
            q5r.append(val)
            q5rf.append(0 if len(q5r) == 1 else a1 * q5r[-2] - b1 * q5rf[-1])

        elif M == "F":
            val = -(num - 72) * 150 / 63
            q6r.append(val)
            q6rf.append(0 if len(q6r) == 1 else a1 * q6r[-2] - b1 * q6rf[-1])

    except Exception as e:
        print("Error en lectura:", e)

tfinal = time.time() - tini

# ------------------- Graficar -------------------
def plot_motor(t, q, qf, idx):
    plt.subplot(3, 2, idx)
    plt.plot(t, q, "-o", label=f"q{idx}")
    plt.plot(t, qf, "-", label=f"q{idx}f")
    plt.xlabel("t (s)")
    plt.ylabel("deg")
    plt.legend()
    plt.grid(True)

plt.figure()
N = len(q1r)
t = np.linspace(0, tfinal, N)
plot_motor(t, q1r, q1rf, 1)
plot_motor(t, q2r, q2rf, 2)
plot_motor(t, q3r, q3rf, 3)
plot_motor(t, q4r, q4rf, 4)
plot_motor(t, q5r, q5rf, 5)
plot_motor(t, q6r, q6rf, 6)
plt.tight_layout()
plt.show()
