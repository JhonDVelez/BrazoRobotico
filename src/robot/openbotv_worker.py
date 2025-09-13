from PyQt6.QtCore import QThread


class robotWorker(QThread):
    def __init__(self):
        super().__init__()

    def send_data(self):
        pass
