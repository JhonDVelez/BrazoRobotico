from pathlib import Path
from PyQt6.QtCore import pyqtSignal, QObject, Qt
import pyqtgraph as pg
import qdarktheme
import qdarktheme.dist
import qdarktheme.dist.dark
import qdarktheme.dist.dark.stylesheet
import qdarktheme.dist.light
import qdarktheme.dist.light.stylesheet
from .theme_stylesheet import dark_style, light_style


class MainThemeMixin:
    """ Mixin donde se gestionan los temas, colores, cambio entre claro y oscuro tanto de forma
        manual con el botón o de forma automática con el tema de windows.
        Centraliza la coherencia visual de todos los componentes de la interfaz.
    """
    # Señal para notificar a otros componentes que el tema ha cambiado
    theme_change = pyqtSignal(str)
    # Almacena el estado actual del esquema de colores
    actual_theme = None

    def update_theme(self, scheme: Qt.ColorScheme):
        """ Se ejecuta cada vez que cambia el tema del sistema operativo.
            Permite que la aplicación reaccione nativamente a los ajustes del usuario en Windows/Linux/macOS.
        """
        if scheme == Qt.ColorScheme.Dark:
            self.load_dark_theme()
        elif scheme == Qt.ColorScheme.Light:
            self.load_light_theme()
        else:
            # Fallback en caso de esquemas de color no definidos o híbridos
            print("Error: Tema desconocido")

    def toggle_theme_event(self):
        """ Maneja el evento de alternancia manual de tema disparado por el usuario.
            Utiliza el ThemeManager para propagar el cambio a través de señales.
        """
        if self.actual_theme == Qt.ColorScheme.Dark:
            # Cambia a modo claro
            self.theme_manager.emit_theme_change(False)
            self.actual_theme = Qt.ColorScheme.Light
        elif self.actual_theme == Qt.ColorScheme.Light:
            # Cambia a modo oscuro
            self.theme_manager.emit_theme_change(True)
            self.actual_theme = Qt.ColorScheme.Dark

        # Aplica los cambios visuales correspondientes al esquema seleccionado
        self.update_theme(self.actual_theme)

    def load_dark_theme(self):
        """ Aplica y personaliza las modificaciones para el tema oscuro.
            Sobrescribe estilos base de qdarktheme e inyecta recursos específicos para modo noche.
        """
        # Configuración del estilo base oscuro
        qdarktheme.dist.dark.stylesheet.STYLE_SHEET = dark_style
        stylesheet = qdarktheme.load_stylesheet("dark")
        
        # Localización dinámica de recursos SVG para componentes personalizados (RadioButtons)
        svg_path = (Path(__file__).resolve().parent.parent.parent.parent /
                    "src/gui/main_window/theme_stylesheet/svg/radio_button_checked_r.svg").as_posix()
        
        # Inyección de QSS para iconos de indicadores de estado
        stylesheet += f"""
        QRadioButton::indicator:checked {{
            image: url("{svg_path}");
        }}"""
        
        self.setStyleSheet(stylesheet)
        
        # --- Estilización de la Barra de Título Personalizada ---
        self.title_bar.title_label.setStyleSheet(
            """background-color: rgba(42.000, 43.000, 46.000, 1.000); color: #ffffff;""")
        self.title_bar.left_container.setStyleSheet(
            """background-color: rgba(42.000, 43.000, 46.000, 1.000); border-radius: 0px""")
        self.title_bar.buttons_frame.setStyleSheet("""
            QWidget {background-color: rgba(42.000, 43.000, 46.000, 1.000); border-radius: 0px;}
            QToolButton {border: none; background: transparent;}
            QToolButton:hover {background-color: rgba(68.000, 70.000, 74.000, 1.000);}
            QToolButton:pressed {background-color: rgba(79.000, 80.000, 84.000, 1.000);}
            """)
        
        # Actualización de iconos y fondo de gráficos para mantener el contraste
        self.logo_label.setPixmap(self.laser_w)
        self.theme_action.setIcon(self.sun_icon)
        
        # Sincronización del fondo de los widgets de PyQtGraph
        self.graph_interface.sim_graph_object.graph_widget.setBackground(
            pg.mkColor((32, 33, 36)))
        self.graph_interface.phy_graph_object.graph_widget.setBackground(
            pg.mkColor((32, 33, 36)))

    def load_light_theme(self):
        """ Aplica y personaliza las modificaciones para el tema claro.
            Ajusta la paleta de colores a tonos claros, optimizando la visibilidad.
        """
        # Configuración del estilo base claro
        qdarktheme.dist.light.stylesheet.STYLE_SHEET = light_style
        stylesheet = qdarktheme.load_stylesheet("light")
        
        # Localización de iconos para el modo claro (ej. indicadores en azul o negro)
        svg_path = (Path(__file__).resolve().parent.parent.parent.parent /
                    "src/gui/main_window/theme_stylesheet/svg/radio_button_checked_b.svg").as_posix()
        
        stylesheet += f"""
        QRadioButton::indicator:checked {{
            image: url("{svg_path}");
        }}"""
        
        self.setStyleSheet(stylesheet)
        
        # --- Estilización de la Barra de Título (Colores claros) ---
        self.title_bar.title_label.setStyleSheet(
            """QLabel {color: #000000;}""")
        self.title_bar.title_label.setStyleSheet(
            """background-color: rgba(223.000, 225.000, 229.000, 1.000); color: #000000;""")
        self.title_bar.left_container.setStyleSheet(
            """background-color: rgba(223.000, 225.000, 229.000, 1.000); border-radius: 0px""")
        self.title_bar.buttons_frame.setStyleSheet("""
            QWidget {background-color: rgba(223.000, 225.000, 229.000, 1.000); border-radius: 0px;}
            QToolButton {border: none; background: transparent;}
            QToolButton:hover {background-color: rgba(215.000, 215.000, 215.000, 1.000);}
            QToolButton:pressed {background-color: rgba(196.000, 196.000, 196.000, 1.000);}
            """)
        
        # Intercambio de recursos visuales para modo claro
        self.logo_label.setPixmap(self.laser_b)
        self.theme_action.setIcon(self.moon_icon)
        
        # Ajuste de los widgets de telemetría a fondo claro
        self.graph_interface.sim_graph_object.graph_widget.setBackground(
            pg.mkColor((248, 249, 250)))
        self.graph_interface.phy_graph_object.graph_widget.setBackground(
            pg.mkColor((248, 249, 250)))


class ThemeManager(QObject):
    """ Gestor de tema encargado de producir la señal necesaria para cambiar de colores y de 
        imágenes según se necesite. 
        Implementa el patrón Singleton para asegurar una única fuente de verdad sobre el tema.
    """
    theme_changed = pyqtSignal(bool)
    _instance = None

    @classmethod
    def get_instance(cls):
        """ Proporciona acceso global a la instancia única del gestor de temas.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def emit_theme_change(self, dark_t: bool):
        """ Emite la señal de cambio de tema a todos los suscriptores interesados.
            True para oscuro, False para claro.
        """
        self.theme_changed.emit(dark_t)