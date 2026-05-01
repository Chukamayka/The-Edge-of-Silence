from settings import CELL_SIZE, CAMERA_SMOOTHING
from utils.helpers import lerp


class Camera:
    def __init__(self, width, height):
        self.x = self.y = self.target_x = self.target_y = 0
        self.width, self.height = width, height

    def update(self, tx, ty, mw, mh):
        self.target_x = max(0, min(tx - self.width // 2, mw * CELL_SIZE - self.width))
        self.target_y = max(0, min(ty - self.height // 2, mh * CELL_SIZE - self.height))
        self.x = lerp(self.x, self.target_x, CAMERA_SMOOTHING)
        self.y = lerp(self.y, self.target_y, CAMERA_SMOOTHING)

    def apply(self, x, y):
        return x - self.x, y - self.y

    def set_position(self, x, y):
        self.x = self.target_x = x - self.width // 2
        self.y = self.target_y = y - self.height // 2