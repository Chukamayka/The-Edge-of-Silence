import math
from settings import CELL_SIZE, FOG_PARTICLE_COUNT
from utils.helpers import line_of_sight


class FogOfWar:
    def __init__(self, width, height, fade_time, vision_radius, particle_system=None):
        self.width, self.height = width, height
        self.fade_time = fade_time
        self.vision_radius = vision_radius
        self.revealed = [[0.0 for _ in range(width)] for _ in range(height)]
        # Память: клетка которую хоть раз видели = True (навсегда)
        self.memory = [[False for _ in range(width)] for _ in range(height)]
        self.particle_system = particle_system
        self.particle_cooldown = [[0.0 for _ in range(width)] for _ in range(height)]
        self.active_cells = set()

    def update(self, dt):
        to_remove = []
        for (x, y) in self.active_cells:
            if self.particle_cooldown[y][x] > 0:
                self.particle_cooldown[y][x] -= dt

            v = self.revealed[y][x]
            if v <= 0:
                to_remove.append((x, y))
                continue

            old_val = v
            self.revealed[y][x] = max(0, v - dt)

            if (self.particle_system
                    and self.particle_cooldown[y][x] <= 0
                    and old_val > 0.5
                    and self.revealed[y][x] <= 0.5):
                self.particle_system.create_fog_particles(x, y, dispersing=False)
                self.particle_cooldown[y][x] = 1.0

            if self.revealed[y][x] <= 0:
                to_remove.append((x, y))

        for cell in to_remove:
            self.active_cells.discard(cell)

    def _mark_visible(self, x, y):
        """Помечает клетку как увиденную (память)"""
        if 0 <= x < self.width and 0 <= y < self.height:
            self.memory[y][x] = True

    def reveal_circle(self, cx, cy, radius, duration=None):
        if duration is None:
            duration = self.fade_time
        ccx, ccy = cx / CELL_SIZE, cy / CELL_SIZE
        r = radius / CELL_SIZE
        for y in range(max(0, int(ccy - r) - 1), min(self.height, int(ccy + r) + 2)):
            for x in range(max(0, int(ccx - r) - 1), min(self.width, int(ccx + r) + 2)):
                if math.sqrt((x + 0.5 - ccx) ** 2 + (y + 0.5 - ccy) ** 2) <= r:
                    self.revealed[y][x] = max(self.revealed[y][x], duration)
                    self.active_cells.add((x, y))
                    self._mark_visible(x, y)

    def reveal_ring_with_los(self, cx, cy, radius, thickness, maze):
        ccx, ccy = cx / CELL_SIZE, cy / CELL_SIZE
        inner = (radius - thickness) / CELL_SIZE
        outer = (radius + thickness) / CELL_SIZE
        for y in range(max(0, int(ccy - outer) - 1), min(self.height, int(ccy + outer) + 2)):
            for x in range(max(0, int(ccx - outer) - 1), min(self.width, int(ccx + outer) + 2)):
                dist = math.sqrt((x + 0.5 - ccx) ** 2 + (y + 0.5 - ccy) ** 2)
                if inner <= dist <= outer:
                    wx = x * CELL_SIZE + CELL_SIZE / 2
                    wy = y * CELL_SIZE + CELL_SIZE / 2
                    if line_of_sight(cx, cy, wx, wy, maze):
                        old_val = self.revealed[y][x]
                        self.revealed[y][x] = max(self.revealed[y][x], self.fade_time)
                        self.active_cells.add((x, y))
                        self._mark_visible(x, y)
                        if (self.particle_system
                                and self.particle_cooldown[y][x] <= 0
                                and old_val < 0.5):
                            self.particle_system.create_fog_particles(x, y, dispersing=True)
                            self.particle_cooldown[y][x] = 0.5

    def get_visibility(self, cell_x, cell_y, player_x, player_y, maze):
        if not (0 <= cell_x < self.width and 0 <= cell_y < self.height):
            return 0.0

        v = self.revealed[cell_y][cell_x]
        base_vis = min(1.0, v / 2.0) if v > 0 else 0.0

        ccx = cell_x * CELL_SIZE + CELL_SIZE / 2
        ccy = cell_y * CELL_SIZE + CELL_SIZE / 2
        dist = math.sqrt((ccx - player_x) ** 2 + (ccy - player_y) ** 2)
        max_dist = self.vision_radius * CELL_SIZE

        if dist <= max_dist:
            if line_of_sight(player_x, player_y, ccx, ccy, maze):
                dist_factor = 1.0 - (dist / max_dist) * 0.3
                return max(base_vis, dist_factor)

        return base_vis

    def is_visible(self, cell_x, cell_y, player_x, player_y, visible_ripples, maze):
        if not (0 <= cell_x < self.width and 0 <= cell_y < self.height):
            return False

        if self.revealed[cell_y][cell_x] > 0:
            return True

        ccx = cell_x * CELL_SIZE + CELL_SIZE / 2
        ccy = cell_y * CELL_SIZE + CELL_SIZE / 2
        dist = math.sqrt((ccx - player_x) ** 2 + (ccy - player_y) ** 2)

        if dist <= self.vision_radius * CELL_SIZE:
            if line_of_sight(player_x, player_y, ccx, ccy, maze):
                self._mark_visible(cell_x, cell_y)
                return True

        for r in visible_ripples:
            if math.sqrt((ccx - r.x) ** 2 + (ccy - r.y) ** 2) <= r.radius:
                if line_of_sight(r.x, r.y, ccx, ccy, maze):
                    self._mark_visible(cell_x, cell_y)
                    return True

        return False

    def is_remembered(self, cell_x, cell_y):
        """Была ли клетка когда-либо видна"""
        if 0 <= cell_x < self.width and 0 <= cell_y < self.height:
            return self.memory[cell_y][cell_x]
        return False
