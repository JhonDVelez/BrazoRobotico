"""Este modulo define las funciones basadas en la camara, tomar una fotografia o imagen, procesarla
    y usarla.
"""
import time
import numpy as np
import cv2


def take_frame():
    """Captura una imagen de la camara

    Returns:
        numpy.ndarray: frame capturado
    """
    # Configura la exposicion, balance de blancos y enfoque de la camara
    cap = camera_config()
    if not cap.isOpened():
        print("No fue posible abrir la camara")
        exit()

    # Captura la imagen
    ret, frame = cap.read()

    # Si la imagen fue recibida correctamente ret es true
    if not ret:
        print("No fue posible resibir la imagen")
        exit()

    # Release the camera
    cap.release()
    return frame


def camera_config():
    """Configura la camara como su resolucion, exposicion, balance de blancos y enfoque para
       una mejor calidad de las imagenes tomadas

    Returns:
        cv2.VideoCapture: instancia de la camara configurada
    """
    # Inicializar la cámara
    cap = cv2.VideoCapture(0)  # 0 para la cámara por defecto

    # Verificar si la cámara se abrió correctamente
    if not cap.isOpened():
        print("No se pudo abrir la cámara")
        return None

    # Configurar propiedades de la cámara para mejor calidad
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 30)

    # Habilitar ajuste automático de exposición
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # 0.25 = automático, 0.75 = manual

    # Habilitar balance de blancos automático
    cap.set(cv2.CAP_PROP_AUTO_WB, 1)

    # Configurar ganancia automática
    cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)

    # Dar tiempo a la cámara para que se ajuste
    for _ in range(30):  # Capturar algunos frames para que se ajuste
        cap.read()
        time.sleep(0.2)

    cv2.destroyAllWindows()
    return cap


def get_coordinates(frame):
    """Adquiere la posicion de los pixeles donde se encuentra una esquina en el tablero de ajedrez
    Args:
        frame (numpy.ndarray): Imagen del tablero para la cual se desea obtener la ubicacion de las
            esquinas

    Returns:
        numpy.ndarray: matriz extendida de la posicion en pixeles de las esquinas
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    mat_size = (7, 7)
    ret, corners = cv2.findChessboardCornersSB(
        gray, mat_size, cv2.CALIB_CB_ADAPTIVE_THRESH)

    if not ret:
        print("Esquinas no encontradas")
        exit()

    extended_corners = extrapolate_outer_corners_improved(corners, mat_size)

    draw_grid(frame, extended_corners)
    return extended_corners


def extrapolate_outer_corners_improved(corners, mat_size):
    """Extrapola las esquinas externas del tablero a partir de las obtenidas con opencv

    Args:
        corners (numpy.ndarray): Tupla de coordenadas xy para cada esquina detectada por opencv
        mat_size (tuple): tamaño de la red original, NxM de la cantidad de esquinas en el tablero

    Returns:
        numpy.ndarray: Matriz de posiciones extendida por extrapolacion
    """
    rows, cols = mat_size

    # Crea las coordenadas ideales de la red para el patron interno
    ideal_points = []
    for i in range(rows):
        for j in range(cols):
            ideal_points.append([j, i])
    ideal_points = np.array(ideal_points, dtype=np.float32)

    # Encuentra la homografia entre el real y el ideal
    corners_flat = corners.reshape(-1, 2).astype(np.float32)
    homography, _ = cv2.findHomography(ideal_points, corners_flat)

    # Crea la red extendida
    extended_rows, extended_cols = rows + 2, cols + 2
    extended_ideal = []
    for i in range(-1, rows + 1):
        for j in range(-1, cols + 1):
            extended_ideal.append([j, i])
    extended_ideal = np.array(extended_ideal, dtype=np.float32)

    extended_corners_flat = cv2.perspectiveTransform(
        extended_ideal.reshape(-1, 1, 2), homography  # pylint: disable=too-many-function-args
    ).reshape(-1, 2)

    extended_corners = extended_corners_flat.reshape(
        extended_rows, extended_cols, 2)

    return extended_corners


def draw_grid(frame, extended_corners):
    """Dibuja la red final obtenida luego de la extrapolacion sobre la imagen de referencia
       del tablero de ajedrez

    Args:
        frame (numpy.ndarray): Imagen tomada de la camara
        extended_corners (numpy.ndarray): Matriz de posiciones extendida por extrapolacion
    """
    # Dibujar todas las esquinas
    extended_rows, extended_cols = extended_corners.shape[:2]

    for i in range(extended_rows):
        for j in range(extended_cols):
            point = extended_corners[i, j].astype(int)

            # Diferentes colores para diferentes tipos de esquinas
            if i == 0 or i == extended_rows-1 or j == 0 or j == extended_cols-1:
                # Esquinas exteriores en rojo
                color = (0, 0, 255)
                radius = 5
            else:
                # Esquinas interiores en amarillo
                color = (0, 240, 255)
                radius = 5

            cv2.circle(frame, tuple(point), radius, color, -1)
            cv2.putText(frame,
                        f"[{point[0]},{point[1]}]",
                        tuple(point + [-25, 15]),
                        cv2.FONT_HERSHEY_COMPLEX_SMALL,
                        0.4,
                        (0, 0, 255),
                        1,
                        cv2.LINE_AA)

    for i in range(extended_rows):
        for j in range(extended_cols-1):
            pt1 = tuple(extended_corners[i, j].astype(int))
            pt2 = tuple(extended_corners[i, j+1].astype(int))
            cv2.line(frame, pt1, pt2, (255, 0, 0), 1)

    # Lineas verticales
    for i in range(extended_rows-1):
        for j in range(extended_cols):
            pt1 = tuple(extended_corners[i, j].astype(int))
            pt2 = tuple(extended_corners[i+1, j].astype(int))
            cv2.line(frame, pt1, pt2, (255, 0, 0), 1)

    cv2.imshow('Contornos', frame)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
