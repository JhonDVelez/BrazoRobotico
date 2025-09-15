import qdarktheme


class MainTheme:
    def __init__(self):
        self.dark_theme = True

    def toggle_theme_event(self):
        if self.dark_theme:
            self.load_light_theme()
            self.dark_theme = False
            if hasattr(self, 'theme_menu'):
                self.theme_menu.setIcon(self.moon_icon)
        else:
            self.load_dark_theme()
            self.dark_theme = True
            if hasattr(self, 'theme_menu'):
                self.theme_menu.setIcon(self.sun_icon)

    def load_dark_theme(self):
        stylesheet = qdarktheme.load_stylesheet("dark")
        replacements = {
            "rgba(138.000, 180.000, 247.000, 1.000)": "rgba(241.000, 57.000, 47.000, 1.000)",
            "rgba(127.000, 166.000, 228.000, 1.000)": "rgba(238.000, 74.000, 65.000, 1.000)",
            "rgba(54.000, 86.000, 140.000, 1.000)": "rgba(129.000, 39.000, 36.000, 1.000)",
            "rgba(30.000, 43.000, 60.000, 1.000)": "rgba(60.000, 32.000, 30.000, 1.000)",
            "rgba(46.000, 70.000, 94.000, 1.000)": "rgba(121.000, 56.000, 53.000, 1.000)",

            """
QPushButton {
    border: 1px solid rgba(63.000, 64.000, 66.000, 1.000);
    padding: 4px 8px;
    border-radius: 4px;
    color: rgba(241.000, 57.000, 47.000, 1.000);
}""":
            """
QPushButton {
    border: 1px solid rgba(63.000, 64.000, 66.000, 1.000);
    padding: 4px 8px;
    border-radius: 4px;
    color: rgba(255.000, 255.000, 255.000, 1.000);
}""",

            """
QSplitter::handle {
    background-color: rgba(63.000, 64.000, 66.000, 1.000);
    margin: 1px 3px;
}
QSplitter::handle:hover {
    background-color: rgba(241.000, 57.000, 47.000, 1.000);
}""":
            """
QSplitter::handle {
    min-width: 16px;
    min-height: 16px;
    border-radius: 8px;

    background: qradialgradient(
        cx: 0.5, cy: 0.5, radius: 0.5,
        fx: 0.5, fy: 0.5,
        stop:0 rgba(241.000, 57.000, 47.000, 0.400),
        stop:1 rgba(0, 0, 0, 0.0)
    );
}
QSplitter::handle:hover {
    min-width: 16px;
    min-height: 16px;
    border-radius: 8px;

    background: qradialgradient(
        cx: 0.5, cy: 0.5, radius: 0.55,
        fx: 0.5, fy: 0.5,
        stop:0 rgba(241.000, 57.000, 47.000, 0.800),
        stop:1 rgba(0, 0, 0, 0.0)
    );
}""",
            """
QMenuBar {
    background-color: rgba(32.000, 33.000, 36.000, 1.000);
    padding: 2px;
    border-bottom: 1px solid rgba(63.000, 64.000, 66.000, 1.000);
}""":
            """
QMenuBar {
    background-color: transparent;
    padding: 5px 5px 5px 5px;
    border-bottom: transparent;
}""",
            """
QToolBar > QToolButton {
    background-color: transparent;
    padding: 3px;
    border-radius: 4px;
}""":
            """
QToolButton {
    background-color: transparent;
    padding: 3px;
    border-radius: 4px;
}
"""
        }
        for old, new in replacements.items():
            stylesheet = stylesheet.replace(old, new)

        # # Estilos para barra de título personalizada
        # custom_styles = """
        # CustomTitleBar {
        #     background-color:  # 2b2b2b;
        #     border-bottom: 1px solid  # 555;
        # }
        # CustomTitleBar QLabel {
        #     color: white;
        #     font-weight: bold;
        #     font-size: 14px;
        # }
        # CustomTitleBar QToolButton {
        #     color: white;
        #     border: none;
        #     font-weight: bold;
        #     font-size: 12px;
        #     padding: 4px 8px;
        #     margin: 1px;
        #     border-radius: 3px;
        # }
        # CustomTitleBar QToolButton: hover {
        #     background-color: rgba(255, 255, 255, 0.2);
        # }
        # CustomTitleBar QToolButton  # close_button:hover {
        #     background-color:  # e81123;
        # }
        # """
        # stylesheet += custom_styles
        self.setStyleSheet(stylesheet)

    def load_light_theme(self):
        stylesheet = qdarktheme.load_stylesheet("light")
        stylesheet = stylesheet.replace("rgba(0.000, 129.000, 219.000, 1.000)",
                                        "rgba(241.000, 57.000, 47.000, 1.000)")

        # Estilos para barra de título en tema claro
        custom_styles = """
        CustomTitleBar {
            background-color:  # f0f0f0;
            border-bottom: 1px solid  # ccc;
        }
        CustomTitleBar QLabel {
            color:  # 333;
            font-weight: bold;
            font-size: 14px;
        }
        CustomTitleBar QToolButton {
            color:  # 333;
            border: none;
            font-weight: bold;
            font-size: 12px;
            padding: 4px 8px;
            margin: 1px;
            border-radius: 3px;
        }
        CustomTitleBar QToolButton: hover {
            background-color: rgba(0, 0, 0, 0.1);
        }
        CustomTitleBar QToolButton  # close_button:hover {
            background-color:  # e81123;
            color: white;
        }
        """
        stylesheet += custom_styles
        self.setStyleSheet(stylesheet)
