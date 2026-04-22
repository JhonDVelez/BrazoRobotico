import trace
import traceback
import cv2
import numpy as np
from PyQt6.QtCore import QRunnable
from data import config_manager as cfg


class ChArUcoDetection(QRunnable):
    """Clase separada para detección de tableros ChArUco.

    El detector mantiene datos precomputados para el tamaño de tablero
    proporcionado, evitando reconstrucciones innecesarias en cada frame.
    Utiliza el identificador de cada esquina detectada para calcular una
    homografía precisa y extrapolar la malla completa, incluso con oclusiones.
    """

    def __init__(self, frame, frame_id, detection_callback, error_callback):
        """Inicializa el detector de tableros ChArUco.
        """
        super().__init__()
        self.frame = frame.get().copy()
        self.frame_id = frame_id
        self.detection_callback = detection_callback
        self.error_callback = error_callback

        camera_config = cfg.load("camera.json")
        self.camera_matrix = np.array(camera_config.get("matrix"))
        self.dist_coeff = np.array(
            camera_config.get("distortion coefficients"))

        # Incializa los detectores para el codigo ArUco y almacena los de ChArUco
        dictionary_id = cv2.aruco.DICT_4X4_50
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(dictionary_id)
        self.charuco_board = cv2.aruco.CharucoBoard(
            size=(12, 5),
            squareLength=0.03,
            markerLength=0.022,
            dictionary=self.aruco_dict
        )
        self.charuco_detector = cv2.aruco.CharucoDetector(self.charuco_board)
        detector_params = cv2.aruco.DetectorParameters()
        self.aruco_detector = cv2.aruco.ArucoDetector(
            self.charuco_board.getDictionary(), detector_params)

    def run(self) -> None | dict:
        """Detecta las esquinas del tablero ChArUco en un frame.

        Convierte la imagen a escala de grises y utiliza el detector ChArUco.
        Si encuentra suficientes esquinas, cruza los IDs detectados con los 
        puntos ideales para calcular la homografía y extrapolar la malla 
        exterior.

        Returns:
            np.ndarray | None: Matriz de esquinas extrapoladas con forma 
            (rows + 2, cols + 2, 2) o None si falla la detección.
        """
        try:
            if self.frame is None:
                self.detection_callback(self.frame_id, None)
                return

            marker_corners, marker_ids, _ = self.aruco_detector.detectMarkers(
                self.frame)

            if marker_ids is None or len(marker_ids) < 6:
                self.detection_callback(self.frame_id,  None)
                return

            charuco_corners, charuco_ids, _, _ = self.charuco_detector.detectBoard(
                self.frame, markerCorners=marker_corners, markerIds=marker_ids
            )

            if charuco_corners is None or len(charuco_corners) < 4:
                self.detection_callback(self.frame_id, None)
                return

            # Homografía con los corners interiores visibles
            all_obj_points, all_img_points = self.charuco_board.matchImagePoints(
                charuco_corners, charuco_ids)

            if all_obj_points is None or all_img_points is None:
                self.detection_callback(self.frame_id, None)
                return

            obj_2d = all_obj_points[:, :2].astype(np.float32)
            img_2d = all_img_points[:, :].astype(np.float32)
            H, _ = cv2.findHomography(obj_2d, img_2d, cv2.RANSAC, 3.0)

            extrapolated_results = self.__extrapolate_corners(
                self.charuco_board, charuco_corners, charuco_ids, H)

            unified_results = self.build_unified_grid(extrapolated_results)

            _, rvec, tvec = cv2.solvePnP(
                all_obj_points,
                all_img_points,
                self.camera_matrix,
                self.dist_coeff,
                flags=cv2.SOLVEPNP_ITERATIVE
            )

            unified_results.update({"rvec": rvec, "tvec": tvec})

            self.detection_callback(
                self.frame_id, self.to_physical_coordinates(unified_results))
        except Exception:
            self.error_callback(
                f"Error al detectar el tablero: {traceback.format_exc()} (ChArUcoDetector)")

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

        id_to_corner = {
            int(cid): charuco_corners[i]
            for i, cid in enumerate(charuco_ids.flatten())
        }

        for idx in range(cols * rows):
            row = idx // cols
            col = idx % cols
            pt = projected_all[idx]

            is_interior = (col, row) in interior_set

            if is_interior:
                # ID en el sistema ChArUco (fila-1, col-1 dentro de interiores)
                charuco_id = (row - 1) * (cols - 2) + (col - 1)
                if charuco_id in id_to_corner:
                    interior_corners.append(id_to_corner[charuco_id])
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
            "charuco_corners":          charuco_corners,
            "charuco_ids":              charuco_ids,
            "visible_corners":          interior_corners,
            "visible_ids":              interior_ids,
            "estimated_interior":       estimated_interior,
            "estimated_interior_ids":   estimated_interior_ids,
            "exterior_corners":         exterior_corners,
            "exterior_ids":             exterior_ids,
            "homography":               H,
            "grid_shape":               (cols, rows),
            "board":                    self.charuco_board,
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

        cols = size[0] + 1
        rows = size[1] + 1

        points = []
        for row in range(rows):
            for col in range(cols):
                points.append([col * square_length, row * square_length, 0.0])

        return np.array(points, dtype=np.float32), cols, rows

    def build_unified_grid(self, results: dict):
        """
        Unifica todos los corners en una grilla ordenada de (cols × rows) puntos.
        new_id = row * cols + col  →  0 en esquina superior izquierda,
                                    aumenta →, luego baja una fila y repite.
        """
        shape = None
        if results is not None and "grid_shape" in results:
            shape = results["grid_shape"]

        if shape is None:
            return None
        cols, rows = shape
        inner_cols = cols - 2

        grid = {}

        # 1. Interiores visibles
        for corner, cid in zip(results["visible_corners"], results["visible_ids"]):
            col = cid % inner_cols + 1
            row = cid // inner_cols + 1
            grid[(col, row)] = corner[0]   # shape (2,)

        # 2. Interiores estimados (ocultos)
        for corner, cid in zip(results["estimated_interior"], results["estimated_interior_ids"]):
            col = cid % inner_cols + 1
            row = cid // inner_cols + 1
            grid[(col, row)] = corner[0]   # shape (2,)

        # 3. Exteriores
        for corner, (col, row) in zip(results["exterior_corners"], results["exterior_ids"]):
            grid[(col, row)] = corner[0]   # shape (2,)

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
        r = results.copy()
        tl = unified_corners[0]
        tr = np.array(unified_corners[cols - 1])
        bl = unified_corners[cols * (rows - 1)]
        br = unified_corners[(cols * rows) - 1]

        corners = np.array([tl, tr, br, bl])
        center = corners.mean(axis=0)

        # Expandir cada punto un 10% alejándolo del centro
        scale = 1.10
        expanded_corners = []
        for point in corners:
            direction = point - center          # Vector desde el centro al punto
            expanded = center + direction * scale  # Mover 10% más lejos
            expanded_corners.append(expanded)

        mask = np.array(expanded_corners, dtype=np.int32).reshape((-1, 1, 2))

        r.update({"unified_corners": unified_corners,
                  "unified_ids": unified_ids,
                  "roi": mask
                  })
        return r

    def to_physical_coordinates(
        self,
        results: dict,
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
        shape = None
        if results is not None and "grid_shape" in results:
            shape = results["grid_shape"]

        if shape is None:
            return None
        cols, rows = shape

        corners = results["unified_corners"].reshape(
            rows, cols, 2)
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
        r = results.copy()
        r.update({"physical_corners": coords
                  })
        return r
