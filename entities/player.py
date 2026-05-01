import math
import random
import pygame
from settings import (
    CELL_SIZE, SCREEN_WIDTH, SCREEN_HEIGHT,
    PLAYER_RADIUS,
    PLAYER_SPEED_WALK, PLAYER_SPEED_SPRINT,
    COLOR_PLAYER, COLOR_WHITE,
    PLAYER_RIPPLE_INTERVAL_IDLE, PLAYER_RIPPLE_INTERVAL_WALK,
    PLAYER_RIPPLE_INTERVAL_SPRINT,
    PLAYER_RIPPLE_SPEED, PLAYER_RIPPLE_MAX_RADIUS,
    PLAYER_WAKE_LIFETIME, PLAYER_WAKE_SPREAD, PLAYER_WAKE_OFFSET,
    WALL_WARNING_DISTANCE, WALL_DANGER_DISTANCE, COLOR_WARNING,
    COLOR_PLAYER_RIPPLE,
)


class WallWarning:
    def __init__(self):
        self.danger_level = 0.0

    def update(self, player_x, player_y, maze):
        min_dist = float('inf')
        cx = int(player_x // CELL_SIZE)
        cy = int(player_y // CELL_SIZE)

        for dy in range(-1, 2):
            for dx in range(-1, 2):
                wx, wy = cx + dx, cy + dy
                if 0 <= wy < len(maze) and 0 <= wx < len(maze[0]) and maze[wy][wx] == '#':
                    wall_left = wx * CELL_SIZE
                    wall_right = (wx + 1) * CELL_SIZE
                    wall_top = wy * CELL_SIZE
                    wall_bottom = (wy + 1) * CELL_SIZE

                    nearest_x = max(wall_left, min(player_x, wall_right))
                    nearest_y = max(wall_top, min(player_y, wall_bottom))

                    dist = math.sqrt(
                        (player_x - nearest_x) ** 2 + (player_y - nearest_y) ** 2
                    )
                    min_dist = min(min_dist, dist)

        if min_dist <= WALL_DANGER_DISTANCE:
            self.danger_level = 1.0
        elif min_dist <= WALL_WARNING_DISTANCE:
            self.danger_level = (WALL_WARNING_DISTANCE - min_dist) / WALL_WARNING_DISTANCE
        else:
            self.danger_level = 0.0

    def draw(self, screen):
        if self.danger_level <= 0:
            return
        alpha = int(80 * self.danger_level)
        if self.danger_level > 0.7:
            pulse = (math.sin(pygame.time.get_ticks() * 0.015) + 1) / 2
            alpha = int(alpha * (0.7 + 0.3 * pulse))
        surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        surface.fill((COLOR_WARNING[0], COLOR_WARNING[1], COLOR_WARNING[2], alpha))
        screen.blit(surface, (0, 0))


class WakeParticle:
    """Одна частица V-следа за игроком"""

    def __init__(self, x, y, dx, dy):
        self.x, self.y = x, y
        self.dx, self.dy = dx, dy
        self.lifetime = PLAYER_WAKE_LIFETIME
        self.max_lifetime = PLAYER_WAKE_LIFETIME
        self.finished = False

    def update(self, dt):
        if self.finished:
            return
        self.x += self.dx * dt
        self.y += self.dy * dt
        self.dx *= 0.94
        self.dy *= 0.94
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.finished = True

    def draw(self, screen, camera):
        if self.finished:
            return
        sx, sy = camera.apply(self.x, self.y)
        a = max(0, self.lifetime / self.max_lifetime)
        # Точка которая тускнеет и немного растёт
        r = 1.5 + (1 - a) * 1.5
        brightness = a * 0.6
        color = (
            int(COLOR_PLAYER_RIPPLE[0] * brightness),
            int(COLOR_PLAYER_RIPPLE[1] * brightness),
            int(COLOR_PLAYER_RIPPLE[2] * brightness),
        )
        pygame.draw.circle(screen, color, (int(sx), int(sy)), max(1, int(r)))


class PlayerRippleSystem:
    """След за игроком при ходьбе, тихая рябь стоя"""

    def __init__(self):
        self.wake_particles = []
        self.ripple_timer = 0
        # Одна рябь стоя — просто круг который расходится
        self.idle_radius = 0
        self.idle_active = False
        self.idle_x, self.idle_y = 0, 0

    def update(self, dt, player_x, player_y, is_moving, is_sprinting, move_angle):
        self.ripple_timer += dt

        if is_moving:
            # Сброс idle ряби
            self.idle_active = False
            self.idle_radius = 0

            # Интервал спавна следа
            interval = PLAYER_RIPPLE_INTERVAL_SPRINT if is_sprinting else PLAYER_RIPPLE_INTERVAL_WALK

            if self.ripple_timer >= interval:
                self.ripple_timer = 0
                back_angle = move_angle + math.pi

                # V-образный след — две линии частиц
                for side in [-1, 1]:
                    spread_angle = back_angle + side * PLAYER_WAKE_SPREAD
                    spawn_x = player_x + math.cos(back_angle) * PLAYER_WAKE_OFFSET
                    spawn_y = player_y + math.sin(back_angle) * PLAYER_WAKE_OFFSET
                    spawn_x += random.uniform(-1, 1)
                    spawn_y += random.uniform(-1, 1)

                    speed = random.uniform(8, 16)
                    if is_sprinting:
                        speed *= 1.4
                    dx = math.cos(spread_angle) * speed
                    dy = math.sin(spread_angle) * speed
                    self.wake_particles.append(WakeParticle(spawn_x, spawn_y, dx, dy))
        else:
            # Стоим — одна расходящаяся рябь (не создаём новые круги)
            if not self.idle_active:
                self.idle_active = True
                self.idle_x, self.idle_y = player_x, player_y
                self.idle_radius = 0

            self.idle_radius += PLAYER_RIPPLE_SPEED * dt
            if self.idle_radius >= PLAYER_RIPPLE_MAX_RADIUS:
                # Рестарт ряби
                self.idle_radius = 0
                self.idle_x, self.idle_y = player_x, player_y

        # Обновляем частицы
        for p in self.wake_particles:
            p.update(dt)
        self.wake_particles = [p for p in self.wake_particles if not p.finished]

    def draw(self, screen, camera):
        # V-след
        for p in self.wake_particles:
            p.draw(screen, camera)

        # Idle рябь — один тонкий круг
        if self.idle_active and self.idle_radius > 1:
            sx, sy = camera.apply(self.idle_x, self.idle_y)
            a = max(0, 1 - self.idle_radius / PLAYER_RIPPLE_MAX_RADIUS)
            color = (
                max(0, min(255, int(COLOR_PLAYER_RIPPLE[0] * a * 0.5 + 15))),
                max(0, min(255, int(COLOR_PLAYER_RIPPLE[1] * a * 0.5 + 15))),
                max(0, min(255, int(COLOR_PLAYER_RIPPLE[2] * a * 0.5 + 15))),
            )
            pygame.draw.circle(screen, color, (int(sx), int(sy)), int(self.idle_radius), 1)

    def clear(self):
        self.wake_particles.clear()
        self.ripple_timer = 0
        self.idle_active = False
        self.idle_radius = 0


class Player:
    def __init__(self, x, y, speed_mult=1.0):
        self.x, self.y = x, y
        self.radius = PLAYER_RADIUS
        self.speed_walk = PLAYER_SPEED_WALK * speed_mult
        self.speed_sprint = PLAYER_SPEED_SPRINT * speed_mult
        self.alive = True
        self.just_died = False
        self.is_moving = False
        self.is_sprinting = False
        self.move_angle = 0
        self.facing_angle = 0
        self.death_x, self.death_y = 0, 0
        self.invincible_timer = 0
        self.wall_push_timer = 0.0
        self.wall_warning = WallWarning()
        self.ripple_system = None

    def update(self, keys, maze, dt, camera):
        self.just_died = False

        if not self.alive:
            return

        if self.invincible_timer > 0:
            self.invincible_timer -= dt

        self.is_sprinting = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        speed = self.speed_sprint if self.is_sprinting else self.speed_walk
        # Нормализуем скорость к 60 FPS, чтобы поведение было стабильнее на разных FPS.
        frame_scale = dt * 60.0

        move_x, move_y = 0, 0
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            move_y -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            move_y += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            move_x -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            move_x += 1

        length = math.sqrt(move_x * move_x + move_y * move_y)
        if length > 0:
            move_x = move_x / length * speed * frame_scale
            move_y = move_y / length * speed * frame_scale
            self.move_angle = math.atan2(move_y, move_x)
            self.facing_angle = self.move_angle

        self.is_moving = (move_x != 0 or move_y != 0)

        if self.is_moving:
            # Пытаемся двигаться по осям отдельно, чтобы не умирать от "ложных"
            # диагональных касаний в узких проходах.
            moved = False

            new_x = self.x + move_x
            if not self._collides(new_x, self.y, maze):
                self.x = new_x
                moved = True

            new_y = self.y + move_y
            if not self._collides(self.x, new_y, maze):
                self.y = new_y
                moved = True

            pressing_into_wall = not moved
            if pressing_into_wall and self.invincible_timer <= 0:
                self.wall_push_timer += dt
            else:
                self.wall_push_timer = max(0.0, self.wall_push_timer - dt * 2.0)

            if self.wall_push_timer >= 0.12 and self.invincible_timer <= 0:
                self.die()
                return
            if moved:
                self.wall_push_timer = 0.0
        else:
            self.wall_push_timer = 0.0

        # Критично: смерть должна срабатывать при любом касании стены, не только в углах.
        nearest_wall_dist = self._distance_to_nearest_wall(self.x, self.y, maze)
        # По факту в игре "визуальное касание" наступает чуть раньше геометрического центра радиуса.
        # Добавляем небольшой запас, чтобы смерть срабатывала ожидаемо для игрока.
        touching_wall = nearest_wall_dist <= self.radius + 1.2
        if touching_wall and self.invincible_timer <= 0:
            self.die()
            return

        self.wall_warning.update(self.x, self.y, maze)

    def _collides(self, x, y, maze):
        check_points = [
            (x - self.radius, y),
            (x + self.radius, y),
            (x, y - self.radius),
            (x, y + self.radius),
            (x - self.radius * 0.7, y - self.radius * 0.7),
            (x + self.radius * 0.7, y - self.radius * 0.7),
            (x - self.radius * 0.7, y + self.radius * 0.7),
            (x + self.radius * 0.7, y + self.radius * 0.7),
        ]
        for px, py in check_points:
            cx = int(px // CELL_SIZE)
            cy = int(py // CELL_SIZE)
            if not (0 <= cy < len(maze) and 0 <= cx < len(maze[0])):
                return True
            if maze[cy][cx] == '#':
                return True
        return False

    def _distance_to_nearest_wall(self, x, y, maze):
        cx = int(x // CELL_SIZE)
        cy = int(y // CELL_SIZE)
        min_dist = float('inf')
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                wx, wy = cx + dx, cy + dy
                if not (0 <= wy < len(maze) and 0 <= wx < len(maze[0])):
                    continue
                if maze[wy][wx] != '#':
                    continue
                left = wx * CELL_SIZE
                right = (wx + 1) * CELL_SIZE
                top = wy * CELL_SIZE
                bottom = (wy + 1) * CELL_SIZE
                nearest_x = max(left, min(x, right))
                nearest_y = max(top, min(y, bottom))
                dist = math.sqrt((x - nearest_x) ** 2 + (y - nearest_y) ** 2)
                if dist < min_dist:
                    min_dist = dist
        return min_dist

    def die(self):
        self.death_x, self.death_y = self.x, self.y
        self.alive = False
        self.just_died = True

    def respawn(self, x, y):
        self.x, self.y = x, y
        self.alive = True
        self.just_died = False
        self.is_moving = False
        self.is_sprinting = False
        self.facing_angle = 0
        self.invincible_timer = 1.5
        self.wall_push_timer = 0.0
        if self.ripple_system:
            self.ripple_system.clear()

    def draw(self, screen, camera):
        if self.ripple_system:
            self.ripple_system.draw(screen, camera)

        if not self.alive:
            return

        sx, sy = camera.apply(self.x, self.y)

        if self.invincible_timer > 0 and int(self.invincible_timer * 10) % 2 == 0:
            return

        pygame.draw.circle(screen, (20, 40, 60), (int(sx) + 2, int(sy) + 2), self.radius)
        pygame.draw.circle(screen, COLOR_PLAYER, (int(sx), int(sy)), self.radius)
        pygame.draw.circle(screen, COLOR_WHITE, (int(sx), int(sy)), self.radius, 2)

        if self.is_sprinting and self.is_moving:
            pygame.draw.circle(screen, (180, 230, 255), (int(sx), int(sy)), self.radius + 2, 1)
