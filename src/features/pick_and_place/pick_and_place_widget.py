"""
Modulo que define el overlay de interaccion para el modo Pick and Place.

Este modulo contiene la clase PickAndPlaceOverlay, un widget transparente
que se superpone a la camara para gestionar la seleccion de objetos.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QWidget, QPushButton


class PickAndPlaceWidget(QWidget):
    """
    Widget transparente que se superpone a la camara para detectar clics.

    Attributes:
        sphere_selected (pyqtSignal): Emite el color de la esfera confirmada.
    """
    sphere_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)

        # Referencia a la geometria original de la camara para mapeo
        self.orig_w = 1280
        self.orig_h = 720
        self.detected_circles_2d = {}
        self._selected_color = None

        self.__setup_ui()
        self.hide()

    def __setup_ui(self):
        """Configura el boton de confirmacion."""
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

    def update_config(self, orig_w, orig_h):
        """Actualiza la resolucion original de la camara."""
        self.orig_w = orig_w
        self.orig_h = orig_h

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

    def _hide_confirm_button(self):
        self.confirm_button.hide()
        self._selected_color = None

    def _on_confirm_clicked(self):
        if self._selected_color:
            self.sphere_selected.emit(self._selected_color)
            self._hide_confirm_button()

    def hideEvent(self, event):
        """Limpia la seleccion temporal al desactivar el modo."""
        self._hide_confirm_button()
        super().hideEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.confirm_button.isVisible():
            self._position_confirm_button()
