import numpy as np
import cv2
from data import config_manager as cfg
from vision.circle_estimation import CircleEstimation


class PoseEstimation:
    def __init__(self) -> None:
        self.prev_circles = None
        self.mask_corners = None
        self.show_mask = False
        self.show_circles = True
        self.show_mask_contour = True

        self.circle_estimator = CircleEstimation()

    def set_sphere_radius(self, radius_mm: float) -> None:
        self.sphere_radius_mm = float(radius_mm)

    def set_board_cell_size(self, cell_size_mm: float) -> None:
        self.board_cell_size_mm = float(cell_size_mm)

    def get_sphere_pose(self, original_frame, drawn_frame, processed_frame, chessboard_corners, mask_corners):
        umat_frame = cv2.UMat(original_frame)
        circles_estimated = self.circle_estimator.get_circle_center(
            original_frame, umat_frame)

        return drawn_frame
