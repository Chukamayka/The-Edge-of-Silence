import math
import random
import pygame
from settings import (
    CELL_SIZE, SCREEN_WIDTH, SCREEN_HEIGHT,
    COLOR_STONE, COLOR_PLAYER_RIPPLE, COLOR_FOG,
    DEATH_PARTICLE_COUNT, DEATH_PARTICLE_SPEED, DEATH_PARTICLE_LIFETIME,
    VICTORY_PARTICLE_COUNT, BUBBLE_SPAWN_RATE, BUBBLE_SPEED, BUBBLE_LIFETIME,
    FOG_PARTICLE_COUNT,
)


class Particle:
    def __init__(self, x, y, dx, dy, lifetime, color, size):
        self.x, self.y = x, y
        self.dx, self.dy = dx, dy
        self.lifetime = self.max_lifetime = lifetime
        self.color, self.size = color, size
        self.finished = False

    def update(self, dt):
        if self.finished:
            return
        self.x += self.dx * dt
        self.y += self.dy * dt
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.finished = True

    def get_alpha(self):
        return max(0, self.lifetime / self.max_lifetime)

    def draw(self, screen, camera):
        if self.finished:
            return
        sx, sy = camera.apply(self.x, self.y)
        a = self.get_alpha()
        color = (int(self.color[0] * a), int(self.color[1] * a), int(self.color[2] * a))
        pygame.draw.circle(screen, color, (int(sx), int(sy)), max(1, int(self.size * a)))


class DeathParticle(Particle):
    def __init__(self, x, y):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(DEATH_PARTICLE_SPEED * 0.5, DEATH_PARTICLE_SPEED)
        color = (random.randint(200, 255), random.randint(50, 150), random.randint(30, 80))
        super().__init__(
            x, y,
            math.cos(angle) * speed, math.sin(angle) * speed,
            random.uniform(DEATH_PARTICLE_LIFETIME * 0.5, DEATH_PARTICLE_LIFETIME),
            color, random.randint(2, 5),
        )
        self.gravity = 80
        self.friction = 0.98

    def update(self, dt):
        if not self.finished:
            self.dy += self.gravity * dt
            self.dx *= self.friction
            self.dy *= self.friction
        super().update(dt)


class VictoryParticle(Particle):
    def __init__(self, x, y):
        angle = random.uniform(-math.pi * 0.8, -math.pi * 0.2)
        speed = random.uniform(50, 150)
        color = (random.randint(80, 150), random.randint(200, 255), random.randint(100, 180))
        super().__init__(
            x, y,
            math.cos(angle) * speed, math.sin(angle) * speed,
            random.uniform(1.0, 2.0), color, random.randint(2, 4),
        )
        self.gravity = -20

    def update(self, dt):
        if not self.finished:
            self.dy += self.gravity * dt
        super().update(dt)


class FogParticle(Particle):
    """Облачко тумана при рассеивании/восстановлении"""

    def __init__(self, x, y, dispersing=True):
        self.dispersing = dispersing
        if dispersing:
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(30, 60)
            dx, dy = math.cos(angle) * speed, math.sin(angle) * speed
            lifetime = random.uniform(0.4, 0.8)
        else:
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(20, 40)
            x += math.cos(angle) * dist
            y += math.sin(angle) * dist
            speed = random.uniform(40, 70)
            dx = -math.cos(angle) * speed
            dy = -math.sin(angle) * speed
            lifetime = random.uniform(0.3, 0.6)

        super().__init__(x, y, dx, dy, lifetime, (10, 10, 15), random.randint(4, 10))
        self.wobble = random.uniform(0, 2 * math.pi)
        self.wobble_speed = random.uniform(8, 15)
        self.wobble_amount = random.uniform(0.3, 0.6)

    def update(self, dt):
        if not self.finished:
            self.wobble += self.wobble_speed * dt
            mod = math.sin(self.wobble) * self.wobble_amount
            self.x += (self.dx + self.dx * mod) * dt
            self.y += (self.dy + self.dy * mod) * dt
            self.lifetime -= dt
            if self.lifetime <= 0:
                self.finished = True

    def get_alpha(self):
        if self.dispersing:
            return max(0, self.lifetime / self.max_lifetime)
        t = 1 - (self.lifetime / self.max_lifetime)
        return t / 0.3 if t < 0.3 else 1 - ((t - 0.3) / 0.7)

    def draw(self, screen, camera):
        if self.finished:
            return
        sx, sy = camera.apply(self.x, self.y)
        a = self.get_alpha()
        base_size = self.size * (0.7 + 0.3 * a)
        for i in range(3):
            ox = math.sin(self.wobble + i * 2) * 3
            oy = math.cos(self.wobble + i * 2) * 3
            s = base_size * (1 - i * 0.2)
            g = int(20 * a)
            pygame.draw.circle(
                screen, (g, g, g + 5),
                (int(sx + ox), int(sy + oy)), max(1, int(s)),
            )


class BubbleParticle(Particle):
    def __init__(self, x, y):
        super().__init__(
            x, y,
            random.uniform(-10, 10), -random.uniform(BUBBLE_SPEED * 0.7, BUBBLE_SPEED),
            random.uniform(BUBBLE_LIFETIME * 0.5, BUBBLE_LIFETIME),
            (100, 150, 200), random.randint(1, 3),
        )
        self.wobble_speed = random.uniform(3, 6)
        self.wobble_amount = random.uniform(5, 15)
        self.wobble_offset = random.uniform(0, 2 * math.pi)
        self.base_x = x
        self.time = 0

    def update(self, dt):
        if self.finished:
            return
        self.time += dt
        self.x = self.base_x + math.sin(self.time * self.wobble_speed + self.wobble_offset) * self.wobble_amount
        self.base_x += self.dx * dt
        self.y += self.dy * dt
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.finished = True


class ParticleSystem:
    def __init__(self):
        self.particles = []
        self.fog_particles = []
        self.bubble_timer = 0

    def create_death_particles(self, x, y):
        for _ in range(DEATH_PARTICLE_COUNT):
            self.particles.append(DeathParticle(x, y))

    def create_victory_particles(self, x, y):
        for _ in range(VICTORY_PARTICLE_COUNT):
            self.particles.append(VictoryParticle(x, y))

    def create_fog_particles(self, cell_x, cell_y, dispersing=True):
        x = cell_x * CELL_SIZE + CELL_SIZE / 2
        y = cell_y * CELL_SIZE + CELL_SIZE / 2
        for _ in range(FOG_PARTICLE_COUNT):
            self.fog_particles.append(FogParticle(
                x + random.uniform(-CELL_SIZE / 3, CELL_SIZE / 3),
                y + random.uniform(-CELL_SIZE / 3, CELL_SIZE / 3),
                dispersing,
            ))

    def update(self, dt, maze, camera):
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if not p.finished]

        for p in self.fog_particles:
            p.update(dt)
        self.fog_particles = [p for p in self.fog_particles if not p.finished]

        # Фоновые пузырьки воды
        self.bubble_timer += dt
        if self.bubble_timer >= 0.1:
            self.bubble_timer = 0
            sx = max(0, int(camera.x // CELL_SIZE) - 1)
            sy = max(0, int(camera.y // CELL_SIZE) - 1)
            ex = min(len(maze[0]), int((camera.x + SCREEN_WIDTH) // CELL_SIZE) + 2)
            ey = min(len(maze), int((camera.y + SCREEN_HEIGHT) // CELL_SIZE) + 2)
            for y in range(sy, ey):
                for x in range(sx, ex):
                    if maze[y][x] != '#' and random.random() < BUBBLE_SPAWN_RATE * 0.1:
                        self.particles.append(BubbleParticle(
                            x * CELL_SIZE + random.uniform(5, CELL_SIZE - 5),
                            y * CELL_SIZE + random.uniform(5, CELL_SIZE - 5),
                        ))

    def draw(self, screen, camera, fog, px, py, visible_ripples, maze):
        for p in self.particles:
            if isinstance(p, (DeathParticle, VictoryParticle)):
                # Эффекты смерти/победы видны всегда
                p.draw(screen, camera)
            else:
                cx = int(p.x // CELL_SIZE)
                cy = int(p.y // CELL_SIZE)
                if fog.is_visible(cx, cy, px, py, visible_ripples, maze):
                    p.draw(screen, camera)

    def draw_fog_particles(self, screen, camera):
        for p in self.fog_particles:
            p.draw(screen, camera)
