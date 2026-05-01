import random


class MazeGenerator:
    def __init__(self, width, height, corridor_width=2):
        self.corridor_width = corridor_width
        self.cell_size = corridor_width + 1
        self.grid_width = max(3, (width - 1) // self.cell_size)
        self.grid_height = max(3, (height - 1) // self.cell_size)
        self.width = self.grid_width * self.cell_size + 1
        self.height = self.grid_height * self.cell_size + 1

    def generate(self):
        maze = [['#' for _ in range(self.width)] for _ in range(self.height)]
        visited = [[False for _ in range(self.grid_width)] for _ in range(self.grid_height)]

        start_gx = self.grid_width // 2
        start_gy = self.grid_height - 1
        stack = [(start_gx, start_gy)]
        visited[start_gy][start_gx] = True
        self._carve_cell(maze, start_gx, start_gy)

        directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        while stack:
            gx, gy = stack[-1]
            neighbors = [
                (gx + dx, gy + dy, dx, dy)
                for dx, dy in directions
                if 0 <= gx + dx < self.grid_width
                and 0 <= gy + dy < self.grid_height
                and not visited[gy + dy][gx + dx]
            ]
            if neighbors:
                nx, ny, dx, dy = random.choice(neighbors)
                visited[ny][nx] = True
                self._carve_passage(maze, gx, gy, dx, dy)
                self._carve_cell(maze, nx, ny)
                stack.append((nx, ny))
            else:
                stack.pop()

        # Старт (внизу) и выход (вверху)
        sx, sy = self.width // 2, self.height - 2
        self._ensure_floor(maze, sx, sy)
        maze[sy][sx] = 'S'

        ex, ey = self.width // 2, 1
        self._ensure_floor(maze, ex, ey)
        maze[ey][ex] = 'E'

        return maze

    def _carve_cell(self, maze, gx, gy):
        bx, by = gx * self.cell_size + 1, gy * self.cell_size + 1
        for dy in range(self.corridor_width):
            for dx in range(self.corridor_width):
                mx, my = bx + dx, by + dy
                if 0 < mx < self.width - 1 and 0 < my < self.height - 1:
                    maze[my][mx] = '.'

    def _carve_passage(self, maze, gx, gy, dx, dy):
        bx, by = gx * self.cell_size + 1, gy * self.cell_size + 1
        if dx != 0:
            sx = bx + (self.corridor_width if dx > 0 else -1)
            for w in range(self.corridor_width):
                if 0 < sx < self.width - 1 and 0 < by + w < self.height - 1:
                    maze[by + w][sx] = '.'
        else:
            sy = by + (self.corridor_width if dy > 0 else -1)
            for w in range(self.corridor_width):
                if 0 < bx + w < self.width - 1 and 0 < sy < self.height - 1:
                    maze[sy][bx + w] = '.'

    def _ensure_floor(self, maze, x, y):
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                nx, ny = x + dx, y + dy
                if 0 < nx < self.width - 1 and 0 < ny < self.height - 1:
                    if maze[ny][nx] == '#':
                        maze[ny][nx] = '.'
