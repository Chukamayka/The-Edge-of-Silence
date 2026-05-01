import math
import random
from collections import deque
import pygame
from settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, CELL_SIZE, FPS,
    CORRIDOR_WIDTH, COLOR_FOG, COLOR_EXIT, COLOR_WHITE,
    STATE_MENU, STATE_PLAYING, STATE_PAUSED, STATE_SETTINGS, STATE_RECORDS,
    DIFFICULTY_SETTINGS, DEFAULT_SETTINGS,
    WALL_EDGE_THICKNESS, MEMORY_WALL_BRIGHTNESS,
    SOUND_STEP_INTERVAL_WALK, SOUND_STEP_INTERVAL_SPRINT, SOUND_MAX_DISTANCE,
    DEBUG_OVERLAY_DEFAULT, LEVEL_CONFIGS, LEVEL_ADVANCE_DELAY, SETTINGS_FILE_PATH,
    EMITTER_MIN_DISTANCE_CELLS, EMITTER_SAFE_ZONE_CELLS,
    EMITTER_RIPPLE_INTERVAL_MIN, EMITTER_RIPPLE_INTERVAL_MAX, EMITTER_SOUND_INTERVAL,
    FIREFLY_MIN_DISTANCE_CELLS, FIREFLY_SAFE_ZONE_CELLS,
    FIREFLY_ON_TIME, FIREFLY_OFF_TIME, FIREFLY_REVEAL_RADIUS_CELLS,
    FOG_ADVANCED_OVERLAY, FOG_OVERLAY_STRENGTH, FOG_OVERLAY_SCALE,
    FOG_SOFT_VISUAL, FOG_SOFT_ALPHA,
)
from core.config_manager import ConfigManager
from core.run_database import RunDatabase
from core.camera import Camera
from entities.player import Player
from entities.stone import Stone
from entities.ripple import RippleManager
from systems.maze import MazeGenerator
from systems.fog import FogOfWar
from systems.water import WaterRenderer, Vignette
from systems.particles import ParticleSystem
from systems.sound import SoundManager
from ui.menus import MainMenu, SettingsMenu, PauseMenu, RecordsMenu
from ui.hud import GameUI, ExitBeacon, SpeedrunTimer, RippleFlash, VictoryScreen
from utils.helpers import lerp_color, line_of_sight


class Game:
    def __init__(self):
        pygame.init()

        # Окно с OpenGL флагом — обязательно для ModernGL
        pygame.display.set_mode(
            (SCREEN_WIDTH, SCREEN_HEIGHT),
            pygame.OPENGL | pygame.DOUBLEBUF
        )
        pygame.display.set_caption("The Edge of Silence")

        self.clock = pygame.time.Clock()
        self.running = True
        self.state = STATE_MENU
        self.prev_state = STATE_MENU

        # Инициализируем рендерер (создаёт OpenGL контекст)
        from systems.renderer import Renderer
        self.renderer = Renderer(SCREEN_WIDTH, SCREEN_HEIGHT)

        # Pygame Surface для рисования — теперь рисуем сюда, не на экран
        # Это обычный Surface без OpenGL, просто буфер пикселей
        # SRCALPHA — поверхность с прозрачностью
        # Клетки воды рисуем прозрачными — сквозь них видна OpenGL вода
        self.game_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.screen = self.game_surface

        self.config_manager = ConfigManager(SETTINGS_FILE_PATH, DEFAULT_SETTINGS)
        self.run_db = RunDatabase()
        self.settings = self.config_manager.load()

        self.main_menu = MainMenu()
        self.settings_menu = SettingsMenu(self.settings)
        self.pause_menu = PauseMenu()
        self.records_menu = RecordsMenu()
        self.game_ui = GameUI()
        self.vignette = Vignette(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.sound = SoundManager(self.settings)
        self.ripple_flash = RippleFlash()
        self.victory_screen = VictoryScreen()

        self.maze = None
        self.player = None
        self.stone = None
        self.camera = None
        self.fog = None
        self.water = None
        self.particles = None
        self.ripples = None
        self.exit_beacon = None
        self.timer = None
        self.start_pos = None
        self.exit_pos = None

        self.death_timer = 0
        self.death_particles_created = False
        self.victory_triggered = False
        self.step_sound_timer = 0
        self.show_debug_overlay = DEBUG_OVERLAY_DEFAULT
        self.level_index = 1
        self.victory_timer = 0.0
        self.level_scale = 1.0
        self.stone_enabled = True
        self.water_emitters = []
        self.fireflies = []
        self.view_half_angle = math.radians(65)
        self.glow_stone_mode = False
        self.glow_stone_found = False
        self.glow_stone_spawn = None
        self.victory_saved = False
        self.victory_new_record = False
        self.victory_record_text = None
        self.menu_records_difficulty = self.settings.get('difficulty', 1)
        self._refresh_menu_records()

    def _init_game(self):
        diff = DIFFICULTY_SETTINGS[self.settings['difficulty']]
        level_cfg = LEVEL_CONFIGS.get(self.level_index, LEVEL_CONFIGS[1])
        maze_size = diff['maze_size']
        self.level_scale = (maze_size * maze_size) / float(31 * 31)

        generator = MazeGenerator(maze_size, maze_size, CORRIDOR_WIDTH)
        self.maze = generator.generate()

        self.start_pos = self._find_cell('S')
        self.exit_pos = self._find_cell('E')

        sx = self.start_pos[0] * CELL_SIZE + CELL_SIZE // 2
        sy = self.start_pos[1] * CELL_SIZE + CELL_SIZE // 2

        self.camera = Camera(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.particles = ParticleSystem()
        self.fog = FogOfWar(
            len(self.maze[0]), len(self.maze),
            diff['fog_fade'], diff['vision_radius'] * level_cfg.get('vision_mult', 1.0),
            self.particles,
        )
        self.water = WaterRenderer()
        self.player = Player(sx, sy, diff['speed_mult'])
        self.stone = Stone()
        self.ripples = RippleManager()
        self.exit_beacon = ExitBeacon(self.exit_pos)
        self.timer = SpeedrunTimer()
        self.timer.start()
        self.stone_enabled = level_cfg['stone_enabled']
        self.glow_stone_mode = (self.level_index == 3)
        self.glow_stone_found = not self.glow_stone_mode
        self.glow_stone_spawn = self._create_glow_stone_spawn() if self.glow_stone_mode else None
        self.water_emitters = self._create_water_emitters(self._scaled_count(level_cfg['water_emitters']))
        self.fireflies = self._create_fireflies(self._scaled_count(level_cfg.get('fireflies', 0)))
        if self.glow_stone_mode:
            self.stone.dashed_trail = True
            self.stone.trail_fade_speed = 60
            self.stone.trail_visible_through_fog = True
        else:
            self.stone.dashed_trail = False
            self.stone.trail_fade_speed = 150
            self.stone.trail_visible_through_fog = False

        self.death_timer = 0
        self.death_particles_created = False
        self.victory_triggered = False
        self.victory_timer = 0.0
        self.victory_saved = False
        self.victory_new_record = False
        self.victory_record_text = None
        self.step_sound_timer = 0

        self.fog.reveal_circle(sx, sy, CELL_SIZE * 3, diff['fog_fade'] * 2)
        self.camera.set_position(sx, sy)

        # Амбиент
        self.sound.start_ambient()

    def _create_glow_stone_spawn(self):
        path = self._build_path_to_exit()
        if len(path) < 4:
            return None
        path_len = len(path)
        min_idx = max(1, int(path_len * 0.18))
        max_idx = max(min_idx, int(path_len * 0.38))
        max_idx = min(path_len - 2, max_idx)
        candidates = path[min_idx:max_idx + 1]
        if not candidates:
            candidates = path[1:max(2, min(path_len - 1, 4))]
        gx, gy = random.choice(candidates)
        return {
            'x': gx * CELL_SIZE + CELL_SIZE // 2,
            'y': gy * CELL_SIZE + CELL_SIZE // 2,
        }

    def _is_walkable_cell(self, x, y):
        if not (0 <= y < len(self.maze) and 0 <= x < len(self.maze[0])):
            return False
        return self.maze[y][x] != '#'

    def _build_path_to_exit(self):
        sx, sy = self.start_pos
        ex, ey = self.exit_pos
        queue = deque([(sx, sy)])
        prev = {(sx, sy): None}
        dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        while queue:
            cx, cy = queue.popleft()
            if (cx, cy) == (ex, ey):
                break
            for dx, dy in dirs:
                nx, ny = cx + dx, cy + dy
                if (nx, ny) in prev:
                    continue
                if not self._is_walkable_cell(nx, ny):
                    continue
                prev[(nx, ny)] = (cx, cy)
                queue.append((nx, ny))
        if (ex, ey) not in prev:
            return [(sx, sy)]
        path = []
        cur = (ex, ey)
        while cur is not None:
            path.append(cur)
            cur = prev[cur]
        path.reverse()
        return path

    def _scaled_count(self, base_count):
        if base_count <= 0:
            return 0
        return max(1, int(round(base_count * self.level_scale)))

    def _create_water_emitters(self, count):
        if count <= 0:
            return []
        maze_h = len(self.maze)
        maze_w = len(self.maze[0])
        sx, sy = self.start_pos
        ex, ey = self.exit_pos
        candidates = []
        for y in range(1, maze_h - 1):
            for x in range(1, maze_w - 1):
                if self.maze[y][x] == '#':
                    continue
                if self.maze[y][x] in ('S', 'E'):
                    continue
                # Не ставим эмиттеры слишком близко к старту/выходу.
                if math.hypot(x - sx, y - sy) < EMITTER_SAFE_ZONE_CELLS:
                    continue
                if math.hypot(x - ex, y - ey) < EMITTER_SAFE_ZONE_CELLS:
                    continue
                near_wall = (
                    self.maze[y - 1][x] == '#'
                    or self.maze[y + 1][x] == '#'
                    or self.maze[y][x - 1] == '#'
                    or self.maze[y][x + 1] == '#'
                )
                if near_wall:
                    candidates.append((x, y))

        random.shuffle(candidates)
        emitters = []
        selected_cells = []
        for x, y in candidates:
            if len(emitters) >= count:
                break
            if any(math.hypot(x - ox, y - oy) < EMITTER_MIN_DISTANCE_CELLS for ox, oy in selected_cells):
                continue
            selected_cells.append((x, y))
            emitters.append({
                'x': x * CELL_SIZE + CELL_SIZE // 2,
                'y': y * CELL_SIZE + CELL_SIZE // 2,
                'timer': random.uniform(0.4, 1.4),
                'interval': random.uniform(EMITTER_RIPPLE_INTERVAL_MIN, EMITTER_RIPPLE_INTERVAL_MAX),
                'sound_timer': random.uniform(0.2, EMITTER_SOUND_INTERVAL),
            })
        return emitters

    def _create_fireflies(self, count):
        if count <= 0:
            return []
        maze_h = len(self.maze)
        maze_w = len(self.maze[0])
        sx, sy = self.start_pos
        ex, ey = self.exit_pos
        candidates = []
        for y in range(1, maze_h - 1):
            for x in range(1, maze_w - 1):
                if self.maze[y][x] == '#':
                    continue
                if self.maze[y][x] in ('S', 'E'):
                    continue
                if math.hypot(x - sx, y - sy) < FIREFLY_SAFE_ZONE_CELLS:
                    continue
                if math.hypot(x - ex, y - ey) < FIREFLY_SAFE_ZONE_CELLS:
                    continue
                candidates.append((x, y))

        random.shuffle(candidates)
        fireflies = []
        selected_cells = []
        for x, y in candidates:
            if len(fireflies) >= count:
                break
            if any(math.hypot(x - ox, y - oy) < FIREFLY_MIN_DISTANCE_CELLS for ox, oy in selected_cells):
                continue
            selected_cells.append((x, y))
            is_on = random.choice([True, False])
            fireflies.append({
                'x': x * CELL_SIZE + CELL_SIZE // 2,
                'y': y * CELL_SIZE + CELL_SIZE // 2,
                'on': is_on,
                'timer': random.uniform(0.3, FIREFLY_ON_TIME if is_on else FIREFLY_OFF_TIME),
            })
        return fireflies

    def _find_cell(self, char):
        for y, row in enumerate(self.maze):
            for x, cell in enumerate(row):
                if cell == char:
                    return (x, y)
        raise ValueError(f"Клетка '{char}' не найдена в лабиринте!")

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            mouse_pos, mouse_pressed, mouse_click, mouse_release = self._collect_input()

            # Обновляем рендерер
            self.renderer.update(dt)

            # Рисуем всё на game_surface (не на экран!)
            if self.state == STATE_MENU:
                self._update_menu(dt, mouse_pos, mouse_click)
                self._draw_menu()
            elif self.state == STATE_SETTINGS:
                self._update_settings(mouse_pos, mouse_pressed, mouse_click)
                self._draw_settings()
            elif self.state == STATE_PLAYING:
                self._update_game(dt, mouse_pos, mouse_click, mouse_release, mouse_pressed)
                self._draw_game(mouse_pos)
            elif self.state == STATE_PAUSED:
                self._draw_game(mouse_pos)
                self._update_pause(mouse_pos, mouse_click)
                self._draw_pause()
            elif self.state == STATE_RECORDS:
                self._update_records(mouse_pos, mouse_click)
                self._draw_records()

            # Передаём готовый кадр рендереру — он покажет на экран через OpenGL
            self.renderer.render(self.game_surface)

        self.renderer.release()
        self._save_settings()
        pygame.quit()

    def _collect_input(self):
        mouse_pos = pygame.mouse.get_pos()
        mouse_pressed = pygame.mouse.get_pressed()[0]
        mouse_click = False
        mouse_release = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_click = True
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                mouse_release = True
            elif event.type == pygame.KEYDOWN:
                self._handle_keydown(event.key)
        return mouse_pos, mouse_pressed, mouse_click, mouse_release

    def _handle_keydown(self, key):
        if key == pygame.K_ESCAPE:
            self._handle_escape()
        elif key == pygame.K_F5:
            self.renderer.reload_shaders()
        elif key == pygame.K_F3:
            self.show_debug_overlay = not self.show_debug_overlay
        elif key == pygame.K_F6:
            self.level_index = 1 if self.level_index >= max(LEVEL_CONFIGS.keys()) else self.level_index + 1
            self.sound.stop_ambient()
            self._init_game()
            self.state = STATE_PLAYING

    def _handle_escape(self):
        if self.state == STATE_PLAYING:
            self.state = STATE_PAUSED
        elif self.state == STATE_PAUSED:
            self.state = STATE_PLAYING
        elif self.state == STATE_SETTINGS:
            self.state = self.prev_state
        elif self.state == STATE_RECORDS:
            self.state = STATE_MENU

    def _update_menu(self, dt, mouse_pos, mouse_click):
        self.main_menu.update(dt, mouse_pos)
        self.main_menu.handle_click(mouse_pos, mouse_click)
        if self.main_menu.play_button.is_clicked(mouse_pos, mouse_click):
            self.level_index = self.main_menu.selected_level
            self._init_game()
            self.state = STATE_PLAYING
        if self.main_menu.records_button.is_clicked(mouse_pos, mouse_click):
            self.menu_records_difficulty = self.settings.get('difficulty', 1)
            self._refresh_menu_records()
            self.state = STATE_RECORDS
        if self.main_menu.settings_button.is_clicked(mouse_pos, mouse_click):
            self.prev_state = STATE_MENU
            self.state = STATE_SETTINGS
        if self.main_menu.quit_button.is_clicked(mouse_pos, mouse_click):
            self._save_settings()
            self.running = False

    def _draw_menu(self):
        self.main_menu.draw(self.screen)

    def _refresh_menu_records(self):
        records = self.run_db.get_records_for_difficulty(self.menu_records_difficulty)
        top_runs = self.run_db.get_top_runs_by_difficulty(self.menu_records_difficulty, limit=5)
        self.records_menu.set_data(self.menu_records_difficulty, records, top_runs)

    def _update_records(self, mouse_pos, mouse_click):
        self.records_menu.update(mouse_pos)
        if self.records_menu.diff_prev_button.is_clicked(mouse_pos, mouse_click):
            self.menu_records_difficulty = max(0, self.menu_records_difficulty - 1)
            self._refresh_menu_records()
        elif self.records_menu.diff_next_button.is_clicked(mouse_pos, mouse_click):
            self.menu_records_difficulty = min(2, self.menu_records_difficulty + 1)
            self._refresh_menu_records()
        if self.records_menu.back_button.is_clicked(mouse_pos, mouse_click):
            self.state = STATE_MENU

    def _draw_records(self):
        self.records_menu.draw(self.screen)

    def _update_settings(self, mouse_pos, mouse_pressed, mouse_click):
        self.settings_menu.update(mouse_pos, mouse_pressed, mouse_click)
        if self.settings_menu.back_button.is_clicked(mouse_pos, mouse_click):
            self.sound.update_ambient_volume()
            self._save_settings()
            self.state = self.prev_state

    def _draw_settings(self):
        self.settings_menu.draw(self.screen)

    def _update_pause(self, mouse_pos, mouse_click):
        self.pause_menu.update(mouse_pos)
        if self.pause_menu.resume_button.is_clicked(mouse_pos, mouse_click):
            self.state = STATE_PLAYING
        if self.pause_menu.settings_button.is_clicked(mouse_pos, mouse_click):
            self.prev_state = STATE_PAUSED
            self.state = STATE_SETTINGS
        if self.pause_menu.menu_button.is_clicked(mouse_pos, mouse_click):
            self.sound.stop_ambient()
            self.state = STATE_MENU

    def _draw_pause(self):
        self.pause_menu.draw(self.screen)

    def _update_game(self, dt, mouse_pos, mouse_click, mouse_release, mouse_pressed):
        self.timer.update(dt)
        self.sound.update(dt)
        self.ripple_flash.update(dt)

        # Победа — экран с кнопками
        if self.victory_triggered:
            self.victory_screen.update(mouse_pos)
            if self.victory_screen.retry_button.is_clicked(mouse_pos, mouse_click):
                self.sound.stop_ambient()
                self._init_game()
            elif self.victory_screen.menu_button.is_clicked(mouse_pos, mouse_click):
                self.sound.stop_ambient()
                self.state = STATE_MENU
            elif self._try_advance_level(dt):
                return
            # Обновляем только визуал
            self.particles.update(dt, self.maze, self.camera)
            self.water.update(dt)
            return

        keys = pygame.key.get_pressed()
        self.player.update(keys, self.maze, dt, self.camera)

        if self.glow_stone_mode and not self.glow_stone_found:
            if keys[pygame.K_e] and self._near_glow_stone():
                self.glow_stone_found = True
                self.stone_enabled = True
                self.sound.play('pickup')

        # Смерть
        if self.player.just_died:
            self.particles.create_death_particles(self.player.death_x, self.player.death_y)
            self.death_particles_created = True
            self.death_timer = 0
            self.timer.deaths += 1
            self.sound.play('death')

        if not self.player.alive:
            self.death_timer += dt
            if self.death_timer >= 1.5:
                self._respawn()
            self.particles.update(dt, self.maze, self.camera)
            self.water.update(dt)
            self.camera.update(self.player.x, self.player.y, len(self.maze[0]), len(self.maze))
            # Камеру обновляем даже при смерти
            self.renderer.set_camera(self.camera.x, self.camera.y)
            self.renderer.set_ripples(self.ripples.ripples)
            return

        # Шаги
        if self.player.is_moving:
            interval = SOUND_STEP_INTERVAL_SPRINT if self.player.is_sprinting else SOUND_STEP_INTERVAL_WALK
            self.step_sound_timer += dt
            if self.step_sound_timer >= interval:
                self.step_sound_timer = 0
                self.sound.play_step(self.player.x, self.player.y)
        else:
            self.step_sound_timer = 0

        # Камень
        if self.stone_enabled:
            if mouse_click and self.stone.is_held:
                self.stone.start_charging()
            if mouse_pressed and self.stone.charging:
                self.stone.update_charge(dt)
            if mouse_release and self.stone.charging and self.stone.is_held:
                wx = mouse_pos[0] + self.camera.x
                wy = mouse_pos[1] + self.camera.y
                self.stone.throw(self.player.x, self.player.y, wx, wy)
                self.timer.stones_thrown += 1
                self.sound.play('throw')
            if keys[pygame.K_e] and self.stone.can_pickup(self.player.x, self.player.y):
                self.stone.pickup()
                self.sound.play('pickup')

        old_flying = self.stone.is_flying
        self.stone.update(dt, self.maze)
        if self.glow_stone_mode and (self.stone.is_flying or self.stone.is_on_ground):
            glow_radius = CELL_SIZE * (1.2 if self.stone.is_flying else 0.9)
            glow_duration = 0.14 if self.stone.is_flying else 0.08
            self.fog.reveal_circle(self.stone.x, self.stone.y, glow_radius, glow_duration)
        if self.glow_stone_mode and self.stone.is_flying and len(self.stone.trajectory) >= 2:
            last = self.stone.trajectory[-1]
            prev = self.stone.trajectory[-2]
            if last is not None and prev is not None:
                mx = (last['x'] + prev['x']) * 0.5
                my = (last['y'] + prev['y']) * 0.5
                self.fog.reveal_circle(mx, my, CELL_SIZE * 0.55, 0.06)

        if self.stone.just_bounced:
            self.sound.play_spatial('bounce', self.stone.x, self.stone.y,
                                    self.player.x, self.player.y, SOUND_MAX_DISTANCE)
        if old_flying and not self.stone.is_flying:
            # Если камень остановился из-за удара о стену, рябь не создаём.
            if self.stone.last_land_hit_wall:
                self.sound.play_spatial('bounce', self.stone.x, self.stone.y,
                                        self.player.x, self.player.y, SOUND_MAX_DISTANCE)
            else:
                if not self.glow_stone_mode:
                    self.ripples.create_ripples(self.stone.x, self.stone.y, self.stone.ripple_radius)
                self.sound.play_spatial('splash', self.stone.x, self.stone.y,
                                        self.player.x, self.player.y, SOUND_MAX_DISTANCE)

        for emitter in self.water_emitters:
            emitter['timer'] -= dt
            emitter['sound_timer'] -= dt
            if emitter['timer'] <= 0:
                emitter['timer'] = emitter['interval']
                self.ripples.create_ripples(emitter['x'], emitter['y'], CELL_SIZE * 3, lit=True)
            if emitter['sound_timer'] <= 0:
                emitter['sound_timer'] = EMITTER_SOUND_INTERVAL + random.uniform(-0.4, 0.6)
                self.sound.play_spatial(
                    'waterfall',
                    emitter['x'], emitter['y'],
                    self.player.x, self.player.y,
                    SOUND_MAX_DISTANCE * 1.2,
                    base_volume=0.45,
                )

        for firefly in self.fireflies:
            firefly['timer'] -= dt
            can_see_firefly = self._can_see_point(firefly['x'], firefly['y'])
            if firefly['on'] and can_see_firefly:
                self.fog.reveal_circle(
                    firefly['x'],
                    firefly['y'],
                    CELL_SIZE * FIREFLY_REVEAL_RADIUS_CELLS,
                    0.18,
                )
            if firefly['timer'] <= 0:
                firefly['on'] = not firefly['on']
                firefly['timer'] = FIREFLY_ON_TIME if firefly['on'] else FIREFLY_OFF_TIME
                if firefly['on']:
                    self.sound.play_spatial(
                        'firefly',
                        firefly['x'], firefly['y'],
                        self.player.x, self.player.y,
                        SOUND_MAX_DISTANCE * 0.9,
                        base_volume=0.35,
                    )

        # Рябь — отслеживаем зажигание
        previously_lit = {id(r) for r in self.ripples.ripples if r.lit}
        self.ripples.update(dt, self.player.x, self.player.y, self.player.radius, self.fog, self.maze)

        for r in self.ripples.ripples:
            if r.lit and id(r) not in previously_lit:
                self.sound.play('ripple_flash')
                self.ripple_flash.trigger(self.player.x, self.player.y)
                break

        self.fog.update(dt)
        self.particles.update(dt, self.maze, self.camera)
        self.water.update(dt)
        self.exit_beacon.update(dt, self.player.x, self.player.y)
        self.camera.update(self.player.x, self.player.y, len(self.maze[0]), len(self.maze))

        # Победа
        pc = (int(self.player.x // CELL_SIZE), int(self.player.y // CELL_SIZE))
        if pc == self.exit_pos:
            self.victory_triggered = True
            self.victory_timer = 0.0
            self.timer.stop()
            self.particles.create_victory_particles(self.player.x, self.player.y)
            self.sound.play('victory')
            if not self.victory_saved:
                self.victory_new_record = self.run_db.save_run(
                    self.level_index, self.settings['difficulty'], self.timer
                )
                best = self.run_db.get_best_record(self.level_index, self.settings['difficulty'])
                if best:
                    best_timer = SpeedrunTimer()
                    best_timer.time = best["best_time_seconds"]
                    prefix = "Новый рекорд!" if self.victory_new_record else "Лучший рекорд:"
                    self.victory_record_text = f"{prefix} {best_timer.format_time()}"
                if self.menu_records_difficulty == self.settings['difficulty']:
                    self._refresh_menu_records()
                self.victory_saved = True

        if self.victory_triggered:
            self.particles.update(dt, self.maze, self.camera)
            self.water.update(dt)

        self.renderer.set_camera(self.camera.x, self.camera.y)
        self.renderer.set_ripples(self.ripples.ripples)

    def _try_advance_level(self, dt):
        self.victory_timer += dt
        max_level = max(LEVEL_CONFIGS.keys())
        if self.level_index >= max_level:
            return False
        if self.victory_timer < LEVEL_ADVANCE_DELAY:
            return False
        self.level_index += 1
        self.sound.stop_ambient()
        self._init_game()
        self.state = STATE_PLAYING
        return True

    def _save_settings(self):
        self.config_manager.save(self.settings)

    def _respawn(self):
        sx = self.start_pos[0] * CELL_SIZE + CELL_SIZE // 2
        sy = self.start_pos[1] * CELL_SIZE + CELL_SIZE // 2
        self.player.respawn(sx, sy)
        self.stone.pickup()
        self.ripples.ripples.clear()
        self.death_timer = 0
        self.death_particles_created = False
        self.step_sound_timer = 0
        self.fog.reveal_circle(sx, sy, CELL_SIZE * 2, self.fog.fade_time)
        self.camera.set_position(sx, sy)

    def _draw_game(self, mouse_pos):
        # Заливаем ВСЁ чёрным непрозрачным туманом
        # Потом "вырезаем" дыры там где видно
        self.screen.fill((4, 6, 10, 255))

        visible_ripples = [
            r for r in self.ripples.get_visible_ripples()
            if self._can_see_point(r.x, r.y)
        ]
        maze_h = len(self.maze)
        maze_w = len(self.maze[0])

        sx = max(0, int(self.camera.x // CELL_SIZE) - 1)
        sy = max(0, int(self.camera.y // CELL_SIZE) - 1)
        ex = min(maze_w, int((self.camera.x + SCREEN_WIDTH) // CELL_SIZE) + 2)
        ey = min(maze_h, int((self.camera.y + SCREEN_HEIGHT) // CELL_SIZE) + 2)

        vis_cache = {}

        def get_vis(cx, cy):
            key = (cx, cy)
            if key in vis_cache:
                return vis_cache[key]
            is_vis = self.fog.is_visible(cx, cy, self.player.x, self.player.y,
                                         visible_ripples, self.maze)
            vis_level = 0.0
            if is_vis:
                vis_level = self.fog.get_visibility(
                    cx, cy, self.player.x, self.player.y, self.maze)
                ccx = cx * CELL_SIZE + CELL_SIZE / 2
                ccy = cy * CELL_SIZE + CELL_SIZE / 2
                for r in visible_ripples:
                    if math.sqrt((ccx - r.x) ** 2 + (ccy - r.y) ** 2) <= r.radius:
                        if line_of_sight(r.x, r.y, ccx, ccy, self.maze):
                            vis_level = max(vis_level, 1.0)
                            break
            vis_cache[key] = (is_vis, vis_level)
            return (is_vis, vis_level)

        def is_wall(wx, wy):
            if not (0 <= wy < maze_h and 0 <= wx < maze_w):
                return True
            return self.maze[wy][wx] == '#'

        # === ПРОХОД 1: Пол ===
        # Видимые клетки делаем прозрачными — сквозь них видна OpenGL вода
        # Невидимые остаются чёрными (туман)
        for y in range(sy, ey):
            for x in range(sx, ex):
                if is_wall(x, y):
                    continue

                is_vis, vis = get_vis(x, y)
                scx, scy = self.camera.apply(x * CELL_SIZE, y * CELL_SIZE)
                rect = pygame.Rect(int(scx), int(scy), CELL_SIZE, CELL_SIZE)

                cell = self.maze[y][x]

                if cell == 'E':
                    if is_vis and vis > 0.01:
                        # Выход — полупрозрачный зелёный поверх воды
                        pulse = (math.sin(self.water.time * 3) + 1) / 2
                        ec = lerp_color(COLOR_EXIT, COLOR_WHITE, pulse * 0.4)
                        alpha = int(200 * vis)
                        pygame.draw.rect(self.screen,
                                         (int(ec[0]), int(ec[1]), int(ec[2]), alpha),
                                         rect)
                    continue

                if not is_vis or vis < 0.01:
                    # Невидимая клетка
                    # Пол невидим полностью; память показываем только по стенам.
                    continue

                # Видимая клетка пола — делаем прозрачной
                # alpha = 0 означает полностью прозрачно (вода видна)
                # Плавный переход на краях видимости
                if vis >= 0.95:
                    # Полностью открыто — полностью прозрачно
                    pygame.draw.rect(self.screen, (0, 0, 0, 0), rect)
                else:
                    # Края — частично затемнены
                    # vis=0.5 → alpha=130, vis=0.0 → alpha=255
                    fog_alpha = int(255 * (1.0 - vis))
                    pygame.draw.rect(self.screen, (0, 0, 0, 0), rect)
                    if fog_alpha > 10:
                        pygame.draw.rect(self.screen,
                                         (4, 6, 10, fog_alpha), rect)

        # === ПРОХОД 2: Грани стен (активно видимые) ===
        t = WALL_EDGE_THICKNESS
        for y in range(sy, ey):
            for x in range(sx, ex):
                if is_wall(x, y):
                    continue
                is_vis, vis = get_vis(x, y)
                if not is_vis or vis < 0.45:
                    continue

                wall_color = self.water.get_wall_color(x, y, vis)
                highlight = tuple(min(255, c + 30) for c in wall_color)

                if is_wall(x, y - 1):
                    wcx, wcy = self.camera.apply(x * CELL_SIZE, (y - 1) * CELL_SIZE)
                    pygame.draw.rect(self.screen, (*wall_color, 255),
                                     (wcx, wcy + CELL_SIZE - t, CELL_SIZE, t))
                    pygame.draw.line(self.screen, (*highlight, 255),
                                     (wcx, wcy + CELL_SIZE - 1),
                                     (wcx + CELL_SIZE - 1, wcy + CELL_SIZE - 1), 1)

                if is_wall(x, y + 1):
                    wcx, wcy = self.camera.apply(x * CELL_SIZE, (y + 1) * CELL_SIZE)
                    pygame.draw.rect(self.screen, (*wall_color, 255),
                                     (wcx, wcy, CELL_SIZE, t))
                    pygame.draw.line(self.screen, (*highlight, 255),
                                     (wcx, wcy), (wcx + CELL_SIZE - 1, wcy), 1)

                if is_wall(x - 1, y):
                    wcx, wcy = self.camera.apply((x - 1) * CELL_SIZE, y * CELL_SIZE)
                    pygame.draw.rect(self.screen, (*wall_color, 255),
                                     (wcx + CELL_SIZE - t, wcy, t, CELL_SIZE))
                    pygame.draw.line(self.screen, (*highlight, 255),
                                     (wcx + CELL_SIZE - 1, wcy),
                                     (wcx + CELL_SIZE - 1, wcy + CELL_SIZE - 1), 1)

                if is_wall(x + 1, y):
                    wcx, wcy = self.camera.apply((x + 1) * CELL_SIZE, y * CELL_SIZE)
                    pygame.draw.rect(self.screen, (*wall_color, 255),
                                     (wcx, wcy, t, CELL_SIZE))
                    pygame.draw.line(self.screen, (*highlight, 255),
                                     (wcx, wcy), (wcx, wcy + CELL_SIZE - 1), 1)

        # === ПРОХОД 3: Память стен ===
        mem_b = MEMORY_WALL_BRIGHTNESS
        for y in range(sy, ey):
            for x in range(sx, ex):
                if is_wall(x, y):
                    continue
                is_vis, vis = get_vis(x, y)
                if is_vis and vis > 0.01:
                    continue
                if not self.fog.is_remembered(x, y):
                    continue

                mem_color = (int(55 * mem_b), int(58 * mem_b), int(65 * mem_b), 255)

                if is_wall(x, y - 1) and self.fog.is_remembered(x, y - 1):
                    wcx, wcy = self.camera.apply(x * CELL_SIZE, (y - 1) * CELL_SIZE)
                    pygame.draw.rect(self.screen, mem_color,
                                     (wcx, wcy + CELL_SIZE - t, CELL_SIZE, t))
                if is_wall(x, y + 1) and self.fog.is_remembered(x, y + 1):
                    wcx, wcy = self.camera.apply(x * CELL_SIZE, (y + 1) * CELL_SIZE)
                    pygame.draw.rect(self.screen, mem_color,
                                     (wcx, wcy, CELL_SIZE, t))
                if is_wall(x - 1, y) and self.fog.is_remembered(x - 1, y):
                    wcx, wcy = self.camera.apply((x - 1) * CELL_SIZE, y * CELL_SIZE)
                    pygame.draw.rect(self.screen, mem_color,
                                     (wcx + CELL_SIZE - t, wcy, t, CELL_SIZE))
                if is_wall(x + 1, y) and self.fog.is_remembered(x + 1, y):
                    wcx, wcy = self.camera.apply((x + 1) * CELL_SIZE, y * CELL_SIZE)
                    pygame.draw.rect(self.screen, mem_color,
                                     (wcx, wcy, t, CELL_SIZE))

        self.exit_beacon.draw(self.screen, self.camera)
        self.particles.draw(self.screen, self.camera, self.fog,
                            self.player.x, self.player.y, visible_ripples, self.maze)
        self.particles.draw_fog_particles(self.screen, self.camera)
        self.ripples.draw(self.screen, self.camera, self.maze)

        if self.player.alive and self.stone_enabled:
            self.stone.draw(self.screen, self.camera, self.player.x, self.player.y,
                            mouse_pos[0], mouse_pos[1], self.fog, visible_ripples, self.maze)

        self.player.draw(self.screen, self.camera)

        if self.player.alive:
            self.player.wall_warning.draw(self.screen)

        # Вспышка ряби
        self.ripple_flash.draw(self.screen, self.camera)
        self._draw_glow_stone()
        self._draw_fireflies()
        self._draw_advanced_fog_overlay()
        self._draw_soft_fog_visual(visible_ripples)

        self.vignette.draw(self.screen)

        # UI
        if self.victory_triggered:
            next_level_text = None
            if self.level_index < max(LEVEL_CONFIGS.keys()):
                left = max(0.0, LEVEL_ADVANCE_DELAY - self.victory_timer)
                next_level_text = f"Следующий уровень через {left:.1f}с"
            self.victory_screen.draw(
                self.screen,
                self.timer,
                next_level_text,
                self.victory_record_text,
            )
        elif not self.player.alive:
            self._draw_death()
        else:
            if self.stone_enabled:
                self.game_ui.draw(self.screen, self.stone, self.player)
            self.timer.draw(self.screen)
            if not self.stone_enabled:
                hint_font = pygame.font.Font(None, 24)
                if self.glow_stone_mode:
                    hint = hint_font.render("3 Уровень | Найди светящийся камень [E]", True, (170, 210, 230))
                else:
                    hint = hint_font.render("2 Уровень | Ориентируйся на звук и слух", True, (130, 170, 200))
                self.screen.blit(hint, (15, SCREEN_HEIGHT - 30))

        if self.show_debug_overlay:
            self._draw_debug_overlay()

    def _draw_death(self):
        font = pygame.font.Font(None, 48)
        text = font.render("ПОГИБ", True, (255, 100, 100))
        self.screen.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50)))
        small_font = pygame.font.Font(None, 24)
        hint = small_font.render("Возврат к началу...", True, (150, 120, 120))
        self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))

    def _draw_debug_overlay(self):
        font = pygame.font.Font(None, 22)
        fps = self.clock.get_fps()
        lit_count = len([r for r in self.ripples.ripples if r.lit])
        lines = [
            f"FPS: {fps:.1f}",
            f"Level mode: {self.level_index} ({LEVEL_CONFIGS.get(self.level_index, {}).get('name', 'unknown')})",
            f"Player: ({self.player.x:.1f}, {self.player.y:.1f}) cell=({int(self.player.x // CELL_SIZE)}, {int(self.player.y // CELL_SIZE)})",
            f"Wall dist: {self.player._distance_to_nearest_wall(self.player.x, self.player.y, self.maze):.2f}",
            f"Fog active: {len(self.fog.active_cells)}",
            f"Stone enabled: {self.stone_enabled}",
            f"Stone state: held={self.stone.is_held} flying={self.stone.is_flying} ground={self.stone.is_on_ground}",
            f"Ripples: {len(self.ripples.ripples)} (lit {lit_count})",
            f"Water emitters: {len(self.water_emitters)}",
            f"Fireflies: {len(self.fireflies)}",
        ]
        y = 12
        for line in lines:
            text = font.render(line, True, (180, 220, 255))
            shadow = font.render(line, True, (15, 20, 28))
            self.screen.blit(shadow, (11, y + 1))
            self.screen.blit(text, (10, y))
            y += 20

    def _draw_fireflies(self):
        for firefly in self.fireflies:
            if not firefly['on']:
                continue
            if not self._can_see_point(firefly['x'], firefly['y']):
                continue
            sx, sy = self.camera.apply(firefly['x'], firefly['y'])
            pulse = (math.sin(pygame.time.get_ticks() * 0.01 + firefly['x'] * 0.01) + 1.0) * 0.5
            radius = int(5 + pulse * 3)
            glow_r = int(20 + pulse * 8)
            glow = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow, (180, 220, 120, 40), (glow_r, glow_r), glow_r)
            pygame.draw.circle(glow, (220, 255, 140, 120), (glow_r, glow_r), max(1, glow_r // 3))
            self.screen.blit(glow, (int(sx) - glow_r, int(sy) - glow_r))
            pygame.draw.circle(self.screen, (230, 255, 170), (int(sx), int(sy)), radius)

    def _near_glow_stone(self):
        if not self.glow_stone_spawn:
            return False
        return math.hypot(
            self.player.x - self.glow_stone_spawn['x'],
            self.player.y - self.glow_stone_spawn['y'],
        ) <= CELL_SIZE * 0.9

    def _draw_glow_stone(self):
        if not self.glow_stone_mode or self.glow_stone_found or not self.glow_stone_spawn:
            return
        if not self._can_see_point(self.glow_stone_spawn['x'], self.glow_stone_spawn['y']):
            return
        sx, sy = self.camera.apply(self.glow_stone_spawn['x'], self.glow_stone_spawn['y'])
        pulse = (math.sin(pygame.time.get_ticks() * 0.008) + 1.0) * 0.5
        radius = int(6 + pulse * 3)
        glow_r = int(24 + pulse * 10)
        glow = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow, (110, 200, 255, 45), (glow_r, glow_r), glow_r)
        pygame.draw.circle(glow, (170, 235, 255, 140), (glow_r, glow_r), max(1, glow_r // 3))
        self.screen.blit(glow, (int(sx) - glow_r, int(sy) - glow_r))
        pygame.draw.circle(self.screen, (200, 245, 255), (int(sx), int(sy)), radius)

    def _can_see_point(self, x, y):
        if not line_of_sight(self.player.x, self.player.y, x, y, self.maze):
            return False
        dx = x - self.player.x
        dy = y - self.player.y
        dist_sq = dx * dx + dy * dy
        if dist_sq < 1e-6:
            return True
        target_angle = math.atan2(dy, dx)
        delta = (target_angle - self.player.facing_angle + math.pi) % (2 * math.pi) - math.pi
        return abs(delta) <= self.view_half_angle

    def _draw_advanced_fog_overlay(self):
        if not FOG_ADVANCED_OVERLAY:
            return
        t = pygame.time.get_ticks() * 0.001
        sx = max(0, int(self.camera.x // CELL_SIZE) - 1)
        sy = max(0, int(self.camera.y // CELL_SIZE) - 1)
        ex = min(len(self.maze[0]), int((self.camera.x + SCREEN_WIDTH) // CELL_SIZE) + 2)
        ey = min(len(self.maze), int((self.camera.y + SCREEN_HEIGHT) // CELL_SIZE) + 2)
        fog_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for y in range(sy, ey):
            for x in range(sx, ex):
                if self.maze[y][x] == '#':
                    continue
                if self.fog.revealed[y][x] > 0:
                    continue
                wx = x * CELL_SIZE + CELL_SIZE * 0.5
                wy = y * CELL_SIZE + CELL_SIZE * 0.5
                n = math.sin(wx * FOG_OVERLAY_SCALE + t * 0.65) + math.cos(wy * FOG_OVERLAY_SCALE - t * 0.8)
                n *= 0.5
                alpha = int(max(0, min(255, FOG_OVERLAY_STRENGTH + 28 + n * 30)))
                if alpha <= 0:
                    continue
                sxp, syp = self.camera.apply(x * CELL_SIZE, y * CELL_SIZE)
                pygame.draw.rect(
                    fog_layer,
                    (0, 0, 0, alpha),
                    (int(sxp), int(syp), CELL_SIZE, CELL_SIZE),
                )
        self.screen.blit(fog_layer, (0, 0))

    def _draw_soft_fog_visual(self, visible_ripples):
        if not FOG_SOFT_VISUAL:
            return
        fog = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        fog.fill((0, 0, 0, FOG_SOFT_ALPHA))

        def cut_hole(world_x, world_y, radius_px, strength=1.0):
            sx, sy = self.camera.apply(world_x, world_y)
            max_r = int(max(1, radius_px))
            for i in range(5):
                r = int(max_r * (1.0 - i * 0.18))
                a = int((70 - i * 12) * strength)
                if r <= 0 or a <= 0:
                    continue
                pygame.draw.circle(fog, (0, 0, 0, a), (int(sx), int(sy)), r)

        cut_hole(self.player.x, self.player.y, CELL_SIZE * 2.4, 1.0)
        if self.glow_stone_mode and (self.stone.is_flying or self.stone.is_on_ground):
            cut_hole(self.stone.x, self.stone.y, CELL_SIZE * 1.8, 0.8)
        for r in visible_ripples[:6]:
            cut_hole(r.x, r.y, min(CELL_SIZE * 2.0, r.radius * 0.5), 0.5)

        self.screen.blit(fog, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)