import math
import pygame
from settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_WHITE,
    COLOR_MENU_BG, COLOR_WATER_DEEP, COLOR_WATER_LIGHT,
    DIFFICULTY_SETTINGS, COLOR_EXIT, LEVEL_CONFIGS,
)
from ui.components import Button, ProgressBar
from utils.helpers import lerp_color


class MainMenu:
    def __init__(self):
        self.title_font = pygame.font.Font(None, 64)
        self.subtitle_font = pygame.font.Font(None, 28)
        self.small_font = pygame.font.Font(None, 22)
        cx = SCREEN_WIDTH // 2 - 100
        self.play_button = Button(cx, 340, 200, 50, "Играть")
        self.records_button = Button(cx, 410, 200, 50, "Рекорды")
        self.settings_button = Button(cx, 480, 200, 50, "Настройки")
        self.quit_button = Button(cx, 550, 200, 50, "Выход")
        self.level_prev_button = Button(SCREEN_WIDTH // 2 - 180, 285, 50, 34, "<", 26)
        self.level_next_button = Button(SCREEN_WIDTH // 2 + 130, 285, 50, 34, ">", 26)
        self.selected_level = 1
        self.time = 0

    def update(self, dt, mouse_pos):
        self.time += dt
        self.play_button.update(mouse_pos)
        self.records_button.update(mouse_pos)
        self.settings_button.update(mouse_pos)
        self.quit_button.update(mouse_pos)
        self.level_prev_button.update(mouse_pos)
        self.level_next_button.update(mouse_pos)

    def handle_click(self, mouse_pos, mouse_click):
        if not mouse_click:
            return
        max_level = max(LEVEL_CONFIGS.keys())
        if self.level_prev_button.is_clicked(mouse_pos, mouse_click):
            self.selected_level = max(1, self.selected_level - 1)
        elif self.level_next_button.is_clicked(mouse_pos, mouse_click):
            self.selected_level = min(max_level, self.selected_level + 1)

    def draw(self, screen):
        screen.fill(COLOR_MENU_BG)
        # Анимация воды на фоне
        for y in range(0, SCREEN_HEIGHT, 20):
            for x in range(0, SCREEN_WIDTH, 20):
                w = math.sin(x * 0.02 + y * 0.01 + self.time) * 0.5 + 0.5
                color = lerp_color(COLOR_WATER_DEEP, COLOR_WATER_LIGHT, w * 0.3)
                pygame.draw.rect(screen, color, (x, y, 20, 20))

        wave = math.sin(self.time * 2) * 5

        shadow = self.title_font.render("The Edge of Silence", True, (30, 50, 80))
        title = self.title_font.render("The Edge of Silence", True, COLOR_WHITE)
        screen.blit(shadow, shadow.get_rect(center=(SCREEN_WIDTH // 2 + 3, 153 + wave)))
        screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 150 + wave)))

        subtitle = self.subtitle_font.render("Найди выход во тьме", True, (150, 180, 220))
        screen.blit(subtitle, subtitle.get_rect(center=(SCREEN_WIDTH // 2, 220)))

        self.play_button.draw(screen)
        self.records_button.draw(screen)
        self.settings_button.draw(screen)
        self.quit_button.draw(screen)
        self.level_prev_button.draw(screen)
        self.level_next_button.draw(screen)

        level_name = LEVEL_CONFIGS.get(self.selected_level, {}).get("name", "unknown")
        level_title = self.small_font.render("Стартовый уровень", True, (145, 178, 205))
        screen.blit(level_title, level_title.get_rect(center=(SCREEN_WIDTH // 2, 294)))
        level_text = self.small_font.render(
            f"Уровень: {self.selected_level} ({level_name})",
            True,
            (130, 170, 200),
        )
        screen.blit(level_text, level_text.get_rect(center=(SCREEN_WIDTH // 2, 312)))

        controls = [
            "WASD — движение | Зажать ЛКМ — зарядить бросок",
            "E — подобрать камень | ESC — пауза",
        ]
        y = 660
        for line in controls:
            text = self.small_font.render(line, True, (100, 130, 160))
            screen.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, y)))
            y += 24


class RecordsMenu:
    def __init__(self):
        self.title_font = pygame.font.Font(None, 56)
        self.small_font = pygame.font.Font(None, 24)
        self.difficulty = 1
        self.records_rows = []
        self.top_runs_rows = []
        self.diff_prev_button = Button(130, 120, 46, 32, "<", 22)
        self.diff_next_button = Button(624, 120, 46, 32, ">", 22)
        self.back_button = Button(SCREEN_WIDTH // 2 - 100, 700, 200, 50, "Назад")

    def set_data(self, difficulty, records_rows, top_runs_rows):
        self.difficulty = difficulty
        self.records_rows = records_rows or []
        self.top_runs_rows = top_runs_rows or []

    def update(self, mouse_pos):
        self.diff_prev_button.update(mouse_pos)
        self.diff_next_button.update(mouse_pos)
        self.back_button.update(mouse_pos)

    def _format_time(self, seconds):
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        ms = int((seconds % 1) * 100)
        return f"{minutes:02d}:{secs:02d}.{ms:02d}"

    def draw(self, screen):
        screen.fill(COLOR_MENU_BG)
        title = self.title_font.render("Рекорды", True, COLOR_WHITE)
        screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 62)))

        self.diff_prev_button.draw(screen)
        self.diff_next_button.draw(screen)
        diff_name = DIFFICULTY_SETTINGS[self.difficulty]["name"]
        diff_text = self.small_font.render(f"Сложность: {diff_name}", True, (180, 210, 235))
        screen.blit(diff_text, diff_text.get_rect(center=(SCREEN_WIDTH // 2, 136)))

        left_panel = pygame.Rect(80, 180, 300, 480)
        right_panel = pygame.Rect(420, 180, 300, 480)
        pygame.draw.rect(screen, (10, 20, 35, 210), left_panel, border_radius=10)
        pygame.draw.rect(screen, (10, 20, 35, 210), right_panel, border_radius=10)
        pygame.draw.rect(screen, (90, 130, 170), left_panel, 2, border_radius=10)
        pygame.draw.rect(screen, (90, 130, 170), right_panel, 2, border_radius=10)

        left_title = self.small_font.render("Топ забегов", True, (195, 220, 245))
        right_title = self.small_font.render("Лучшее по уровням", True, (195, 220, 245))
        screen.blit(left_title, (left_panel.x + 10, left_panel.y + 10))
        screen.blit(right_title, (right_panel.x + 10, right_panel.y + 10))

        y = left_panel.y + 44
        if self.top_runs_rows:
            for i, row in enumerate(self.top_runs_rows[:12], start=1):
                line = f"{i:>2}. L{row['level']}  {self._format_time(row['time_seconds'])}  D:{row['deaths']}"
                text = self.small_font.render(line, True, (160, 190, 220))
                screen.blit(text, (left_panel.x + 12, y))
                y += 28
        else:
            text = self.small_font.render("Нет записей", True, (120, 145, 165))
            screen.blit(text, (left_panel.x + 12, y))

        y = right_panel.y + 44
        if self.records_rows:
            for row in self.records_rows:
                line = f"L{row['level']}: {self._format_time(row['best_time_seconds'])}  D:{row['deaths']}"
                text = self.small_font.render(line, True, (160, 190, 220))
                screen.blit(text, (right_panel.x + 12, y))
                y += 30
        else:
            text = self.small_font.render("Нет рекордов", True, (120, 145, 165))
            screen.blit(text, (right_panel.x + 12, y))

        self.back_button.draw(screen)


class SettingsMenu:
    def __init__(self, settings):
        self.settings = settings
        self.font = pygame.font.Font(None, 48)
        self.small_font = pygame.font.Font(None, 24)
        cx = SCREEN_WIDTH // 2 - 150

        self.master_bar = ProgressBar(cx, 180, 250, 28, "Общая громкость",
                                      0, 1, settings['master_volume'], 0.05)
        self.music_bar = ProgressBar(cx, 260, 250, 28, "Музыка",
                                     0, 1, settings['music_volume'], 0.05)
        self.sfx_bar = ProgressBar(cx, 340, 250, 28, "Эффекты",
                                    0, 1, settings['sfx_volume'], 0.05)

        self.difficulty_buttons = [
            Button(cx, 440, 90, 40, "Easy", 24),
            Button(cx + 105, 440, 90, 40, "Normal", 24),
            Button(cx + 210, 440, 90, 40, "Hard", 24),
        ]

        self.back_button = Button(SCREEN_WIDTH // 2 - 100, 560, 200, 50, "Назад")
        self._update_difficulty_buttons()

    def _update_difficulty_buttons(self):
        for i, btn in enumerate(self.difficulty_buttons):
            btn.active = (i == self.settings['difficulty'])

    def update(self, mouse_pos, mouse_pressed, mouse_click):
        self.master_bar.update(mouse_pos, mouse_click)
        self.music_bar.update(mouse_pos, mouse_click)
        self.sfx_bar.update(mouse_pos, mouse_click)
        self.back_button.update(mouse_pos)

        for i, btn in enumerate(self.difficulty_buttons):
            btn.update(mouse_pos)
            if btn.is_clicked(mouse_pos, mouse_click):
                self.settings['difficulty'] = i
                self._update_difficulty_buttons()

        self.settings['master_volume'] = self.master_bar.value
        self.settings['music_volume'] = self.music_bar.value
        self.settings['sfx_volume'] = self.sfx_bar.value

    def draw(self, screen):
        screen.fill(COLOR_MENU_BG)

        title = self.font.render("Настройки", True, COLOR_WHITE)
        screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 80)))

        self.master_bar.draw(screen)
        self.music_bar.draw(screen)
        self.sfx_bar.draw(screen)

        diff_label = self.small_font.render("Сложность:", True, COLOR_WHITE)
        screen.blit(diff_label, (SCREEN_WIDTH // 2 - 150, 415))

        for btn in self.difficulty_buttons:
            btn.draw(screen)

        diff = self.settings['difficulty']
        diff_info = DIFFICULTY_SETTINGS[diff]
        desc = (f"Лабиринт: {diff_info['maze_size']}x{diff_info['maze_size']}"
                f" | Обзор: {diff_info['vision_radius']} | Туман: {diff_info['fog_fade']:.0f}с")
        desc_text = self.small_font.render(desc, True, (150, 180, 220))
        screen.blit(desc_text, desc_text.get_rect(center=(SCREEN_WIDTH // 2, 500)))

        self.back_button.draw(screen)


class PauseMenu:
    def __init__(self):
        self.font = pygame.font.Font(None, 48)
        cx = SCREEN_WIDTH // 2 - 100
        self.resume_button = Button(cx, 300, 200, 50, "Продолжить")
        self.settings_button = Button(cx, 370, 200, 50, "Настройки")
        self.menu_button = Button(cx, 440, 200, 50, "В меню")

    def update(self, mouse_pos):
        self.resume_button.update(mouse_pos)
        self.settings_button.update(mouse_pos)
        self.menu_button.update(mouse_pos)

    def draw(self, screen):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        title = self.font.render("ПАУЗА", True, COLOR_WHITE)
        screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 200)))

        self.resume_button.draw(screen)
        self.settings_button.draw(screen)
        self.menu_button.draw(screen)
