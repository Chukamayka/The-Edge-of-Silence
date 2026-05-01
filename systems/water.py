import math
import pygame
from settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_FOG, COLOR_GRAY,
    COLOR_WATER_DEEP, COLOR_WATER_LIGHT, COLOR_WATER_HIGHLIGHT,
    WATER_WAVE_SPEED, WATER_WAVE_SCALE, VIGNETTE_STRENGTH,
)
from utils.helpers import lerp_color


class WaterRenderer:
    def __init__(self):
        self.time = 0

    def update(self, dt):
        self.time += dt

    def get_water_color(self, x, y, visibility):
        if visibility <= 0:
            return COLOR_FOG
        w1 = math.sin(x * 0.5 + y * 0.3 + self.time * WATER_WAVE_SPEED)
        w2 = math.sin(x * 0.3 - y * 0.5 + self.time * WATER_WAVE_SPEED * 0.7)
        w3 = math.sin((x + y) * 0.4 + self.time * WATER_WAVE_SPEED * 1.3)
        wv = ((w1 + w2 * 0.5 + w3 * 0.3) / 1.8 + 1) / 2

        if wv < 0.5:
            base = lerp_color(COLOR_WATER_DEEP, COLOR_WATER_LIGHT, wv * 2)
        else:
            base = lerp_color(
                COLOR_WATER_LIGHT, COLOR_WATER_HIGHLIGHT,
                (wv - 0.5) * 2 * WATER_WAVE_SCALE,
            )
        return (int(base[0] * visibility), int(base[1] * visibility), int(base[2] * visibility))

    def get_wall_color(self, x, y, visibility):
        if visibility <= 0:
            return COLOR_FOG
        w = math.sin(x * 0.3 + y * 0.3 + self.time * WATER_WAVE_SPEED * 0.5)
        g = int(COLOR_GRAY[0] * (1 + (w + 1) / 2 * 0.1))
        val = int(min(255, g) * visibility)
        return (val, val, val)


class Vignette:
    def __init__(self, width, height):
        self.surface = pygame.Surface((width, height), pygame.SRCALPHA)
        cx, cy = width // 2, height // 2
        max_dist = math.sqrt(cx ** 2 + cy ** 2)
        for y in range(0, height, 4):
            for x in range(0, width, 4):
                dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                t = max(0, (dist / max_dist - 0.5) / 0.5)
                alpha = int(t * 255 * VIGNETTE_STRENGTH)
                pygame.draw.rect(
                    self.surface, (0, 0, 0, max(0, min(255, alpha))), (x, y, 4, 4)
                )

    def draw(self, screen):
        screen.blit(self.surface, (0, 0))
