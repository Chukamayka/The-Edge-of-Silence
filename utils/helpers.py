import math
from settings import CELL_SIZE


def raycast(start_x, start_y, angle, max_distance, maze):
    """Бросает луч из точки под углом, возвращает расстояние до стены"""
    dir_x, dir_y = math.cos(angle), math.sin(angle)
    step, distance = 2, 0
    while distance < max_distance:
        cx = int((start_x + dir_x * distance) // CELL_SIZE)
        cy = int((start_y + dir_y * distance) // CELL_SIZE)
        if not (0 <= cy < len(maze) and 0 <= cx < len(maze[0])):
            return distance
        if maze[cy][cx] == '#':
            return distance
        distance += step
    return max_distance


def line_of_sight(x1, y1, x2, y2, maze):
    """Проверяет прямую видимость между двумя точками (нет стен на пути)"""
    dx, dy = x2 - x1, y2 - y1
    dist = math.sqrt(dx * dx + dy * dy)
    if dist < 1:
        return True
    steps = int(dist / 5) + 1
    for i in range(steps + 1):
        t = i / steps
        px, py = x1 + dx * t, y1 + dy * t
        cx, cy = int(px // CELL_SIZE), int(py // CELL_SIZE)
        if 0 <= cy < len(maze) and 0 <= cx < len(maze[0]):
            if maze[cy][cx] == '#':
                return False
        else:
            return False
    return True


def lerp_color(c1, c2, t):
    """Линейная интерполяция между двумя цветами"""
    t = max(0, min(1, t))
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


def lerp(a, b, t):
    """Линейная интерполяция между числами"""
    return a + (b - a) * t