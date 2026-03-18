import cv2
import numpy as np
from data import config_manager as cfg


class ChessboardDetector:
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
        camera_width = cfg.load("camera.json").get("resolution")["width"]
        font_scale_base = 0.3
        thickness_base = 0.4
        # escala base según resolución para tener un punto de partida
        self._base_font_scale = (camera_width / 1280) * font_scale_base
        self.font_scale = self._base_font_scale
        self.font_scale_min = 0.25
        self.font_scale_max = 0.6
        self.font = cv2.FONT_HERSHEY_DUPLEX
        # pos_offset = -
        self.thickness = max(
            0.6, int(self._base_font_scale * thickness_base / font_scale_base))
        self.dot_size = int(self.font_scale * 4)
        self.line_thickness = int(self.font_scale * 2)

    def detect_corners(self, frame: np.ndarray) -> tuple[np.ndarray, np.ndarray] | None:
        """Detecta las esquinas del tablero en un frame.

        La imagen se convierte a escala de grises solo si tiene tres canales. Se
        usa ``findChessboardCornersSB`` con comprobación rápida y umbral
        adaptativo; el refinado con ``cornerSubPix`` sólo se ejecuta si hubo
        éxito.

        Retorna una tupla (grid_extrapolated_9x9, outer_corners_11x11).
        """
        if frame is None:
            return None

        # aceptar también imágenes ya en gris
        gray = cv2.cvtColor(
            frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame

        ret, corners = cv2.findChessboardCornersSB(
            gray,
            self.board_size,
            cv2.CALIB_CB_ACCURACY,
        )

        if not ret:
            return None

        corners_refined = cv2.cornerSubPix(
            gray, corners, self.board_size, (-1, -1), self.criteria
        )

        corners_flat = corners_refined.reshape(-1, 2).astype(np.float32)
        homography, _ = cv2.findHomography(self._ideal_points, corners_flat)

        extrapolated_corners = self.__extrapolate_corners(homography)
        mask_corners = self.__extrapolate_corners_mask_corners(homography)
        return extrapolated_corners, mask_corners

    def __extrapolate_corners(self, homography: np.ndarray) -> np.ndarray:
        """Extrapola las esquinas externas usando homografía proporcionada.

        Args:
            homography (np.ndarray): Matriz de homografía calculada.

        Returns:
            np.ndarray: Esquinas extendidas para abarcar los bordes del tablero que no son 
                        detectados por opencv
        """
        extended_corners = cv2.perspectiveTransform(
            self._extended_ideal.reshape((-1, 1, 2)), homography
        ).reshape(-1, 2)

        rows, cols = self.board_size
        return extended_corners.reshape(rows + 2, cols + 2, 2)

    def __extrapolate_corners_mask_corners(self, homography: np.ndarray) -> np.ndarray:
        """ Extrapola sólo las 4 esquinas del grid extendido para la mascara de búsqueda de objeto.

        Args:
            homography (np.ndarray): Matriz de homografía calculada.

        Returns:
            np.ndarray: Coordenadas de los 4 puntos para la mascara de búsqueda.
        """
        if homography is None:
            return None

        rows, cols = self.board_size
        ideal_outer = np.array(
            [[-2.0, -2.0],
             [-2.0, rows + 1.0],
             [cols + 1.0, rows + 1.0],
             [cols + 1.0, -2.0]],
            dtype=np.float32).reshape(-1, 1, 2)

        mask_corners = cv2.perspectiveTransform(
            ideal_outer, homography).reshape(-1, 2)
        return mask_corners

    def _get_dynamic_font_scale(self, corners: np.ndarray) -> float:
        """Calcula la escala de fuente basada en ancho de celda medida en pixeles.

        Se hacen dos mediciones en filas opuestas para estimar el ancho de celda y
        se promedian. Se aplican límites mínimo y máximo preestablecidos.
        """
        if corners is None:
            return self._base_font_scale

        rows, cols = corners.shape[:2]
        if rows < 2 or cols < 2:
            return self._base_font_scale

        # usar dos mediciones opuestas: borde superior e inferior
        try:
            top_left = corners[0, 0].astype(float)
            top_right = corners[0, cols - 1].astype(float)
            bottom_left = corners[rows - 1, 0].astype(float)
            bottom_right = corners[rows - 1, cols - 1].astype(float)
        except Exception:
            return self._base_font_scale

        width_top = np.linalg.norm(top_right - top_left) / max(1, cols - 1)
        width_bottom = np.linalg.norm(
            bottom_right - bottom_left) / max(1, cols - 1)
        avg_cell_width = (width_top + width_bottom) / 2.0

        if avg_cell_width <= 0:
            return self._base_font_scale

        # escala en base al ancho de celda, normalizada respecto a 30 pixeles
        dynamic_scale = (avg_cell_width / 30.0) * self._base_font_scale
        return float(np.clip(dynamic_scale, self.font_scale_min, self.font_scale_max))

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
        font_scale = self._get_dynamic_font_scale(corners)
        label_thickness = max(
            0.6, int(round(self.thickness * font_scale / max(0.01, self._base_font_scale))))
        dynamic_dot_size = int(self.font_scale * 16)
        dynamic_line_thickness = int(self.font_scale * 8)

        # Si se pedirán coordenadas físicas, calcúlelas de una vez
        phys = None
        if show_phys:
            phys = self.to_physical_coordinates(corners, origin, cell_size_mm)

        # Dibujar líneas usando polylines para mejorar rendimiento
        horizontal_lines = [pts[i].reshape(-1, 1, 2) for i in range(rows)]
        vertical_lines = [pts[:, j].reshape(-1, 1, 2) for j in range(cols)]
        cv2.polylines(frame, horizontal_lines, False,
                      (70, 70, 70), dynamic_line_thickness)
        cv2.polylines(frame, vertical_lines, False,
                      (70, 70, 70), dynamic_line_thickness)

        # Dibujar puntos y etiquetas
        for i in range(rows):
            for j in range(cols):
                point = pts[i, j]
                color = (0, 240, 255)
                point_x, point_y = point
                cv2.circle(frame, tuple(point), dynamic_dot_size, color, -1)

                if show_labels and not border_labels_only:
                    txt = f"[{point[0]},{point[1]}]"
                    (txt_w, txt_h), _ = cv2.getTextSize(
                        txt, self.font, font_scale, label_thickness)
                    cv2.putText(
                        frame,
                        txt,
                        (int(point_x - (txt_w/2)), int(point_y + (txt_h*1.5))),
                        self.font,
                        font_scale,
                        (0, 0, 255),
                        label_thickness,
                        cv2.LINE_AA,
                    )
                if show_phys and phys is not None:
                    # obtiene coordenada correspondiente en mm
                    mmpt = phys[i, j]
                    txt = f"{mmpt[0]:.0f},{mmpt[1]:.0f}"
                    (txt_w, txt_h), _ = cv2.getTextSize(
                        txt, self.font, font_scale, label_thickness)
                    cv2.putText(
                        frame,
                        txt,
                        (int(point_x - (txt_w/2)), int(point_y + (txt_h*1.5))),
                        self.font,
                        font_scale,
                        (0, 255, 0),
                        label_thickness,
                        cv2.LINE_AA,
                    )

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

        Args:
            corners (np.ndarray): Esquinas obtenida y extrapoladas del tablero de ajedrez.
            origin (str | tuple[int, int], optional): Posicion deseada del punto de origen de las
                coordenadas. Defaults to "tl".
            cell_size_mm (tuple[float, float], optional): Tamaño en milímetros de cada cuadro del
                tablero de ajedrez. Defaults to (25.0, 25.0).

        Returns:
            np.ndarray | None: Coordenadas en mm de cada esquina respecto al punto de origen.
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
