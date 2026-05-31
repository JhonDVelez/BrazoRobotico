import numpy as np
from scipy.interpolate import LinearNDInterpolator
import math
import serial
import time
import threading
import re
import matplotlib.pyplot as plt

# ==========================================================================
# 📐 CONFIGURACIÓN ESTÉTICA Y FORMATO PARA LA TESIS (MODIFICABLE)
# ==========================================================================
TAMANO_TITULO = 14
TAMANO_ETIQUETAS_EJES = 11   # Texto de 'X (mm)', 'Iteración Total', etc.
TAMANO_NUMEROS_EJES = 10     # Escala numérica de los ejes (ticks)
TAMANO_LEYENDA = 10          # Cuadro de texto de las series

GROSOR_LINEA = 2.0           # Grosor de la respuesta real del robot
TAMANO_MARCADOR = 4          # Puntos por cada iteración muestreada
GROSOR_LINEA_TARGET = 1.5    # Grosor de la referencia (línea discontinua)

# Paleta de colores formal para ámbitos académicos (Rojo, Verde, Azul sobrios)
COLORES_REALES = ["#FF0000", "#026807", "#02488D"]  
COLORES_TARGET = ["#000000", "#000000", "#000000"]  

# Configuración opcional: Forzar tipografía con serifas para empastados (Times New Roman)
plt.rcParams.update({
    "font.family": "serif",
    "font.size": TAMANO_NUMEROS_EJES
})

# ==========================================================================
# 🛡️ TELEMETRÍA CON FILTRO DE PERSISTENCIA ANTE CORTES/APAGONES
# ==========================================================================
telemetry = {
    'current_pos': [150.0] * 6,
    'last_valid': [150.0] * 6,     # Memoria de hardware para el filtro de saltos
    'running': True,
    'lock': threading.Lock()
}

def serial_reader_thread(ser):
    pattern = re.compile(r"([A-F])(\d+\.?\d*)T[A-F](\d+)")
    congelado_count = [0] * 6  # Contador para romper estancamientos si el salto es real
    
    while telemetry['running']:
        try:
            if ser.in_waiting > 0:
                line = ser.readline().decode('ascii', errors='ignore').strip()
                matches = pattern.findall(line)
                
                # 1. Filtro de ráfagas mutiladas
                if len(matches) < 6:
                    continue 

                temp_pos = [None] * 6
                lecturas_reales = [None] * 6  # Guardamos la verdad del hardware
                
                for motor_char, pos_val, _ in matches:
                    idx = ord(motor_char) - ord('A')
                    if idx < 6: 
                        temp_pos[idx] = float(pos_val)
                        lecturas_reales[idx] = float(pos_val)

                with telemetry['lock']:
                    # 2. Detección de tramas nulas / caídas de tensión
                    if all(v is not None and abs(v) < 0.001 for v in temp_pos[:4]):
                        temp_pos = list(telemetry['last_valid'])
                    else:
                        # 3. FILTRO GLOBAL ANTI-RUIDO ELECTROMAGNÉTICO
                        trama_valida = True
                        for i in range(6):
                            if temp_pos[i] is not None:
                                diff = abs(temp_pos[i] - telemetry['last_valid'][i])
                                
                                # Si el motor reporta un salto mayor a 35 grados en un milisegundo...
                                if diff > 35.0:
                                    congelado_count[i] += 1
                                    # Escape de seguridad: si el cambio se sostiene por más de 8 tramas,
                                    # asumimos que el robot realmente se está moviendo rápido a esa posición.
                                    if congelado_count[i] <= 4:
                                        trama_valida = False  # Marcamos toda la trama como corrupta
                                else:
                                    congelado_count[i] = 0  # Reset del contador si vuelve a valores normales
                        
                        # Si un solo motor falló la prueba física, toda la trama se descarta
                        if not trama_valida:
                            temp_pos = list(telemetry['last_valid'])
                    
                    # 4. Actualización limpia de la telemetría
                    for i in range(6):
                        if temp_pos[i] is not None:
                            telemetry['current_pos'][i] = temp_pos[i]
                            # Mantenemos sincronizado el last_valid con el último estado estable aprobado
                            telemetry['last_valid'][i] = temp_pos[i]
                            
        except Exception as e: 
            print(f"\n Alerta: Hilo de telemetría interrumpido por error: {e}")
            break

def enviar_robot(q_robot, ser):
    motores = ['A', 'B', 'C', 'D', 'E', 'F']
    trama = ""
    for i, char in enumerate(motores):
        val_pwm = int(round(max(0, min(300, float(q_robot[i]))) * (1023/300)))
        trama += f"{char}{val_pwm}"
    trama += "\n"
    ser.write(trama.encode('ascii'))
    ser.flush()

# ==========================================================================
#                   CONVERSIÓN DE ÁNGULOS Y LÍMITES
# ==========================================================================
def angulos_robotang(q1, q2, q3, q4, q5, q6):
    return [q1+150, 150-q2, 150-q3, q4+150, q5+150, q6+150]

def robotang_angulos(q1, q2, q3, q4, q5, q6):
    return [q1-150, 150-q2, 150-q3, q4-150, q5-150, q6-150]

def aplicar_limites_fisicos(q_rad):
    limites_deg = [(-100, 100), (-90, 90), (-130, 130), (-90, 120)]
    q_ajustado = []
    for i, q in enumerate(q_rad):
        q_deg = math.degrees(q)
        low, high = limites_deg[i]
        q_saturado = max(low, min(q_deg, high))
        q_ajustado.append(math.radians(q_saturado))
    return np.array(q_ajustado)

# ==========================================================================
#                   CINEMÁTICA DIRECTA Y JACOBIANO
# ==========================================================================
def cinematica_directa(q, L):
    t1, t2, t3, t4 = q
    L1, L2, L3, L4, L5 = L
    arg23 = t2 + t3
    arg234 = t2 + t3 + t4
    projection = (L4 * math.cos(arg23) + L3 * math.sin(arg23) +
                  L2 * math.sin(t2) + L5 * math.sin(arg234))
    px = math.cos(t1) * projection
    py = math.sin(t1) * projection
    pz = L1 + L3 * math.cos(arg23) - L4 * math.sin(arg23) + L2 * math.cos(t2) + L5 * math.cos(arg234)
    return np.array([px, py, pz])

def calcular_pseudoinversa(q, L):
    t1, t2, t3, t4 = q
    L1, L2, L3, L4, L5 = L
    s1, c1 = math.sin(t1), math.cos(t1)
    s2, c2 = math.sin(t2), math.cos(t2)
    s23, c23 = math.sin(t2+t3), math.cos(t2+t3)
    s234, c234 = math.sin(t2+t3+t4), math.cos(t2+t3+t4)
    f = L4*c23 + L3*s23 + L2*s2 + L5*s234
    df_dt2 = -L4*s23 + L3*c23 + L2*c2 + L5*c234
    df_dt3 = -L4*s23 + L3*c23 + L5*c234
    df_dt4 = L5*c234
    dz_dt2 = -L3*s23 - L4*c23 - L2*s2 - L5*s234
    dz_dt3 = -L3*s23 - L4*c23 - L5*s234
    dz_dt4 = -L5*s234
    J = np.array([
        [-s1 * f,  c1 * df_dt2,  c1 * df_dt3,  c1 * df_dt4],
        [ c1 * f,  s1 * df_dt2,  s1 * df_dt3,  s1 * df_dt4],
        [ 0,       dz_dt2,       dz_dt3,       dz_dt4]
    ])
    return np.linalg.pinv(J)

# ==========================================================================
#        CONTROLADOR PID CARTESIANO CON ANTI-WINDUP Y FILTRADO
# ==========================================================================
KP_EJES = np.array([1.38, 1.0, 1.38]) 
KI_EJES = np.array([0.627, 0.0, 0.8625]) 
KD_EJES = np.array([0.0759, 0.0, 0.0552]) 
ALPHA_D = 0.25  # Factor de filtrado EMA para la derivada.

def control_cinematico_pid_realtime(posicion_objetivo, ser, L, axs, lines_reales, lines_targets, historial_reales, historial_targets):
    max_intentos = 120 # Aumentamos un poco el margen de tiempo
    
    # Memoria del controlador
    error_acumulado_xyz = np.zeros(3)
    error_anterior_xyz = np.zeros(3)
    d_filtrada = np.zeros(3)
    primera_iteracion = True
    
    # --- 🎯 NUEVAS GANANCIAS RECALIBRADAS ---
    # Bajamos KI para evitar la oscilación cíclica vista en la gráfica
    KP_Z_MOD = KP_EJES[2] * 0.9
    KI_Z_MOD = KI_EJES[2] * 0.4  # Reducción drástica para eliminar el rebote
    
    t_anterior = time.time()

    for i in range(max_intentos):
        t_actual = time.time()
        dt = t_actual - t_anterior
        if dt < 0.01: dt = 0.01
        
        # 1. Telemetría y CD
        with telemetry['lock']:
            q_reales_deg = np.array(robotang_angulos(*telemetry['current_pos']))
        q_actual_rad = np.radians([q_reales_deg[0], q_reales_deg[1], q_reales_deg[2], q_reales_deg[4]])
        p_actual = cinematica_directa(q_actual_rad, L)
        
        # Actualización de Gráficas
        historial_reales.append(p_actual)
        historial_targets.append(posicion_objetivo)
        for j in range(3):
            lines_reales[j].set_data(range(len(historial_reales)), np.array(historial_reales)[:, j])
            lines_targets[j].set_data(range(len(historial_targets)), np.array(historial_targets)[:, j])
            axs[j].relim(); axs[j].autoscale_view()
        plt.gcf().canvas.draw_idle(); plt.gcf().canvas.flush_events()

        # 2. Cálculo de Error
        error_actual = posicion_objetivo - p_actual
        
        # --- ESTRATEGIA ANTI-OSCILACIÓN ---
        # Componente P
        P = error_actual * KP_EJES
        P[2] = error_actual[2] * KP_Z_MOD

        # Componente I (Solo actúa si estamos cerca para evitar el "látigo")
        if np.abs(error_actual[2]) < 15.0:
            error_acumulado_xyz[2] += error_actual[2] * dt
        else:
            # Si el salto es muy grande, reseteamos la integral de Z para evitar el pico de 200mm
            error_acumulado_xyz[2] *= 0.5 
            
        error_acumulado_xyz[0:2] += error_actual[0:2] * dt
        
        # Anti-Windup Estricto
        error_acumulado_xyz = np.clip(error_acumulado_xyz, -20, 20)
        I = error_acumulado_xyz * KI_EJES
        I[2] = error_acumulado_xyz[2] * KI_Z_MOD
        
        # --- COMPENSACIÓN DINÁMICA DE GRAVEDAD (BIAS) ---
        # Esta fuerza sostiene al robot independientemente del PID
        R = np.sqrt(p_actual[0]**2 + p_actual[1]**2)
        GRAVEDAD_SOPORTE = 8.0 + (0.055 * R) 
        
        # --- Componente D (Amortiguado) ---
        if primera_iteracion:
            D = np.zeros(3); primera_iteracion = False
        else:
            d_cruda = (error_actual - error_anterior_xyz) / dt
            d_filtrada = 0.3 * d_cruda + 0.7 * d_filtrada
            D = d_filtrada * KD_EJES
            D[2] *= 2.0 # Freno extra en Z

        # Acción de Control Final
        v_control = P + I + D
        v_control[2] += GRAVEDAD_SOPORTE # Inyectamos el soporte de gravedad fuera del PID

        # 3. Verificación de Tolerancia
        if np.all(np.abs(error_actual) < [2.0, 2.0, 2.0]):
            print(f"🎯 ESTABILIZADO EN ITERACIÓN {i}")
            break
            
        # 4. Hardware
        J_inv = calcular_pseudoinversa(q_actual_rad, L)
        dq = J_inv @ v_control
        
        q_next_rad = aplicar_limites_fisicos(q_actual_rad + dq)
        q_next_rad[0] = math.atan2(posicion_objetivo[1], posicion_objetivo[0])
        
        q_out_deg = np.degrees(q_next_rad)
        enviar_robot(angulos_robotang(q_out_deg[0], q_out_deg[1], q_out_deg[2], 0, q_out_deg[3], -80), ser)
        
        error_anterior_xyz = error_actual.copy()
        t_anterior = t_actual

        time.sleep(0.01)

# ==========================================================================
#                                 MAIN LOOP
# ==========================================================================
def main():
    L = [155, 92, 111, 8, 150]
    puerto = 'COM7'
    
    # Inicializamos la Gráfica aplicando el diccionario estético
    plt.ion()
    fig, axs = plt.subplots(3, 1, figsize=(8, 10), sharex=True)
    fig.suptitle('PID eje X,Z y P eje Y- Seguimiento en Tiempo Real', fontsize=TAMANO_TITULO)
    etiquetas = ['X', 'Y', 'Z']
    lines_reales = []
    lines_targets = []
    
    for i in range(3):
        line_real, = axs[i].plot([], [], 
                                   color=COLORES_REALES[i], 
                                   linewidth=GROSOR_LINEA, 
                                   marker='o', 
                                   linestyle='-', 
                                   markersize=TAMANO_MARCADOR, 
                                   label=f'{etiquetas[i]} Real')
        
        line_target, = axs[i].plot([], [], 
                                     color=COLORES_TARGET[i], 
                                     linestyle='--', 
                                     linewidth=GROSOR_LINEA_TARGET, 
                                     label=f'{etiquetas[i]} Target')
        
        axs[i].set_ylabel(f'{etiquetas[i]} (mm)', fontsize=TAMANO_ETIQUETAS_EJES)
        axs[i].tick_params(axis='both', labelsize=TAMANO_NUMEROS_EJES)
        axs[i].grid(True, alpha=0.3)
        axs[i].legend(loc='lower right', fontsize=TAMANO_LEYENDA)
        
        lines_reales.append(line_real)
        lines_targets.append(line_target)
        
    axs[2].set_xlabel('Iteración Total', fontsize=TAMANO_ETIQUETAS_EJES)
    
    try:
        CM904 = serial.Serial(puerto, 9600, timeout=1)
        threading.Thread(target=serial_reader_thread, args=(CM904,), daemon=True).start()
        time.sleep(2)
        
        historial_reales = [] 
        historial_targets = []
        
        while True:
            print("\n Volviendo a HOME...")
            enviar_robot(angulos_robotang(*[0, -45, 120, 0, 30, 0]), CM904)
            time.sleep(2.5)
            
            try:
                line_in = input("Ingrese destino X Y Z (o 'exit'): ")
                if line_in.lower() == 'exit': break
                coords = [float(x) for x in line_in.split()]
                tx_raw, ty_raw, tz_raw = coords
                tx_p = tx_raw + 110
                tx = tx_p
                ty = ty_raw 
                tz = tz_raw
                
                # ==================================================================
                #   DESACOPLAMIENTO SECUENCIAL ESTRICTO: 1° X, 2° Y, 3° Z
                # ==================================================================

                # --- PASO 0: Elevación inicial de seguridad en Z ---
                # Antes de movernos en el plano horizontal (X, Y), levantamos Z a una altura segura.
                # Como el robot arranca desde HOME, mantenemos X en 185 e Y en 0 de forma estricta.
                z_c = tz + 30
                print(" [Fase 0] Elevando Z a zona segura...")
                control_cinematico_pid_realtime(np.array([185, 0, z_c]), CM904, L, axs, lines_reales, lines_targets, historial_reales, historial_targets)


                # --- PASO 1: Mover ÚNICAMENTE el eje X (1°) ---
                # Y se queda bloqueado en 0 (posición de HOME), Z se queda bloqueado en z_c.
                # Solo el eje X viaja en línea recta hacia su destino final 'tx'.
                print(" [Fase 1] Posicionando eje X...")
                control_cinematico_pid_realtime(np.array([tx, 0, z_c]), CM904, L, axs, lines_reales, lines_targets, historial_reales, historial_targets)


                # --- PASO 2: Mover ÚNICAMENTE el eje Y (2°) ---
                # X ya llegó a 'tx' y el PID lo debe clavar ahí. Z sigue bloqueado en z_c.
                # Ahora el eje Y viaja hacia su destino final 'ty'.
                print(" [Fase 2] Posicionando eje Y...")
                control_cinematico_pid_realtime(np.array([tx, ty, z_c]), CM904, L, axs, lines_reales, lines_targets, historial_reales, historial_targets)

                #  --- PASO 3: Descenso final eje Z (3°) ---
                print(" [Fase 3] Posicionando eje Z...")
                # Asentamiento final en el target exacto (Asegura error estático cero)
                control_cinematico_pid_realtime(np.array([tx, ty, tz]), CM904, L, axs, lines_reales, lines_targets, historial_reales, historial_targets)
                 
            except ValueError:
                print(" Formato inválido.")
            
            if input("\n¿Otro movimiento? (s/n): ").lower() != 's': break
            
    except Exception as e:
        print(f" Error crítico en ejecución: {e}")
    finally:
        telemetry['running'] = False
        if 'CM904' in locals(): CM904.close()
        
        # ==================================================================
        #   EXPORTACIÓN DE GRÁFICAS EN ULTRA-ALTA CALIDAD PARA LA TESIS
        # ==================================================================
        print("\n Exportando diagramas de respuesta temporal sin pérdida de calidad...")
        fig.savefig('Respuesta_Temporal_Ziegler_Nichols.pdf', format='pdf', bbox_inches='tight')
        fig.savefig('Respuesta_Temporal_Ziegler_Nichols.png', format='png', dpi=600, bbox_inches='tight')
        print(" Archivos 'Respuesta_Temporal_Ziegler_Nichols.pdf' y '.png' guardados con éxito.")
        
        plt.ioff()
        plt.show()

if __name__ == "__main__":
    main()
