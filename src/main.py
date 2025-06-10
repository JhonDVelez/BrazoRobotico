"""Importa las librerias y modulos necesarios
"""
import vision.camera_interface as camIn
# import config.settings as sett

if __name__ == '__main__':
    # Obtiene la imagen de la camara
    frame = camIn.take_frame()
    camIn.get_coordinates(frame)
