import math
import pygame
from settings import (
    CELL_SIZE,
    RIPPLE_SPEED, RIPPLE_COUNT, RIPPLE_INTERVAL, RIPPLE_SEGMENTS, RIPPLE_THICKNESS,
    COLOR_RIPPLE,
)
from utils.helpers import raycast, line_of_sight


class Ripple:
    """Рябь от камня — невидима пока не коснётся игрока"""

    def __init__(self, x, y, max_radius, delay=0, lit=False):
        self.x, self.y = x, y
        self.radius = 0
        self.max_radius = max_radius
        self.delay = delay
        self.active = False
        self.lit = lit
        self.finished = False
        self.wall_distances = []
        self.distances_calculated = False

    def update(self, dt, maze=None):
        if self.finished:
            return
        if self.delay > 0:
            self.delay -= dt
            return
        self.active = True
        self.radius += RIPPLE_SPEED * dt

        if not self.distances_calculated and maze:
            self.wall_distances = [
                raycast(
                    self.x, self.y,
                    (2 * math.pi * i) / RIPPLE_SEGMENTS,
                    self.max_radius, maze,
                )
                for i in range(RIPPLE_SEGMENTS)
            ]
            self.distances_calculated = True

        if self.radius >= self.max_radius:
            self.finished = True

    def check_player_contact(self, px, py, pr, maze):
        if not self.active or self.finished:
            return False
        if not line_of_sight(self.x, self.y, px, py, maze):
            return False
        dist = math.sqrt((self.x - px) ** 2 + (self.y - py) ** 2)
        return abs(dist - self.radius) < pr + 20 or dist < self.radius

    def light_up(self):
        if not self.lit:
            self.lit = True

    def draw(self, screen, camera, maze):
        if not self.active or self.finished or not self.lit or self.radius <= 0:
            return

        if not self.distances_calculated:
            self.wall_distances = [
                raycast(
                    self.x, self.y,
                    (2 * math.pi * i) / RIPPLE_SEGMENTS,
                    self.max_radius, maze,
                )
                for i in range(RIPPLE_SEGMENTS)
            ]
            self.distances_calculated = True

        alpha = max(0, 1 - self.radius / self.max_radius)
        color = tuple(
            max(0, min(255, int(c * alpha + v)))
            for c, v in zip(COLOR_RIPPLE, (60, 80, 100))
        )
        glow = tuple(max(0, min(255, int(c * alpha * 0.3))) for c in COLOR_RIPPLE)

        points = []
        for i in range(RIPPLE_SEGMENTS):
            angle = (2 * math.pi * i) / RIPPLE_SEGMENTS
            wd = self.wall_distances[i] if i < len(self.wall_distances) else self.max_radius
            ad = min(self.radius, wd)
            if ad > 5:
                rpx = self.x + ad * math.cos(angle)
                rpy = self.y + ad * math.sin(angle)
                sx, sy = camera.apply(rpx, rpy)
                points.append((int(sx), int(sy)))
            else:
                points.append(None)

        for i in range(len(points)):
            p1 = points[i]
            p2 = points[(i + 1) % len(points)]
            if p1 and p2:
                seg_dist = math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)
                if seg_dist <= CELL_SIZE * 1.5:
                    pygame.draw.line(screen, glow, p1, p2, RIPPLE_THICKNESS + 4)
                    pygame.draw.line(screen, color, p1, p2, RIPPLE_THICKNESS)


class RippleManager:
    def __init__(self):
        self.ripples = []

    def create_ripples(self, x, y, max_radius, lit=False):
        for i in range(RIPPLE_COUNT):
            self.ripples.append(Ripple(x, y, max_radius, delay=i * RIPPLE_INTERVAL, lit=lit))

    def update(self, dt, px, py, pr, fog, maze):
        for r in self.ripples:
            r.update(dt, maze)
            if r.check_player_contact(px, py, pr, maze):
                if not r.lit:
                    r.light_up()
            if r.lit and r.active:
                fog.reveal_ring_with_los(r.x, r.y, r.radius, 20, maze)

        self.ripples = [r for r in self.ripples if not r.finished]

    def get_visible_ripples(self):
        return [r for r in self.ripples if r.lit and r.active and not r.finished]

    def draw(self, screen, camera, maze):
        for r in self.ripples:
            r.draw(screen, camera, maze)