import pygame
from settings import (
    COLOR_WHITE, COLOR_BUTTON, COLOR_BUTTON_HOVER, COLOR_BUTTON_ACTIVE,
    COLOR_BUTTON_TEXT, COLOR_SEGMENT_EMPTY, COLOR_SEGMENT_HOVER,
)
from utils.helpers import lerp_color


class Button:
    def __init__(self, x, y, width, height, text, font_size=32):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = pygame.font.Font(None, font_size)
        self.hovered = False
        self.active = False

    def update(self, mouse_pos):
        self.hovered = self.rect.collidepoint(mouse_pos)

    def draw(self, screen):
        if self.active:
            color = COLOR_BUTTON_ACTIVE
        elif self.hovered:
            color = COLOR_BUTTON_HOVER
        else:
            color = COLOR_BUTTON
        pygame.draw.rect(screen, color, self.rect, border_radius=8)
        border_color = COLOR_WHITE if self.active else COLOR_BUTTON_TEXT
        border_width = 3 if self.active else 2
        pygame.draw.rect(screen, border_color, self.rect, border_width, border_radius=8)
        text = self.font.render(self.text, True, COLOR_WHITE if self.active else COLOR_BUTTON_TEXT)
        screen.blit(text, text.get_rect(center=self.rect.center))

    def is_clicked(self, mouse_pos, mouse_click):
        return mouse_click and self.rect.collidepoint(mouse_pos)


class ProgressBar:
    """Прогресс-бар с шагом по 5% (вместо слайдера)"""

    def __init__(self, x, y, width, height, label, min_val=0, max_val=1, value=0.5, step=0.05):
        self.rect = pygame.Rect(x, y, width, height)
        self.label = label
        self.min_val, self.max_val = min_val, max_val
        self.step = step
        self.value = round(value / step) * step
        self.segments = int((max_val - min_val) / step)
        self.font = pygame.font.Font(None, 24)
        self.hovered_segment = -1

    def update(self, mouse_pos, mouse_click):
        self.hovered_segment = -1
        if self.rect.collidepoint(mouse_pos):
            rel_x = mouse_pos[0] - self.rect.x
            segment_width = self.rect.width / self.segments
            self.hovered_segment = int(rel_x / segment_width)
            if mouse_click:
                new_value = self.min_val + (self.hovered_segment + 1) * self.step
                self.value = max(self.min_val, min(self.max_val, new_value))

    def draw(self, screen):
        segment_width = self.rect.width / self.segments
        filled = int((self.value - self.min_val) / self.step)

        for i in range(self.segments):
            seg_x = self.rect.x + i * segment_width
            seg_rect = pygame.Rect(seg_x + 1, self.rect.y + 1,
                                   segment_width - 2, self.rect.height - 2)
            if i < filled:
                if i == self.hovered_segment:
                    color = COLOR_SEGMENT_HOVER
                else:
                    t = i / self.segments
                    if t < 0.5:
                        color = lerp_color((60, 180, 100), (180, 180, 60), t * 2)
                    else:
                        color = lerp_color((180, 180, 60), (200, 100, 60), (t - 0.5) * 2)
            else:
                color = (70, 75, 90) if i == self.hovered_segment else COLOR_SEGMENT_EMPTY
            pygame.draw.rect(screen, color, seg_rect, border_radius=2)

        pygame.draw.rect(screen, COLOR_BUTTON_TEXT, self.rect, 2, border_radius=4)

        for i in range(1, self.segments):
            x = self.rect.x + i * segment_width
            pygame.draw.line(screen, (30, 35, 50),
                             (x, self.rect.y + 3), (x, self.rect.bottom - 3), 1)

        percent = int(self.value * 100)
        label_text = self.font.render(f"{self.label}: {percent}%", True, COLOR_WHITE)
        screen.blit(label_text, (self.rect.x, self.rect.y - 25))

        val_text = self.font.render(f"{percent}%", True, COLOR_WHITE)
        screen.blit(val_text, (self.rect.right + 10, self.rect.y + 4))
