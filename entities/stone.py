import math
import random
import pygame
from settings import (
    CELL_SIZE,
    STONE_SPEED_MIN, STONE_SPEED_MAX, STONE_CHARGE_TIME,
    STONE_MAX_DISTANCE_MIN, STONE_MAX_DISTANCE_MAX,
    STONE_PICKUP_RADIUS, STONE_BOUNCE_DECAY,
    STONE_MAX_BOUNCES_MIN, STONE_MAX_BOUNCES_MAX,
    RIPPLE_MAX_RADIUS_MIN, RIPPLE_MAX_RADIUS_MAX,
    COLOR_STONE, COLOR_WHITE, COLOR_POWER_BAR_BG, COLOR_POWER_BAR_FILL,
    COLOR_POWER_BAR_MAX,
)
from utils.helpers import lerp_color


class Stone:
    def __init__(self):
        self.x, self.y = 0, 0
        self.dx, self.dy = 0, 0
        self.is_held = True
        self.is_flying = False
        self.is_on_ground = False
        self.bounces_left = STONE_MAX_BOUNCES_MAX
        self.max_bounces = STONE_MAX_BOUNCES_MAX
        self.distance_traveled = 0
        self.max_distance = STONE_MAX_DISTANCE_MAX
        self.ripple_radius = RIPPLE_MAX_RADIUS_MAX
        self.trajectory = []
        self.pulse_timer = 0
        self.charging = False
        self.charge_power = 0
        self.just_bounced = False
        self.just_landed = False
        self.last_land_hit_wall = False
        self.dashed_trail = False
        self.trail_fade_speed = 150
        self.trail_visible_through_fog = False

    def start_charging(self):
        if self.is_held:
            self.charging = True
            self.charge_power = 0

    def update_charge(self, dt):
        if self.charging and self.is_held:
            self.charge_power = min(1.0, self.charge_power + dt / STONE_CHARGE_TIME)

    def throw(self, start_x, start_y, target_x, target_y):
        if not self.is_held:
            return

        self.x, self.y = start_x, start_y
        dx, dy = target_x - start_x, target_y - start_y
        dist = math.sqrt(dx * dx + dy * dy)

        if dist > 0:
            speed = STONE_SPEED_MIN + (STONE_SPEED_MAX - STONE_SPEED_MIN) * self.charge_power
            self.max_distance = (STONE_MAX_DISTANCE_MIN
                                 + (STONE_MAX_DISTANCE_MAX - STONE_MAX_DISTANCE_MIN) * self.charge_power)
            self.max_bounces = int(
                STONE_MAX_BOUNCES_MIN
                + (STONE_MAX_BOUNCES_MAX - STONE_MAX_BOUNCES_MIN) * self.charge_power
            )
            self.ripple_radius = (RIPPLE_MAX_RADIUS_MIN
                                  + (RIPPLE_MAX_RADIUS_MAX - RIPPLE_MAX_RADIUS_MIN) * self.charge_power)
            self.dx = (dx / dist) * speed
            self.dy = (dy / dist) * speed

        self.is_held = False
        self.is_flying = True
        self.is_on_ground = False
        self.bounces_left = self.max_bounces
        self.distance_traveled = 0
        self.trajectory = []
        self.charging = False
        self.charge_power = 0
        self.last_land_hit_wall = False

    def update(self, dt, maze):
        self.just_bounced = False
        self.just_landed = False

        if self.is_flying:
            self.trajectory.append({'x': self.x, 'y': self.y, 'alpha': 255})
            # Нормализация к 60 FPS: физика камня не зависит от текущего FPS.
            frame_scale = dt * 60.0
            step_x = self.dx * frame_scale
            step_y = self.dy * frame_scale
            total_step = math.sqrt(step_x ** 2 + step_y ** 2)
            # Дробим длинный шаг на подшаги, чтобы стабилизировать рикошет в углах.
            substeps = max(1, int(total_step / max(1.0, CELL_SIZE / 4.0)))
            inc_x = step_x / substeps
            inc_y = step_y / substeps

            for _ in range(substeps):
                old_x, old_y = self.x, self.y
                self.x += inc_x
                self.y += inc_y
                self.distance_traveled += math.sqrt(inc_x ** 2 + inc_y ** 2)

                cx = int(self.x // CELL_SIZE)
                cy = int(self.y // CELL_SIZE)
                hit = (not (0 <= cy < len(maze) and 0 <= cx < len(maze[0]))
                       or maze[cy][cx] == '#')

                if hit:
                    if self.bounces_left > 0:
                        self._bounce(old_x, old_y, maze)
                        self.just_bounced = True
                        # После отражения продолжаем оставшиеся подшаги уже с новой скоростью.
                        continue
                    self._land(old_x, old_y, hit_wall=True)
                    break

                if self.distance_traveled >= self.max_distance:
                    self._land(self.x, self.y, hit_wall=False)
                    break

        elif self.is_on_ground:
            self.pulse_timer += dt

        # Затухание траектории
        new_traj = []
        for p in self.trajectory:
            if p is None:
                new_traj.append(None)
            else:
                p['alpha'] -= self.trail_fade_speed * dt
                if p['alpha'] > 0:
                    new_traj.append(p)
        self.trajectory = new_traj

    def _is_wall(self, x, y, maze):
        """Проверяет является ли клетка стеной или за границей"""
        cx = int(x // CELL_SIZE)
        cy = int(y // CELL_SIZE)
        if not (0 <= cy < len(maze) and 0 <= cx < len(maze[0])):
            return True
        return maze[cy][cx] == '#'

    def _bounce(self, old_x, old_y, maze):
        """Отскок с правильным определением оси столкновения"""
        # Проверяем какая ось вызвала столкновение
        # Пробуем двигаться только по X (оставляя старый Y)
        hit_x = self._is_wall(self.x, old_y, maze)
        # Пробуем двигаться только по Y (оставляя старый X)
        hit_y = self._is_wall(old_x, self.y, maze)

        if hit_x and hit_y:
            # Угол — отражаем обе оси, но добавляем небольшое смещение
            # чтобы не лететь идеально обратно
            self.dx = -self.dx
            self.dy = -self.dy
            # Небольшое случайное отклонение при угловом столкновении
            angle_offset = random.uniform(-0.3, 0.3)
            speed = math.sqrt(self.dx ** 2 + self.dy ** 2)
            angle = math.atan2(self.dy, self.dx) + angle_offset
            self.dx = math.cos(angle) * speed
            self.dy = math.sin(angle) * speed
        elif hit_x:
            # Столкновение по горизонтали — отражаем X
            self.dx = -self.dx
        elif hit_y:
            # Столкновение по вертикали — отражаем Y
            self.dy = -self.dy
        else:
            # Диагональное попадание — отражаем обе с отклонением
            self.dx = -self.dx
            self.dy = -self.dy
            angle_offset = random.uniform(-0.4, 0.4)
            speed = math.sqrt(self.dx ** 2 + self.dy ** 2)
            angle = math.atan2(self.dy, self.dx) + angle_offset
            self.dx = math.cos(angle) * speed
            self.dy = math.sin(angle) * speed

        self.dx *= STONE_BOUNCE_DECAY
        self.dy *= STONE_BOUNCE_DECAY
        self.x, self.y = old_x, old_y
        self.bounces_left -= 1
        self.trajectory.append(None)

    def _land(self, x, y, hit_wall=False):
        self.x, self.y = x, y
        self.dx = self.dy = 0
        self.is_flying = False
        self.is_on_ground = True
        self.pulse_timer = 0
        self.just_landed = True
        self.last_land_hit_wall = hit_wall

    def can_pickup(self, px, py):
        if not self.is_on_ground:
            return False
        return math.sqrt((self.x - px) ** 2 + (self.y - py) ** 2) <= STONE_PICKUP_RADIUS

    def pickup(self):
        self.is_held = True
        self.is_flying = False
        self.is_on_ground = False
        self.trajectory = []
        self.charging = False
        self.charge_power = 0
        self.last_land_hit_wall = False

    def get_distance_to(self, px, py):
        return math.sqrt((self.x - px) ** 2 + (self.y - py) ** 2)

    def draw(self, screen, camera, player_x, player_y, mouse_x, mouse_y,
             fog, visible_ripples, maze):
        # Траектория
        prev = None
        seg_index = 0
        for p in self.trajectory:
            if p is None:
                prev = None
                continue
            if prev:
                seg_index += 1
                if self.dashed_trail and seg_index % 2 == 0:
                    prev = p
                    continue
                cx = int(p['x'] // CELL_SIZE)
                cy = int(p['y'] // CELL_SIZE)
                if self.trail_visible_through_fog or fog.is_visible(cx, cy, player_x, player_y, visible_ripples, maze):
                    p1 = camera.apply(prev['x'], prev['y'])
                    p2 = camera.apply(p['x'], p['y'])
                    a = min(255, int(p['alpha']))
                    color = (
                        int(COLOR_STONE[0] * a / 255),
                        int(COLOR_STONE[1] * a / 255),
                        int(COLOR_STONE[2] * a / 255),
                    )
                    pygame.draw.line(
                        screen, color,
                        (int(p1[0]), int(p1[1])),
                        (int(p2[0]), int(p2[1])), 2,
                    )
            prev = p

        if self.is_held:
            wmx = mouse_x + camera.x
            wmy = mouse_y + camera.y
            angle = math.atan2(wmy - player_y, wmx - player_x)
            offset = 25
            stone_x = player_x + math.cos(angle) * offset
            stone_y = player_y + math.sin(angle) * offset
            sx, sy = camera.apply(stone_x, stone_y)

            if self.charging:
                stone_color = lerp_color(COLOR_STONE, COLOR_POWER_BAR_MAX, self.charge_power)
            else:
                stone_color = COLOR_STONE
            pygame.draw.circle(screen, stone_color, (int(sx), int(sy)), 7)

            psx, psy = camera.apply(player_x, player_y)
            aim_length = 30 + 50 * self.charge_power
            aim_x = psx + math.cos(angle) * aim_length
            aim_y = psy + math.sin(angle) * aim_length
            aim_color = lerp_color((80, 80, 80), COLOR_POWER_BAR_MAX, self.charge_power)
            pygame.draw.line(
                screen, aim_color,
                (int(psx), int(psy)), (int(aim_x), int(aim_y)),
                1 + int(self.charge_power * 2),
            )

            if self.charge_power > 0:
                self._draw_power_bar(screen, camera, player_x, player_y)

        elif self.is_flying or self.is_on_ground:
            cx = int(self.x // CELL_SIZE)
            cy = int(self.y // CELL_SIZE)
            if fog.is_visible(cx, cy, player_x, player_y, visible_ripples, maze):
                sx, sy = camera.apply(self.x, self.y)
                if self.is_on_ground:
                    pulse = math.sin(self.pulse_timer * 4) * 0.3 + 1.0
                    radius = int(7 * pulse)
                    for i in range(3):
                        ga = 0.3 - i * 0.1
                        gc = (
                            int(COLOR_STONE[0] * ga),
                            int(COLOR_STONE[1] * ga),
                            int(COLOR_STONE[2] * ga * 0.5),
                        )
                        pygame.draw.circle(
                            screen, gc,
                            (int(sx), int(sy)), int(14 * pulse) + i * 4, 2,
                        )
                else:
                    radius = 7
                pygame.draw.circle(screen, COLOR_STONE, (int(sx), int(sy)), radius)
                pygame.draw.circle(screen, COLOR_WHITE, (int(sx), int(sy)), radius, 1)

    def _draw_power_bar(self, screen, camera, px, py):
        sx, sy = camera.apply(px, py)
        bx, by = sx + 25, sy - 20
        w, h = 8, 40

        bg_rect = pygame.Rect(bx, by, w, h)
        pygame.draw.rect(screen, COLOR_POWER_BAR_BG, bg_rect, border_radius=2)

        fill_h = int(h * self.charge_power)
        fill_rect = pygame.Rect(bx, by + h - fill_h, w, fill_h)
        fill_color = lerp_color(COLOR_POWER_BAR_FILL, COLOR_POWER_BAR_MAX, self.charge_power)
        pygame.draw.rect(screen, fill_color, fill_rect, border_radius=2)

        border_width = 1 + int(self.charge_power >= 0.95)
        pygame.draw.rect(screen, COLOR_WHITE, bg_rect, border_width, border_radius=2)
