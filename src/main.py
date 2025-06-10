"""Import the necessary modules
"""
import vision.camera_interface as camIn
# import config.settings as sett

if __name__ == '__main__':
    # Get a frame ang get the 2d plane coordinates
    frame = camIn.take_frame()
    camIn.get_coordinates(frame)
