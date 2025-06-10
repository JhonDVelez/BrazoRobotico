"""
    This module defines camera-based functions, taking a photograph or frame, processing it,
    and using it.
"""
import numpy as np
import cv2


def take_frame():
    """

    Returns:
        _type_: _description_
    """
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Cannot open camera")
        exit()

    # Capture frame
    ret, frame = cap.read()

    # If frame is read correctly ret is True
    if not ret:
        print("Can't receive frame")
        exit()

    # Release the camera
    cap.release()
    print(type(frame))
    return frame


def get_coordinates(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    mat_size = (7, 7)
    ret, corners = cv2.findChessboardCornersSB(
        gray, mat_size, cv2.CALIB_CB_ADAPTIVE_THRESH)

    if not ret:
        print("Corners not found")
        exit()

    extended_corners = extrapolate_outer_corners_improved(corners, mat_size)

    draw_grid(frame, extended_corners)

    return extended_corners


def extrapolate_outer_corners_improved(corners, mat_size):
    rows, cols = mat_size

    # Create ideal coordinate grid for the interior pattern
    ideal_points = []
    for i in range(rows):
        for j in range(cols):
            ideal_points.append([j, i])
    ideal_points = np.array(ideal_points, dtype=np.float32)

    # Finding the homography between ideal and real points
    corners_flat = corners.reshape(-1, 2).astype(np.float32)
    homography, _ = cv2.findHomography(ideal_points, corners_flat)

    # Create extended grid
    extended_rows, extended_cols = rows + 2, cols + 2
    extended_ideal = []
    for i in range(-1, rows + 1):
        for j in range(-1, cols + 1):
            extended_ideal.append([j, i])
    extended_ideal = np.array(extended_ideal, dtype=np.float32)
    print(type(extended_ideal))
    extended_corners_flat = cv2.perspectiveTransform(
        extended_ideal.reshape(-1, 1, 2), homography  # pylint: disable=too-many-function-args
    ).reshape(-1, 2)

    extended_corners = extended_corners_flat.reshape(
        extended_rows, extended_cols, 2)

    return extended_corners


def draw_grid(frame, extended_corners):
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
