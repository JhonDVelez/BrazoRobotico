import cv2
import numpy as np
from PyQt6.QtCore import QThread


class ChessboardDetector(QThread):
    """Clase separada para detección de tableros de ajedrez.

    El detector mantiene datos precomputados para el tamaño de tablero
    proporcionado, evitando reconstrucciones innecesarias en cada frame.
    """

    def __init__(self, board_size=(7, 7)):
        """Inicializa el detector de tableros de ajedrez.

        Args:
            board_size (Tuple[int, int], optional): Tamaño del tablero de ajedrez
                (filas, columnas). Por defecto es ``(7, 7)``.
        """
        super().__init__()
        self.board_size = board_size
        self.criteria = (cv2.TERM_CRITERIA_EPS +
                         cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

        # cache de puntos ideales para homografía
        rows, cols = board_size
        self._ideal_points = np.array(
            [[j, i] for i in range(rows) for j in range(cols)],
            dtype=np.float32,
        )
        self._extended_ideal = np.array(
            [[j, i] for i in range(-1, rows + 1) for j in range(-1, cols + 1)],
            dtype=np.float32,
        )

    def detect_corners(self, frame: np.ndarray) -> np.ndarray | None:
        """Detecta las esquinas del tablero en un frame.

        La imagen se convierte a escala de grises solo si tiene tres canales. Se
        usa ``findChessboardCornersSB`` con comprobación rápida y umbral
        adaptativo; el refinado con ``cornerSubPix`` sólo se ejecuta si hubo
        éxito.
        """
        if frame is None:
            return None

        # aceptar también imágenes ya en gris
        gray = cv2.cvtColor(
            frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame

        ret, corners = cv2.findChessboardCornersSB(
            gray,
            self.board_size,
            cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_FAST_CHECK,
        )

        if not ret:
            return None

        corners_refined = cv2.cornerSubPix(
            gray, corners, self.board_size, (-1, -1), self.criteria
        )
        return self.__extrapolate_corners(corners_refined)

    def __extrapolate_corners(self, corners: np.ndarray) -> np.ndarray:
        """Extrapola las esquinas externas usando homografía cached.

        La homografía se calcula entre los puntos ideales ya guardados y los
        vértices detectados; después se transforma la malla extendida precalculada.
        """
        corners_flat = corners.reshape(-1, 2).astype(np.float32)
        homography, _ = cv2.findHomography(self._ideal_points, corners_flat)

        extended_corners = cv2.perspectiveTransform(
            self._extended_ideal.reshape((-1, 1, 2)), homography
        ).reshape(-1, 2)

        rows, cols = self.board_size
        return extended_corners.reshape(rows + 2, cols + 2, 2)

    def draw_grid(
        self,
        frame,
        corners,
        show_labels: bool = False,
        border_labels_only: bool = True,
        show_phys: bool = False,
        origin: "str | tuple[int,int]" = "tl",
        cell_size_mm: tuple[float, float] = (30.0, 30.0),
    ):
        """Dibuja la red final obtenida luego de la extrapolación sobre la imagen de referencia
        del tablero de ajedrez.

        Los parámetros ``show_labels`` y ``border_labels_only`` controlan las
        etiquetas de pixeles sobre los nodos. Si ``show_phys`` es ``True`` se
        dibujarán además las coordenadas físicas (mm) obtenidas usando
        :meth:`to_physical_coordinates` con el ``origin`` y ``cell_size_mm``
        especificados. Esto resulta útil para visualizar inmediatamente la
        transformación a un sistema de referencia físico.
        Args:
            frame (numpy.ndarray): Imagen tomada de la cámara
            corners (numpy.ndarray): Matriz de posiciones extendida por extrapolación
            show_labels (bool): Si True, muestra etiquetas de texto en los puntos.
            border_labels_only (bool): Si True, muestra etiquetas solo en los puntos de borde.
            show_phys (bool): Si True, dibuja coordenadas en mm bajo cada punto.
            origin: Esquina usada como (0,0) para el cálculo físico.
            cell_size_mm: Tamaño de cada cuadro en milímetros.
        """
        if corners is None:
            return frame

        rows, cols = corners.shape[:2]
        pts = corners.astype(int)

        # Si se pedirán coordenadas físicas, calcúlelas de una vez
        phys = None
        if show_phys:
            phys = self.to_physical_coordinates(corners, origin, cell_size_mm)

        # Dibujar puntos y etiquetas
        for i in range(rows):
            for j in range(cols):
                point = pts[i, j]
                is_border = (i == 0 or i == rows -
                             1 or j == 0 or j == cols - 1)
                color = (0, 0, 255) if is_border else (0, 240, 255)
                cv2.circle(frame, tuple(point), 5, color, -1)
                if show_labels and (not border_labels_only or is_border):
                    cv2.putText(
                        frame,
                        f"[{point[0]},{point[1]}]",
                        tuple(point + [-25, 15]),
                        cv2.FONT_HERSHEY_COMPLEX_SMALL,
                        0.4,
                        (0, 0, 255),
                        1,
                        cv2.LINE_AA,
                    )
                if show_phys and phys is not None:
                    # obtiene coordenada correspondiente en mm
                    mmpt = phys[i, j]
                    txt = f"{mmpt[0]:.0f},{mmpt[1]:.0f}"
                    cv2.putText(
                        frame,
                        txt,
                        tuple(point + [-25, 10]),
                        cv2.FONT_HERSHEY_COMPLEX_SMALL,
                        0.4,
                        (0, 255, 0),
                        1,
                        cv2.LINE_AA,
                    )

        # Dibujar líneas usando polylines para mejorar rendimiento
        for i in range(rows):
            row_pts = pts[i].reshape(-1, 1, 2)
            cv2.polylines(frame, [row_pts], False, (255, 0, 0), 1)
        for j in range(cols):
            col_pts = pts[:, j].reshape(-1, 1, 2)
            cv2.polylines(frame, [col_pts], False, (255, 0, 0), 1)

        return frame

    # ------------------------------------------------------------
    def to_physical_coordinates(
        self,
        corners: np.ndarray,
        origin: "str | tuple[int, int]" = "tl",
        cell_size_mm: tuple[float, float] = (25.0, 25.0),
    ) -> np.ndarray | None:
        """Convierte la malla de esquinas en coordenadas mm.

        Se usa el índice de cada vértice como referencia para generar una
        rejilla regular de tamaño ``cell_size_mm``. El punto escogido como origen
        se transformará en (0,0). Para obtener resultados consistentes todos los
        valores devueltos son no negativos.
        """
        if corners is None:
            return None

        rows, cols = corners.shape[:2]

        # elegir índices del origen
        if isinstance(origin, str):
            mapping = {
                "tl": (0, 0),
                "tr": (0, cols - 1),
                "bl": (rows - 1, 0),
                "br": (rows - 1, cols - 1),
            }
            origin_idx = mapping.get(origin.lower(), (0, 0))
        else:
            origin_idx = origin

        oi, oj = origin_idx
        sx = cell_size_mm[0] if oj == 0 else -cell_size_mm[0]
        sy = cell_size_mm[1] if oi == 0 else -cell_size_mm[1]

        ij = np.indices((rows, cols), dtype=float)
        coords = np.empty((rows, cols, 2), dtype=float)
        coords[..., 0] = (ij[1] - oj) * sx
        coords[..., 1] = (ij[0] - oi) * sy
        return coords
