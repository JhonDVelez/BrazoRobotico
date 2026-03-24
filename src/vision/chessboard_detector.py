import cv2
import numpy as np
from data import config_manager as cfg


class ChessboardDetector:
    """Clase separada para detección de tableros ChArUco.

    El detector mantiene datos precomputados para el tamaño de tablero
    proporcionado, evitando reconstrucciones innecesarias en cada frame.
    Utiliza el identificador de cada esquina detectada para calcular una
    homografía precisa y extrapolar la malla completa, incluso con oclusiones.
    """

    def __init__(
        self,
        board_size: tuple[int, int] = (12, 5),
        aruco_dict=None,
        charuco_board=None,
        charuco_detector=None
    ):
        """Inicializa el detector de tableros ChArUco.

        Args:
            board_size (Tuple[int, int], optional): Número de esquinas internas 
                del tablero (filas, columnas). Por defecto es ``(7, 7)``.
            dictionary_id (int, optional): Diccionario ArUco a utilizar.
            square_length (float, optional): Longitud del lado del cuadro (metros).
            marker_length (float, optional): Longitud del lado del marcador ArUco (metros).
        """
        super().__init__()
        self.board_size = board_size
        rows, cols = board_size

        # Incializa los detectores para el codigo ArUco y almacena los de ChArUco
        self.aruco_dict = aruco_dict
        detector_params = cv2.aruco.DetectorParameters()
        self.aruco_detector = cv2.aruco.ArucoDetector(
            charuco_board.getDictionary(), detector_params)
        self.charuco_board = charuco_board
        self.charuco_detector = charuco_detector

        # Configuraciones guardadas de la cámara
        camera = cfg.load("camera.json")
        camera_resolution = camera.get("resolution", {})
        camera_width = camera_resolution.get("width", 1280)

        # Inicializa la configuración de escala automática de texto e indicadores del tablero.
        font_scale_base = 0.3
        thickness_base = 0.4

        self.base_font_scale = (camera_width / 1280) * font_scale_base
        self.font_scale = self.base_font_scale
        self.font_scale_min = 0.25
        self.font_scale_max = 0.6
        self.font = cv2.FONT_HERSHEY_DUPLEX

        self.thickness = max(
            0.6, int(self.base_font_scale * thickness_base / font_scale_base)
        )
        self.dot_size = int(self.font_scale * 4)
        self.line_thickness = int(self.font_scale * 2)

        self.label_thickness = None
        self.dynamic_dot_size = None

    def detect_corners(self, frame) -> None | dict:
        """Detecta las esquinas del tablero ChArUco en un frame.

        Convierte la imagen a escala de grises y utiliza el detector ChArUco.
        Si encuentra suficientes esquinas, cruza los IDs detectados con los 
        puntos ideales para calcular la homografía y extrapolar la malla 
        exterior.

        Returns:
            np.ndarray | None: Matriz de esquinas extrapoladas con forma 
            (rows + 2, cols + 2, 2) o None si falla la detección.
        """
        if frame is None:
            return None

        marker_corners, marker_ids, _ = self.aruco_detector.detectMarkers(
            frame)

        if marker_ids is None or len(marker_ids) < 4:
            return None

        charuco_corners, charuco_ids, _, _ = self.charuco_detector.detectBoard(
            frame, markerCorners=marker_corners, markerIds=marker_ids
        )

        if charuco_corners is None or len(charuco_corners) < 4:
            return None

        # Homografía con los corners interiores visibles
        all_obj_points, all_img_points = self.charuco_board.matchImagePoints(
            charuco_corners, charuco_ids)
        obj_2d = all_obj_points[:, :2].astype(np.float32)
        img_2d = all_img_points[:, :].astype(np.float32)
        H, _ = cv2.findHomography(obj_2d, img_2d, cv2.RANSAC, 3.0)

        extrapolated_results = self.__extrapolate_corners(
            self.charuco_board, charuco_corners, charuco_ids, H)

        return self.build_unified_grid(extrapolated_results)

    def __extrapolate_corners(self, board, charuco_corners, charuco_ids, H) -> np.ndarray:
        """Extrapola las esquinas externas usando la homografía calculada.

        Args:
            homography (np.ndarray): Matriz de homografía.

        Returns:
            np.ndarray: Esquinas extendidas que abarcan los bordes externos 
            del tablero.
        """
        if H is None:
            return None

        # ── Grilla completa (interiores + exteriores) ──────────────────────────
        full_grid_3d, cols, rows = self._get_full_grid_corners(board)
        interior_set = self._get_interior_ids_set(board)
        visible_ids = set(charuco_ids.flatten())

        # Proyectar TODA la grilla con la homografía
        grid_2d = full_grid_3d[:, :2].reshape(-1, 1, 2)
        projected_all = cv2.perspectiveTransform(
            grid_2d, H)  # (cols*rows, 1, 2)

        interior_corners = []   # Detectados por detectBoard
        interior_ids = []
        estimated_interior = []  # Interiores ocultos (tapados)
        estimated_interior_ids = []
        exterior_corners = []   # Borde externo
        exterior_ids = []   # Guardamos (col, row) como referencia

        for idx in range(cols * rows):
            row = idx // cols
            col = idx % cols
            pt = projected_all[idx]

            is_interior = (col, row) in interior_set

            if is_interior:
                # ID en el sistema ChArUco (fila-1, col-1 dentro de interiores)
                charuco_id = (row - 1) * (cols - 2) + (col - 1)
                if charuco_id in visible_ids:
                    # Ya detectado, usamos la posición real de detectBoard
                    idx_in_detected = list(
                        charuco_ids.flatten()).index(charuco_id)
                    interior_corners.append(charuco_corners[idx_in_detected])
                    interior_ids.append(charuco_id)
                else:
                    # Interior oculto → estimado con homografía
                    estimated_interior.append(pt)
                    estimated_interior_ids.append(charuco_id)
            else:
                # Punto del borde exterior → siempre estimado
                exterior_corners.append(pt)
                exterior_ids.append((col, row))

        return {
            "visible_corners":          interior_corners,
            "visible_ids":              interior_ids,
            "estimated_interior":       estimated_interior,
            "estimated_interior_ids":   estimated_interior_ids,
            "exterior_corners":         exterior_corners,
            "exterior_ids":             exterior_ids,
            "homography":               H,
            "grid_shape":               (cols, rows),
        }

    def _get_interior_ids_set(self, board):
        """
        Retorna un set con las coordenadas (col, row) de los corners interiores
        para poder excluirlos al dibujar los estimados exteriores.
        """
        size = board.getChessboardSize()
        inner = set()
        for row in range(1, size[1]):
            for col in range(1, size[0]):
                inner.add((col, row))
        return inner

    def _get_full_grid_corners(self, board):
        """
        Genera TODOS los puntos de la grilla en coordenadas 3D del tablero,
        incluyendo los exteriores que getChessboardCorners() no retorna.

        Para un tablero (SQUARES_X, SQUARES_Y), la grilla completa es
        (SQUARES_X+1) × (SQUARES_Y+1) puntos.
        """
        size = board.getChessboardSize()   # (SQUARES_X, SQUARES_Y)
        square_length = board.getSquareLength()

        cols = size[0] + 1   # 13 para un tablero de 12 cuadros
        rows = size[1] + 1   # 6  para un tablero de 5 cuadros

        points = []
        for row in range(rows):
            for col in range(cols):
                points.append([col * square_length, row * square_length, 0.0])

        return np.array(points, dtype=np.float32), cols, rows

    def build_unified_grid(self, result: dict):
        """
        Unifica todos los corners en una grilla ordenada de (cols × rows) puntos.
        new_id = row * cols + col  →  0 en esquina superior izquierda,
                                    aumenta →, luego baja una fila y repite.
        """
        cols, rows = result["grid_shape"]   # (13, 6) para tablero 12×5
        inner_cols = cols - 2               # 11 columnas interiores

        # ── Mapeo (col, row) → corner_point ───────────────────────────────────

        grid = {}   # key: (col, row), value: punto shape (1,2)

        # 1. Interiores visibles
        for corner, cid in zip(result["visible_corners"], result["visible_ids"]):
            col = cid % inner_cols + 1
            row = cid // inner_cols + 1
            grid[(col, row)] = corner[0]   # shape (2,)

        # 2. Interiores estimados (ocultos)
        for corner, cid in zip(result["estimated_interior"], result["estimated_interior_ids"]):
            col = cid % inner_cols + 1
            row = cid // inner_cols + 1
            grid[(col, row)] = corner[0]   # shape (2,)

        # 3. Exteriores
        for corner, (col, row) in zip(result["exterior_corners"], result["exterior_ids"]):
            grid[(col, row)] = corner[0]   # shape (2,)

        # ── Construir arrays ordenados por new_id ─────────────────────────────

        unified_ids = []
        unified_corners = []

        for row in range(rows):
            for col in range(cols):
                new_id = row * cols + col
                if (col, row) in grid:
                    unified_ids.append(new_id)
                    unified_corners.append(grid[(col, row)])

        unified_corners = np.array(unified_corners, dtype=np.float32)  # (N, 2)
        unified_ids = np.array(
            unified_ids,     dtype=np.int32)    # (N,)
        r = result.copy()
        r.update({"unified_corners": unified_corners,
                  "unified_ids": unified_ids})
        return r

    def _get_dynamic_font_scale(self, corners: np.ndarray) -> float:
        """Calcula la escala de fuente basada en ancho de celda medida en pixeles.

        Se hacen dos mediciones en filas opuestas para estimar el ancho de celda y
        se promedian. Se aplican límites mínimo y máximo preestablecidos.
        """
        if corners is None:
            return self.base_font_scale

        rows, cols = corners.shape[:2]
        if rows < 2 or cols < 2:
            return self.base_font_scale

        try:
            top_left = corners[0, 0].astype(float)
            top_right = corners[0, cols - 1].astype(float)
            bottom_left = corners[rows - 1, 0].astype(float)
            bottom_right = corners[rows - 1, cols - 1].astype(float)
        except Exception:
            return self.base_font_scale

        width_top = np.linalg.norm(top_right - top_left) / max(1, cols - 1)
        width_bottom = np.linalg.norm(
            bottom_right - bottom_left) / max(1, cols - 1)
        avg_cell_width = (width_top + width_bottom) / 2.0

        if avg_cell_width <= 0:
            return self.base_font_scale

        dynamic_scale = (avg_cell_width / 30.0) * self.base_font_scale
        self.font_scale = float(
            np.clip(dynamic_scale, self.font_scale_min, self.font_scale_max))

        self.label_thickness = max(
            0.6, int(round(self.thickness * self.font_scale /
                     max(0.01, self.base_font_scale)))
        )
        self.dynamic_dot_size = int(self.font_scale * 8)

    def draw_grid(
        self,
        frame,
        results,
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
            frame (np.ndarray): Imagen tomada de la cámara.
            corners (np.ndarray): Matriz de posiciones extendida por extrapolación.
            show_labels (bool): Si True, muestra etiquetas de texto en los puntos.
            border_labels_only (bool): Si True, muestra etiquetas solo en los bordes.
            show_phys (bool): Si True, dibuja coordenadas físicas (mm) bajo cada punto.
            origin: Esquina usada como origen (0,0) para cálculo físico.
            cell_size_mm: Tamaño de cada cuadro en milímetros.
        """
        vis = frame.copy()
        corners = results["unified_corners"].reshape(-1, 13, 2)
        self._get_dynamic_font_scale(corners)

        # Corners interiores visibles → verde
        for corner in results["visible_corners"]:
            pt = tuple(corner[0].astype(int))
            cv2.circle(vis, pt, self.dynamic_dot_size, (0, 230, 0), -1)

        # Corners interiores ocultos → naranja
        for corner in results["estimated_interior"]:
            pt = tuple(corner[0].astype(int))
            cv2.circle(vis, pt, self.dynamic_dot_size, (0, 140, 255), -1)

        # Corners exteriores estimados → azul
        for corner in results["exterior_corners"]:
            pt = tuple(corner[0].astype(int))
            cv2.circle(vis, pt, self.dynamic_dot_size, (220, 60, 0), -1)

        # print("new")
        physical_corners = self.to_physical_coordinates(
            corners)
        for corner, phy_corner in zip(corners.reshape(-1, 1, 2), physical_corners.reshape(-1, 1, 2)):
            corner = corner[0]
            phy_corner = phy_corner[0]
            cv2.putText(
                vis,
                f"[{phy_corner[1]},{phy_corner[0]}]",
                tuple(corner.astype(int) + [-25, 15]),
                cv2.FONT_HERSHEY_COMPLEX_SMALL,
                self.font_scale,
                (0, 0, 255),
                self.label_thickness,
                cv2.LINE_AA
            )

            # Leyenda
            # legends = [
            #     ((0, 230, 0),   "Interior visible"),
            #     ((0, 140, 255), "Interior oculto"),
            #     ((220, 60, 0),  "Exterior estimado"),
            # ]
            # for i, (color, label) in enumerate(legends):
            #     y = 25 + i * 22
            #     cv2.circle(vis, (15, y), 6, color, -1)
            #     cv2.putText(vis, label, (26, y + 5),
            #                 cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1, cv2.LINE_AA)

        return vis

    def to_physical_coordinates(
        self,
        corners: np.ndarray,
        origin: "str | tuple[int, int]" = "tl",
        cell_size_mm: tuple[float, float] = (30.0, 30.0),
    ) -> np.ndarray | None:
        """Convierte la malla de esquinas en coordenadas físicas en milímetros.

        Args:
            corners (np.ndarray): Esquinas extrapoladas del tablero.
            origin (str | tuple[int, int], optional): Esquina de origen ("tl", "tr", "bl", "br").
            cell_size_mm (tuple[float, float], optional): Tamaño en milímetros de cada cuadro.

        Returns:
            np.ndarray | None: Matriz con coordenadas físicas o None.
        """
        if corners is None:
            return None

        rows, cols = corners.shape[:2]

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
