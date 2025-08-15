import os
from PyQt6.QtWidgets import (QWidget, QSizePolicy)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QResizeEvent, QPixmap
from PyQt6 import uic
from .VideoWorker import VideoWorker  # Importar el worker thread


class VideoOverlayWidget(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.video_worker = None
        self.video_active = False
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        """ Configura la interfaz de usuario del widget de video
        """
        self.ui = uic.loadUi(os.path.join(os.path.dirname(__file__), 'cameraInterface.ui'), self)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(160, 120)
        
        self.videoLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.videoLabel.setScaledContents(False)
        self.videoLabel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        self.videoButton.setFixedSize(50, 30)
        self.videoButton.raise_()
        self.imagePath = os.path.join(os.path.dirname(__file__), "..", "img", 'camera.png')
        self.load_image(self.imagePath)
    
    def setup_connections(self):
        """Configura las conexiones de eventos
        """
        if hasattr(self.ui, 'videoButton'):
            self.videoButton.clicked.connect(self.toggle_video)
    
    def set_video_pixmap(self, pixmap: QPixmap):
        """ Método para establecer el pixmap del video en el label reescalado si es necesario.

        Args:
            pixmap (QPixmap): El pixmap del video a mostrar
        """
        if pixmap and not pixmap.isNull():
            # Cache del pixmap original para reescalado
            self._original_pixmap = pixmap
            
            # Escalar solo si es necesario
            label_size = self.videoLabel.size()
            if pixmap.size() != label_size:
                scaled_pixmap = pixmap.scaled(
                    label_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.FastTransformation 
                )
                self.videoLabel.setPixmap(scaled_pixmap)
            else:
                self.videoLabel.setPixmap(pixmap)
        else:
            self.videoLabel.clear()
            if hasattr(self, '_original_pixmap'):
                del self._original_pixmap
    
    def load_image(self, image_path: str):
        """ Carga una imagen desde la raiz del proyecto y la establece como pixmap en el label.

        Args:
            image_path (str): Ruta de la imagen a cargar
        """
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            self.set_video_pixmap(pixmap)
        else:
            print(f"Error: No se pudo cargar la imagen desde {image_path}")
    
    def on_frame_ready(self, pixmap: QPixmap):
        """ Slot para manejar el frame listo del worker thread.

        Args:
            pixmap (QPixmap): El pixmap del frame de video listo
        """
        if self.video_active:
            self.set_video_pixmap(pixmap)
    
    def on_video_error(self, error_message):
        """ Maneja errores del worker thread de video.

        Args:
            error_message (str): Mensaje de error recibido del worker thread
        """
        print(f"Error de video: {error_message}")
        self.stop_video()
    
    def start_video(self):
        """ Inicia la captura de video desde la cámara y configura el worker thread para recibir frames.
        """
        if self.video_worker is not None:
            self.stop_video()
        
        try:
            self.video_worker = VideoWorker(camera_index=0)
            
            # Conectar señales
            self.video_worker.frame_ready.connect(self.on_frame_ready)
            self.video_worker.error_occurred.connect(self.on_video_error)
            
            # Iniciar el hilo
            self.video_worker.start()
            self.video_active = True
            
        except Exception as e:
            print(f"Error al iniciar video: {e}")
            self.on_video_error(str(e))
    
    def stop_video(self):
        """ Detiene la captura de video
        """
        self.video_active = False  # Marcar como inactivo primero
        
        if self.video_worker is not None:
            try:
                # Desconectar señales ANTES de detener el worker
                self.video_worker.frame_ready.disconnect()
                self.video_worker.error_occurred.disconnect()
                
                self.video_worker.stop()
                self.video_worker.wait(3000)  # Esperar máximo 3 segundos
                self.video_worker.deleteLater()
                self.video_worker = None
            except Exception as e:
                print(f"Error deteniendo video: {e}")
        
        self.load_image(self.imagePath)
    
    def resizeEvent(self, event: QResizeEvent):
        """ Maneja el evento de redimensionamiento del widget.

        Args:
            event (QResizeEvent): Evento de redimensionamiento
        """
        super().resizeEvent(event)
        
        # Reescalar imagen actual si existe (de forma optimizada)
        if hasattr(self, '_original_pixmap'):
            if self.parent.cameraBox.isVisible():
                scaled_pixmap = self._original_pixmap.scaled(
                    self.videoLabel.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.FastTransformation
                )
                self.videoLabel.setPixmap(scaled_pixmap)
    
    def toggle_video(self):
        """ Alterna el estado de la captura de video.
        """
        if not self.parent.cameraBox.isVisible():
            return
        
        if self.video_active:
            self.stop_video()
        else:
            self.start_video()