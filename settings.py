from core.paths import settings_path

# ============== ЭКРАН ==============
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 800
CELL_SIZE = 35
FPS = 60

# ============== ЛАБИРИНТ ==============
MAZE_WIDTH = 31
MAZE_HEIGHT = 31
CORRIDOR_WIDTH = 2

# ============== ЦВЕТА ==============
COLOR_BLACK         = (0, 0, 0)
COLOR_WHITE         = (255, 255, 255)
COLOR_PLAYER        = (180, 210, 230)
COLOR_STONE         = (190, 175, 145)
COLOR_EXIT          = (100, 180, 120)
COLOR_RIPPLE        = (90, 120, 150)
COLOR_FOG           = (4, 6, 10, 0)      # RGBA прозрачный
COLOR_PLAYER_RIPPLE = (25, 45, 65)
COLOR_GRAY          = (42, 45, 52)
COLOR_DARK_GRAY     = (25, 28, 34)
COLOR_WARNING       = (160, 15, 15)

# Вода (используется WaterRenderer для выхода и стен)
COLOR_WATER_DEEP      = (8, 14, 22)
COLOR_WATER_LIGHT     = (18, 32, 48)
COLOR_WATER_HIGHLIGHT = (28, 48, 68)

# UI
COLOR_MENU_BG        = (6, 8, 14)
COLOR_BUTTON         = (30, 45, 70)
COLOR_BUTTON_HOVER   = (45, 68, 105)
COLOR_BUTTON_ACTIVE  = (55, 140, 90)
COLOR_BUTTON_TEXT    = (160, 185, 210)
COLOR_POWER_BAR_BG   = (20, 22, 28)
COLOR_POWER_BAR_FILL = (200, 170, 80)
COLOR_POWER_BAR_MAX  = (220, 80, 50)
COLOR_SEGMENT_EMPTY  = (30, 33, 42)
COLOR_SEGMENT_HOVER  = (55, 110, 165)

# ============== ИГРОК ==============
PLAYER_RADIUS        = 10
PLAYER_SPEED_WALK    = 1.5
PLAYER_SPEED_SPRINT  = 3.0

# Мини-рябь от игрока
PLAYER_RIPPLE_INTERVAL_IDLE   = 0.8
PLAYER_RIPPLE_INTERVAL_WALK   = 0.4
PLAYER_RIPPLE_INTERVAL_SPRINT = 0.2
PLAYER_RIPPLE_SPEED           = 35
PLAYER_RIPPLE_MAX_RADIUS      = 30

# След на воде
PLAYER_WAKE_LIFETIME = 1.2
PLAYER_WAKE_SPREAD   = 0.4
PLAYER_WAKE_OFFSET   = 8

# ============== КАМЕРА ==============
CAMERA_SMOOTHING = 0.1

# ============== КАМЕНЬ ==============
STONE_SPEED_MIN          = 3
STONE_SPEED_MAX          = 10
STONE_CHARGE_TIME        = 1.0
STONE_MAX_DISTANCE_MIN   = 10
STONE_MAX_DISTANCE_MAX   = 250
STONE_PICKUP_RADIUS      = 40
STONE_BOUNCE_DECAY       = 0.6
STONE_MAX_BOUNCES_MIN    = 0
STONE_MAX_BOUNCES_MAX    = 3

# ============== РЯБЬ ==============
RIPPLE_SPEED          = 80
RIPPLE_MAX_RADIUS_MIN = 10
RIPPLE_MAX_RADIUS_MAX = 200
RIPPLE_COUNT          = 3
RIPPLE_INTERVAL       = 0.45
RIPPLE_SEGMENTS       = 72
RIPPLE_THICKNESS      = 4

# ============== ТУМАН ВОЙНЫ ==============
FOG_FADE_TIME_BASE  = 6.0
FOG_PARTICLE_COUNT  = 8
FOG_ADVANCED_OVERLAY = False
FOG_OVERLAY_STRENGTH = 34
FOG_OVERLAY_SCALE = 0.013
FOG_SOFT_VISUAL = True
FOG_SOFT_ALPHA = 110

# ============== ВОДА ==============
WATER_WAVE_SPEED  = 1.5
WATER_WAVE_SCALE  = 0.3

# ============== ЧАСТИЦЫ ==============
DEATH_PARTICLE_COUNT    = 30
DEATH_PARTICLE_SPEED    = 120
DEATH_PARTICLE_LIFETIME = 1.2
BUBBLE_SPAWN_RATE       = 0.2
BUBBLE_SPEED            = 25
BUBBLE_LIFETIME         = 2.5
VICTORY_PARTICLE_COUNT  = 50

# ============== ВИНЬЕТКА ==============
VIGNETTE_STRENGTH = 0.82

# ============== ПРЕДУПРЕЖДЕНИЕ О СТЕНАХ ==============
WALL_WARNING_DISTANCE = 15
WALL_DANGER_DISTANCE  = 5

# ============== МАЯК ВЫХОДА ==============
EXIT_BEACON_DISTANCE = 7

# ============== ГРАНИ СТЕН ==============
WALL_EDGE_THICKNESS = 4

# ============== ПАМЯТЬ КАРТЫ ==============
MEMORY_WALL_BRIGHTNESS = 0.06

# ============== ВСПЫШКА РЯБИ ==============
RIPPLE_FLASH_DURATION  = 0.4
RIPPLE_FLASH_INTENSITY = 120
RIPPLE_FLASH_COLOR     = (80, 150, 255)

# ============== ЗВУК ==============
SOUND_STEP_INTERVAL_WALK   = 0.35
SOUND_STEP_INTERVAL_SPRINT = 0.2
SOUND_MAX_DISTANCE         = 400

# ============== СОСТОЯНИЯ ИГРЫ ==============
STATE_MENU     = 0
STATE_PLAYING  = 1
STATE_PAUSED   = 2
STATE_SETTINGS = 3
STATE_RECORDS  = 4

# ============== СЛОЖНОСТЬ ==============
DIFFICULTY_SETTINGS = {
    0: {
        'name':         'Легко',
        'fog_fade':     10.0,
        'speed_mult':   1.0,
        'maze_size':    21,
        'vision_radius': 1.8,
    },
    1: {
        'name':         'Нормально',
        'fog_fade':     6.0,
        'speed_mult':   1.0,
        'maze_size':    31,
        'vision_radius': 1.3,
    },
    2: {
        'name':         'Сложно',
        'fog_fade':     3.0,
        'speed_mult':   0.9,
        'maze_size':    41,
        'vision_radius': 0.9,
    },
}

DEFAULT_SETTINGS = {
    'master_volume': 0.7,
    'music_volume':  0.5,
    'sfx_volume':    0.8,
    'difficulty':    1,
}

SETTINGS_FILE_PATH = str(settings_path())

# ============== ОТЛАДКА ==============
DEBUG_OVERLAY_DEFAULT = False

# ============== РЕЖИМЫ УРОВНЯ ==============
LEVEL_CONFIGS = {
    1: {
        'name': 'Базовый',
        'stone_enabled': True,
        'water_emitters': 0,
        'fireflies': 0,
    },
    2: {
        'name': 'Эхо воды',
        'stone_enabled': False,
        'water_emitters': 8,
        'fireflies': 6,
    },
    3: {
        'name': 'Светящийся камень',
        'stone_enabled': False,
        'water_emitters': 0,
        'fireflies': 0,
        'vision_mult': 0.45,
    },
}

LEVEL_ADVANCE_DELAY = 2.5

# ============== ИСТОЧНИКИ ВОДЫ ==============
EMITTER_MIN_DISTANCE_CELLS = 6
EMITTER_SAFE_ZONE_CELLS = 4
EMITTER_RIPPLE_INTERVAL_MIN = 1.6
EMITTER_RIPPLE_INTERVAL_MAX = 2.8
EMITTER_SOUND_INTERVAL = 2.2

# ============== СВЕТЛЯЧКИ (ПРОТОТИП) ==============
FIREFLY_MIN_DISTANCE_CELLS = 5
FIREFLY_SAFE_ZONE_CELLS = 3
FIREFLY_ON_TIME = 5.0
FIREFLY_OFF_TIME = 5.0
FIREFLY_REVEAL_RADIUS_CELLS = 2.2
