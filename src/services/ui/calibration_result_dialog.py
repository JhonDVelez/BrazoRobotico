"""
Modulo de dialogo de resultados de calibracion de camara.

Proporciona CalibrationResultDialog, un QDialog que muestra los
resultados numericos de la calibracion de la camara: matriz
intrinseca 3x3, coeficientes de distorsion y error de reproyeccion.
"""

import numpy as np
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QGridLayout, QPushButton
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt


class CalibrationResultDialog(QDialog):
    """Dialogo que muestra los resultados de la calibracion de la camara.

    Presenta la matriz intrinseca de la camara, los coeficientes de
    distorsion radial y el error de reproyeccion en un formato visual
    que simula los parentesis de matriz.

    Args:
        parent: Widget padre del dialogo.
        camera_matrix (np.ndarray): Matriz intrinseca 3x3.
        dist_coeffs (np.ndarray): Coeficientes de distorsion.
        reprojection_error (float): Error de reproyeccion RMS.
    """

    def __init__(self, parent, camera_matrix: np.ndarray, dist_coeffs: np.ndarray, reprojection_error: float):
        super().__init__(parent)
        self.setWindowTitle("Calibración Completada")
        self.setMinimumWidth(500)

        self._camera_matrix = camera_matrix
        self._dist_coeffs = dist_coeffs
        self._reprojection_error = reprojection_error

        self.__setup_ui()

    def __setup_ui(self):
        """Configura la interfaz de usuario del dialogo.

        Crea los elementos visuales: titulo de exito, error de
        reproyeccion, matriz de camara 3x3 con bordes de parentesis,
        coeficientes de distorsion y boton OK.
        """
        self.main_layout = QVBoxLayout(self)

        self.title_label = QLabel("✓ La calibración ha sido exitosa")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        self.title_label.setFont(title_font)
        self.main_layout.addWidget(self.title_label)

        self.error_label = QLabel(f"Error de reproyección: {self._reprojection_error:.4f}")
        self.main_layout.addWidget(self.error_label)

        self.matrix_title = QLabel("Matriz de Cámara (3×3):")
        matrix_title_font = QFont()
        matrix_title_font.setBold(True)
        self.matrix_title.setFont(matrix_title_font)
        self.main_layout.addWidget(self.matrix_title)

        self.matrix_grid = QGridLayout()
        self.matrix_grid.setSpacing(5)

        for i in range(3):
            for j in range(3):
                value = self._camera_matrix[i, j]
                label = QLabel(f"{value:.4f}")
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)

                style = "border: 1px solid black; padding: 8px; font-family: monospace; font-weight: bold;"

                if j == 0:
                    style += " border-right: 1px solid black;"
                elif j == 2:
                    style += " border-left: 1px solid black;"

                if i == 0 and j == 0:
                    style += " border-top-left-radius: 5px;"
                elif i == 0 and j == 2:
                    style += " border-top-right-radius: 5px;"
                elif i == 2 and j == 0:
                    style += " border-bottom-left-radius: 5px;"
                elif i == 2 and j == 2:
                    style += " border-bottom-right-radius: 5px;"

                label.setStyleSheet(style)
                self.matrix_grid.addWidget(label, i, j)

        self.main_layout.addLayout(self.matrix_grid)

        self.dist_title = QLabel("Coeficientes de Distorsión:")
        dist_title_font = QFont()
        dist_title_font.setBold(True)
        self.dist_title.setFont(dist_title_font)
        self.main_layout.addWidget(self.dist_title)

        dist_values = self._dist_coeffs.flatten()
        self.dist_label = QLabel(", ".join([f"{x:.6f}" for x in dist_values]))
        self.dist_label.setStyleSheet("font-family: monospace; border: 1px solid black; padding: 8px;")
        self.main_layout.addWidget(self.dist_label)

        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.main_layout.addWidget(self.ok_button)

    # Getters explicitos

    def get_camera_matrix(self):
        """Retorna la matriz intrinseca de la camara.

        Returns:
            np.ndarray: Matriz 3x3 de calibracion.
        """
        return self._camera_matrix

    def get_dist_coeffs(self):
        """Retorna los coeficientes de distorsion.

        Returns:
            np.ndarray: Coeficientes de distorsion.
        """
        return self._dist_coeffs

    def get_reprojection_error(self):
        """Retorna el error de reproyeccion RMS.

        Returns:
            float: Error de reproyeccion.
        """
        return self._reprojection_error
