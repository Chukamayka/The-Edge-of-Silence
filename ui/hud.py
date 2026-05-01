import math
import pygame
from settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, CELL_SIZE,
    COLOR_STONE, COLOR_EXIT, COLOR_GRAY, COLOR_WHITE,
    COLOR_POWER_BAR_MAX, EXIT_BEACON_DISTANCE,
    RIPPLE_FLASH_DURATION, RIPPLE_FLASH_INTENSITY, RIPPLE_FLASH_COLOR,
)
from utils.helpers import lerp_color
from ui.components import Button


class ExitBeacon:
    def __init__(self, exit_cell):
        self.cell = exit_cell
        self.x = exit_cell[0] * CELL_SIZE + CELL_SIZE // 2
        self.y = exit_cell[1] * CELL_SIZE + CELL_SIZE // 2
        self.time = 0
        self.intensity = 0

    def update(self, dt, player_x, player_y):
        self.time += dt
        dist = math.sqrt((self.x - player_x) ** 2 + (self.y - player_y) ** 2)
        dist_cells = dist / CELL_SIZE
        if dist_cells < EXIT_BEACON_DISTANCE:
            self.intensity = 1.0 - (dist_cells / EXIT_BEACON_DISTANCE)
        else:
            self.intensity = 0

    def draw(self, screen, camera):
        if self.intensity <= 0.05:
            return
        sx, sy = camera.apply(self.x, self.y)
        pulse = math.sin(self.time * 2) * 0.3 + 0.7
        radius = int(CELL_SIZE * 2 * self.intensity * pulse)
        if radius < 3:
            return
        glow = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow, (100, 255, 150, int(25 * self.intensity)), (radius, radius), radius)
        pygame.draw.circle(glow, (100, 255, 150, int(50 * self.intensity)), (radius, radius), radius // 2)
        screen.blit(glow, (int(sx) - radius, int(sy) - radius))


class RippleFlash:
    """Вспышка при касании ряби игроком — момент 'прозрения'"""

    def __init__(self):
        self.timer = 0
        self.active = False
        self.flash_x, self.flash_y = 0, 0

    def trigger(self, x, y):
        """Запускает вспышку в точке касания"""
        self.active = True
        self.timer = RIPPLE_FLASH_DURATION
        self.flash_x, self.flash_y = x, y

    def update(self, dt):
        if self.active:
            self.timer -= dt
            if self.timer <= 0:
                self.active = False

    def draw(self, screen, camera):
        if not self.active or self.timer <= 0:
            return

        progress = self.timer / RIPPLE_FLASH_DURATION  # 1.0 → 0.0
        alpha = int(RIPPLE_FLASH_INTENSITY * progress * progress)

        # Полноэкранная вспышка (мягкая)
        flash_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        flash_surface.fill((
            RIPPLE_FLASH_COLOR[0],
            RIPPLE_FLASH_COLOR[1],
            RIPPLE_FLASH_COLOR[2],
            max(0, min(255, alpha // 3)),
        ))
        screen.blit(flash_surface, (0, 0))

        # Направленное свечение от точки касания
        sx, sy = camera.apply(self.flash_x, self.flash_y)
        radius = int(150 * (1 - progress) + 30)
        glow_alpha = max(0, min(255, alpha))

        glow = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow, (
            RIPPLE_FLASH_COLOR[0],
            RIPPLE_FLASH_COLOR[1],
            RIPPLE_FLASH_COLOR[2],
            glow_alpha // 2,
        ), (radius, radius), radius)
        screen.blit(glow, (int(sx) - radius, int(sy) - radius))


class SpeedrunTimer:
    def __init__(self):
        self.time = 0
        self.deaths = 0
        self.stones_thrown = 0
        self.running = False
        self.font = pygame.font.Font(None, 28)

    def start(self):
        self.time = 0
        self.deaths = 0
        self.stones_thrown = 0
        self.running = True

    def update(self, dt):
        if self.running:
            self.time += dt

    def stop(self):
        self.running = False

    def format_time(self):
        minutes = int(self.time // 60)
        seconds = int(self.time % 60)
        ms = int((self.time % 1) * 100)
        return f"{minutes:02d}:{seconds:02d}.{ms:02d}"

    def draw(self, screen):
        time_text = self.font.render(self.format_time(), True, (180, 200, 220))
        screen.blit(time_text, (SCREEN_WIDTH - time_text.get_width() - 15, 15))

        if self.deaths > 0:
            death_text = self.font.render(f"x {self.deaths}", True, (200, 100, 100))
            screen.blit(death_text, (SCREEN_WIDTH - death_text.get_width() - 15, 42))


class GameUI:
    def __init__(self):
        self.font = pygame.font.Font(None, 24)

    def draw(self, screen, stone, player):
        panel_h = 40
        panel_surface = pygame.Surface((SCREEN_WIDTH, panel_h), pygame.SRCALPHA)
        panel_surface.fill((20, 30, 50, 180))
        screen.blit(panel_surface, (0, SCREEN_HEIGHT - panel_h))

        if stone.is_held:
            if stone.charging:
                status = f"Заряд: {int(stone.charge_power * 100)}%"
                color = lerp_color(COLOR_STONE, COLOR_POWER_BAR_MAX, stone.charge_power)
            else:
                status = "1 Уровень | Камень в руке | ЛКМ — бросить"
                color = COLOR_STONE
        elif stone.is_flying:
            status = "Камень летит..."
            color = COLOR_STONE
        elif stone.can_pickup(player.x, player.y):
            status = "[E] Подобрать камень"
            color = COLOR_EXIT
        else:
            status = "Камень на земле"
            color = COLOR_GRAY

        text = self.font.render(status, True, color)
        screen.blit(text, (15, SCREEN_HEIGHT - panel_h + 10))

        # Подсказка спринта
        sprint_text = self.font.render("SHIFT — бег", True, (60, 80, 100))
        screen.blit(sprint_text, (SCREEN_WIDTH - sprint_text.get_width() - 15,
                                  SCREEN_HEIGHT - panel_h + 10))


class VictoryScreen:
    """Экран победы с кнопками"""

    def __init__(self):
        self.font = pygame.font.Font(None, 48)
        self.stat_font = pygame.font.Font(None, 28)
        self.retry_button = Button(SCREEN_WIDTH // 2 - 110, SCREEN_HEIGHT // 2 + 130, 100, 45, "Ещё раз", 24)
        self.menu_button = Button(SCREEN_WIDTH // 2 + 10, SCREEN_HEIGHT // 2 + 130, 100, 45, "Меню", 24)

    def update(self, mouse_pos):
        self.retry_button.update(mouse_pos)
        self.menu_button.update(mouse_pos)

    def draw(self, screen, timer, next_level_text=None, record_text=None):
        # Затемнение
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        title = self.font.render("ВЫХОД НАЙДЕН", True, COLOR_EXIT)
        screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 120)))

        time_text = self.stat_font.render(f"Время: {timer.format_time()}", True, COLOR_WHITE)
        screen.blit(time_text, time_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 65)))

        deaths_text = self.stat_font.render(f"Смертей: {timer.deaths}", True, (200, 150, 150))
        screen.blit(deaths_text, deaths_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 35)))

        throws_text = self.stat_font.render(f"Бросков: {timer.stones_thrown}", True, (150, 180, 200))
        screen.blit(throws_text, throws_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 5)))

        if next_level_text:
            hint_text = self.stat_font.render(next_level_text, True, (170, 220, 190))
            screen.blit(hint_text, hint_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 25)))

        if record_text:
            record_surface = self.stat_font.render(record_text, True, (245, 225, 130))
            screen.blit(record_surface, record_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 60)))

        self.retry_button.draw(screen)
        self.menu_button.draw(screen)
