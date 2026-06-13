"""
Modulo que define el overlay de interaccion para el modo Pick and Place.

Este modulo contiene la clase PickAndPlaceOverlay, un widget transparente
que se superpone a la camara para gestionar la seleccion de objetos.
"""

from PyQt6.QtCore import Qt, pyqtSignal, QPointF
from PyQt6.QtWidgets import QWidget, QPushButton
from PyQt6.QtGui import QPainter, QPen, QColor, QIcon
import numpy as np
import cv2
from src.services.vision.geometry_utils import pixel_to_board_coordinates


class PickAndPlaceWidget(QWidget):
    """
    Widget transparente que se superpone a la camara para detectar clics.

    Attributes:
        sphere_selected (pyqtSignal): Emite el color de la esfera confirmada.
        place_requested (pyqtSignal): Emite las coordenadas {x, y, z} de destino.
        mode_changed (pyqtSignal): Emite el nuevo modo ('pick' o 'place').
    """
    sphere_selected = pyqtSignal(str)
    place_requested = pyqtSignal(dict)
    mode_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)

        # Referencia a la geometria original de la camara para mapeo
        self.orig_w = 1280
        self.orig_h = 720
        self.detected_circles_2d = {}
        self._selected_color = None
        self._selected_place = None  # {x, y, z}
        self._mode = 'pick'  # 'pick' o 'place'
        self._charuco_pose = None  # {rvec, tvec, camera_matrix, dist_coeffs}
        self._custom_origin = np.array([180.0, 0.0, 0.0]).reshape(3, 1)

        self.__setup_ui()
        self.hide()

    def __setup_ui(self):
        """Configura los botones de confirmacion y reset."""
        self.confirm_button = QPushButton("Confirmar", self)
        self.confirm_button.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: white;
                border: 2px solid #555555;
                border-radius: 12px;
                padding: 6px 20px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
        """)
        self.confirm_button.setFixedHeight(32)
        self.confirm_button.hide()
        self.confirm_button.clicked.connect(self._on_confirm_clicked)

        # Boton de reset (regresar a modo pick)
        self.reset_button = QPushButton(self)
        self.reset_button.setFixedSize(30, 30)
        self.reset_button.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #F0F0F0;
            }
        """)
        self.reset_button.setIcon(QIcon('icons:refresh_l.png'))
        self.reset_button.hide()
        self.reset_button.clicked.connect(self._on_reset_clicked)

    def set_mode(self, mode):
        """Cambia el modo de interaccion y limpia la seleccion actual."""
        if mode not in ('pick', 'place'):
            return
        self._mode = mode
        self._selected_color = None
        self._selected_place = None
        self._hide_confirm_button()

        if mode == 'place':
            self.reset_button.show()
        else:
            self.reset_button.hide()

        self.mode_changed.emit(mode)
        self.update()

    def _on_reset_clicked(self):
        self.set_mode('pick')

    def update_config(self, orig_w, orig_h, custom_origin=None):
        """Actualiza la resolucion y el origen personalizado."""
        self.orig_w = orig_w
        self.orig_h = orig_h
        if custom_origin is not None:
            self._custom_origin = np.array(custom_origin).reshape(3, 1)
        else:
            self._custom_origin = np.array([180.0, 0.0, 0.0]).reshape(3, 1)

    def paintEvent(self, event):
        """Dibuja indicadores visuales (como la X en modo Place)."""
        super().paintEvent(event)
        if self._mode == 'place' and self._selected_place and self._charuco_pose:
            self._draw_selection_x()

    def _draw_selection_x(self):
        """Dibuja una X sobre la posicion snapped seleccionada."""
        if not self._charuco_pose:
            return

        # Verificar que tengamos todos los datos necesarios para proyectar
        required = ['rvec', 'tvec', 'camera_matrix', 'dist_coeffs']
        if not all(k in self._charuco_pose and self._charuco_pose[k] is not None for k in required):
            return

        # 1. Convertir de espacio robot a espacio tablero
        p_robot = np.array([
            self._selected_place['x'],
            self._selected_place['y'],
            self._selected_place['z']
        ]).reshape(3, 1)

        p_board = p_robot + self._custom_origin

        # 2. Proyectar de tablero a imagen
        img_points, _ = cv2.projectPoints(
            p_board.reshape(1, 1, 3),
            self._charuco_pose['rvec'],
            self._charuco_pose['tvec'],
            self._charuco_pose['camera_matrix'],
            self._charuco_pose['dist_coeffs']
        )

        orig_x, orig_y = img_points.flatten()

        # 3. Mapear de imagen original a coordenadas de este widget
        camera_widget = self.parent()
        if not hasattr(camera_widget, "get_pixmap_geometry"):
            return

        mapping = camera_widget.get_pixmap_geometry()
        if mapping[0] is None:
            return

        x_off, y_off, disp_w, disp_h, pixmap_w, pixmap_h = mapping
        scale_x = pixmap_w / self.orig_w
        scale_y = pixmap_h / self.orig_h

        ui_x = orig_x * scale_x + x_off
        ui_y = orig_y * scale_y + y_off

        # 4. Dibujar
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(255, 0, 0), 3)
        painter.setPen(pen)

        size = 10
        painter.drawLine(int(ui_x - size), int(ui_y - size),
                         int(ui_x + size), int(ui_y + size))
        painter.drawLine(int(ui_x - size), int(ui_y + size),
                         int(ui_x + size), int(ui_y - size))

    def update_detected_circles(self, circles_2d: dict):
        """Actualiza los datos de las esferas detectadas en 2D."""
        self.detected_circles_2d = circles_2d

    def mousePressEvent(self, event):
        """
        Detecta clics sobre la imagen de camara cuando Pick and Place esta activo.

        El overlay consulta al `CameraWidget` padre para mapear coordenadas de UI
        a coordenadas originales de imagen, sin acoplar la camara a este feature.
        """
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        camera_widget = self.parent()
        if not hasattr(camera_widget, "get_pixmap_geometry"):
            return

        mapping = camera_widget.get_pixmap_geometry()
        self._handle_click_with_mapping(event.position(), mapping)

    def _handle_click_with_mapping(self, pos, mapping):
        """
        Busca una esfera cercana al clic usando la geometria visible del pixmap.
        """
        if mapping[0] is None:
            self._hide_confirm_button()
            return

        x_off, y_off, disp_w, disp_h, pixmap_w, pixmap_h = mapping
        img_x = pos.x() - x_off
        img_y = pos.y() - y_off

        if img_x < 0 or img_y < 0 or img_x > disp_w or img_y > disp_h:
            self._hide_confirm_button()
            return

        scale_x = self.orig_w / pixmap_w
        scale_y = self.orig_h / pixmap_h
        orig_x = img_x * scale_x
        orig_y = img_y * scale_y

        if self._mode == 'pick':
            hit_color = self._find_nearest_circle(orig_x, orig_y)
            if hit_color:
                self._selected_color = hit_color
                self.confirm_button.setText(hit_color.capitalize())
                self.confirm_button.adjustSize()
                self._position_confirm_button()
                self.confirm_button.show()
                self.confirm_button.raise_()
            else:
                self._hide_confirm_button()
        else:
            self._handle_place_click(orig_x, orig_y)

    def _handle_place_click(self, x, y):
        """Calcula la posicion 3D en el tablero y aplica snapping."""
        if not self._charuco_pose:
            return

        # Verificar datos de calibracion y pose
        required = ['rvec', 'tvec', 'camera_matrix', 'dist_coeffs']
        if not all(k in self._charuco_pose and self._charuco_pose[k] is not None for k in required):
            print(
                "[PickPlace] Error: Faltan datos de pose o camara para calcular coordenadas")
            return

        # 1. Proyectar pixel a coordenadas del tablero (z=0)
        p_board = pixel_to_board_coordinates(
            (x, y),
            self._charuco_pose['rvec'],
            self._charuco_pose['tvec'],
            self._charuco_pose['camera_matrix'],
            self._charuco_pose['dist_coeffs'],
            (self.orig_w, self.orig_h),
            plane_z=0
        )

        if p_board is None:
            return

        # 2. Aplicar offset del origen personalizado
        p_final = p_board - self._custom_origin

        fx, fy, fz = p_final.flatten()

        # 3. Snapping a la rejilla de 30mm
        snap_x = round(fx / 30.0) * 30.0
        snap_y = round(fy / 30.0) * 30.0

        self._selected_place = {'x': snap_x, 'y': snap_y, 'z': 0.0}

        self.confirm_button.setText(f"Ir a ({int(snap_x)}, {int(snap_y)})")
        self.confirm_button.adjustSize()
        self._position_confirm_button()
        self.confirm_button.show()
        self.confirm_button.raise_()
        self.update()

    def _find_nearest_circle(self, x, y):
        best_color = None
        best_dist = 40.0
        for color, data in self.detected_circles_2d.items():
            cx, cy = data.get("center", (0, 0))
            radius = data.get("radius", 20)
            dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            if dist < best_dist or dist < radius * 1.5:
                best_dist = dist
                best_color = color
        return best_color

    def _position_confirm_button(self):
        cw = self.confirm_button.width()
        btn_x = max(0, (self.width() - cw) // 2)
        btn_y = self.height() - 50
        self.confirm_button.move(btn_x, btn_y)

        # Posicionar reset button en esquina inferior izquierda
        self.reset_button.move(10, self.height() - 40)

    def _hide_confirm_button(self):
        self.confirm_button.hide()
        self._selected_color = None

    def _on_confirm_clicked(self):
        if self._mode == 'pick' and self._selected_color:
            self.sphere_selected.emit(self._selected_color)
            self._hide_confirm_button()
        elif self._mode == 'place' and self._selected_place:
            self.place_requested.emit(self._selected_place)
            self._hide_confirm_button()
            self.reset_button.hide()  # Ocultar durante el proceso de place

    def hideEvent(self, event):
        """Limpia la seleccion temporal al desactivar el modo."""
        self._hide_confirm_button()
        super().hideEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.confirm_button.isVisible():
            self._position_confirm_button()
