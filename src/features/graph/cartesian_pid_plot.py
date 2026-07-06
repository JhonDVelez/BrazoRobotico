"""
Modulo que define el widget de grafico cartesiano basado en matplotlib.

Proporciona la clase CartesianPIDPlot, un widget Qt que embebe una figura
matplotlib con tres subplots (X, Y, Z) para visualizar la convergencia
del control PID cartesiano en tiempo real, mostrando el valor real vs el
objetivo (target) por iteracion.

Estilo configurado para formato de tesis (fuente serif, colores sobrios,
tamanos definidos).
"""

import matplotlib
matplotlib.use("QtAgg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
from PyQt6.QtWidgets import QWidget, QVBoxLayout

plt.ioff()

# ==========================================================================
# CONFIGURACION ESTETICA Y FORMATO PARA LA TESIS (MODIFICABLE)
# ==========================================================================
TAMANO_TITULO = 14
TAMANO_ETIQUETAS_EJES = 11
TAMANO_NUMEROS_EJES = 10
TAMANO_LEYENDA = 10

GROSOR_LINEA = 2.0
TAMANO_MARCADOR = 4
GROSOR_LINEA_TARGET = 1.5

COLORES_REALES = ["#FF0000", "#026807", "#02488D"]
COLORES_TARGET = ["#000000", "#000000", "#000000"]

plt.rcParams.update({
    "font.family": "serif",
    "font.size": TAMANO_NUMEROS_EJES
})

ETIQUETAS = ["X", "Y", "Z"]
TITULO_SUPERIOR = "PID eje X,Z y P eje Y — Seguimiento en Tiempo Real"


class CartesianPIDPlot(QWidget):
    """
    Widget que grafica la convergencia del PID cartesiano en tiempo real.

    Mantiene tres subplots (X, Y, Z) con dos series cada uno:
    - Linea solida con marcadores: posicion real del robot.
    - Linea discontinua negra: posicion objetivo (target).

    Se reinicia en cada nueva ejecucion de `execute_target`.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._real_data = [[] for _ in range(3)]
        self._target_data = [[] for _ in range(3)]

        self._setup_figure()
        self._setup_canvas()

    def _setup_figure(self):
        self.figure, self.axes = plt.subplots(3, 1, figsize=(8, 10), sharex=True)
        self.figure.suptitle(TITULO_SUPERIOR, fontsize=TAMANO_TITULO)
        self._lines_reales = []
        self._lines_targets = []

        for i, ax in enumerate(self.axes):
            line_real, = ax.plot(
                [], [],
                color=COLORES_REALES[i],
                linewidth=GROSOR_LINEA,
                marker="o",
                linestyle="-",
                markersize=TAMANO_MARCADOR,
                label=f"{ETIQUETAS[i]} Real"
            )
            line_target, = ax.plot(
                [], [],
                color=COLORES_TARGET[i],
                linestyle="--",
                linewidth=GROSOR_LINEA_TARGET,
                label=f"{ETIQUETAS[i]} Target"
            )

            ax.set_ylabel(f"{ETIQUETAS[i]} (mm)", fontsize=TAMANO_ETIQUETAS_EJES)
            ax.tick_params(axis="both", labelsize=TAMANO_NUMEROS_EJES)
            ax.grid(True, alpha=0.3)
            ax.legend(loc="lower right", fontsize=TAMANO_LEYENDA)

            self._lines_reales.append(line_real)
            self._lines_targets.append(line_target)

        self.axes[-1].set_xlabel("Iteración Total", fontsize=TAMANO_ETIQUETAS_EJES)
        self.figure.tight_layout(rect=[0, 0, 1, 0.97])

    def _setup_canvas(self):
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)

    def reset_plot(self, target_xyz):
        """
        Limpia los datos acumulados y prepara el grafico para un nuevo movimiento.

        Args:
            target_xyz (list): Coordenadas [x, y, z] del objetivo.
        """
        for i in range(3):
            self._real_data[i].clear()
            self._target_data[i].clear()

        for i, ax in enumerate(self.axes):
            self._lines_reales[i].set_data([], [])
            self._lines_targets[i].set_data([], [])
            ax.relim()
            ax.autoscale_view()

        self._target_xyz = list(target_xyz)
        self._redraw()

    def append_data(self, iteration, actual_xyz, target_xyz):
        """
        Agrega un punto de datos y actualiza el grafico.

        Args:
            iteration (int): Numero de iteracion actual del PID.
            actual_xyz (list): Posicion real [x, y, z] en mm.
            target_xyz (list): Posicion objetivo [x, y, z] en mm.
        """
        for i in range(3):
            self._real_data[i].append(actual_xyz[i])
            self._target_data[i].append(target_xyz[i])

        self._redraw()

    def _redraw(self):
        n = len(self._real_data[0])
        if n == 0:
            return

        x_vals = list(range(n))

        for i, ax in enumerate(self.axes):
            self._lines_reales[i].set_data(x_vals, self._real_data[i])
            self._lines_targets[i].set_data(x_vals, self._target_data[i])

            all_y = self._real_data[i] + self._target_data[i]
            y_min, y_max = min(all_y), max(all_y)
            margin = max((y_max - y_min) * 0.15, 5.0)
            ax.set_xlim(-0.5, max(n - 1 + 0.5, 4.5))
            ax.set_ylim(y_min - margin, y_max + margin)

        self.canvas.draw_idle()
