import os
import math
import random
import struct
import pygame
from core.paths import resource_dir, user_data_dir


# ============== ПАПКИ СО ЗВУКАМИ ==============
RESOURCE_SOUND_DIR = str(resource_dir("sounds"))
USER_SOUND_DIR = str(user_data_dir() / "sounds")

# Маппинг: имя звука → имя файла (без расширения)
# Система ищет .wav, потом .mp3, потом .ogg
SOUND_FILES = {
    'throw':        'throw',
    'bounce':       'bounce',
    'splash':       'splash',
    'ripple':       'ripple',
    'ripple_flash': 'ripple_flash',
    'step1':        'step1',
    'step2':        'step2',
    'death':        'death',
    'victory':      'victory',
    'pickup':       'pickup',
    'ambient':      'ambient',
    'waterfall':    'waterfall',
    'firefly':      'firefly',
}

SUPPORTED_FORMATS = ('.wav', '.mp3', '.ogg')


# ============== ПРОЦЕДУРНАЯ ГЕНЕРАЦИЯ (FALLBACK) ==============

def _generate_sound(sample_rate=44100, duration=0.2, volume=0.5, generator=None):
    num_samples = int(sample_rate * duration)
    samples = []
    for i in range(num_samples):
        t = i / sample_rate
        value = generator(t, duration) if generator else 0
        fade = min(1.0, t * 200) * min(1.0, (duration - t) * 200)
        value = max(-1.0, min(1.0, value * volume * fade))
        samples.append(int(value * 32767))
    buf = struct.pack(f'<{len(samples)}h', *samples)
    return pygame.mixer.Sound(buffer=buf)


def _gen_throw(t, dur):
    freq = 400 * math.exp(-t * 15)
    env = math.exp(-t * 12)
    return math.sin(2 * math.pi * freq * t) * env * 0.6


def _gen_bounce(t, dur):
    freq = 800 * math.exp(-t * 25)
    env = math.exp(-t * 30)
    noise = (random.random() * 2 - 1) * math.exp(-t * 20) * 0.3
    return (math.sin(2 * math.pi * freq * t) * 0.7 + noise) * env


def _gen_splash(t, dur):
    hit_env = 1.0 if t < 0.02 else math.exp(-(t - 0.02) * 200)
    hit_noise = (random.random() * 2 - 1) * 0.8 * hit_env
    slap = math.sin(2 * math.pi * 1200 * t) * math.exp(-t * 150) * 0.5
    plunge_freq = 200 * math.exp(-t * 12) + 60
    plunge = math.sin(2 * math.pi * plunge_freq * t) * math.exp(-t * 5) * 0.6
    bubbles = 0.0
    if t > 0.05:
        bubble_freq = 400 + 800 * (t - 0.05) / (dur - 0.05)
        bubble_env = math.exp(-(t - 0.05) * 10) * max(0, math.sin((t - 0.05) * math.pi * 20))
        bubbles = math.sin(2 * math.pi * bubble_freq * t) * bubble_env * 0.3
        bubbles += math.sin(2 * math.pi * (bubble_freq * 0.7) * t) * bubble_env * 0.2
    master_env = math.exp(-t * 6)
    signal = (hit_noise + slap + plunge + bubbles) * master_env
    return max(-1.0, min(1.0, signal * 0.8))


def _gen_ripple(t, dur):
    env = math.sin(math.pi * t / dur)
    wave = math.sin(2 * math.pi * 250 * t) * 0.2
    wave += math.sin(2 * math.pi * 380 * t) * 0.15
    shimmer = math.sin(2 * math.pi * 600 * t + math.sin(t * 40) * 2) * 0.1
    return (wave + shimmer) * env * 0.6


def _gen_step(t, dur):
    env = math.exp(-t * 15)
    noise = (random.random() * 2 - 1) * 0.6
    low = math.sin(2 * math.pi * 100 * t) * 0.3
    return (noise + low) * env * 0.4


def _gen_death(t, dur):
    freq = 120 * math.exp(-t * 3)
    env = math.exp(-t * 4)
    hit = math.sin(2 * math.pi * freq * t) * 0.6
    crack = (random.random() * 2 - 1) * math.exp(-t * 15) * 0.5
    rumble = math.sin(2 * math.pi * 40 * t) * env * 0.3
    return (hit + crack + rumble) * env


def _gen_victory(t, dur):
    note1 = math.sin(2 * math.pi * 523 * t) * max(0, 1 - t * 2)
    note2 = math.sin(2 * math.pi * 659 * t) * max(0, min(1, t * 4 - 0.5))
    note3 = math.sin(2 * math.pi * 784 * t) * max(0, min(1, t * 3 - 1))
    env = min(1, t * 5) * max(0, 1 - (t / dur) * 0.5)
    return (note1 + note2 + note3) * env * 0.25


def _gen_pickup(t, dur):
    freq = 400 + 400 * t / dur
    env = math.exp(-t * 6)
    return math.sin(2 * math.pi * freq * t) * env * 0.4


def _gen_ambient(t, dur):
    wave1 = math.sin(2 * math.pi * 40 * t + math.sin(t * 0.7) * 3) * 0.15
    wave2 = math.sin(2 * math.pi * 65 * t + math.sin(t * 1.1) * 2) * 0.1
    noise_raw = random.random() * 2 - 1
    noise_env = (math.sin(t * 2.5) * 0.3 + 0.7)
    noise = noise_raw * 0.08 * noise_env
    drop = 0
    drop_times = [0.8, 2.1, 3.5, 4.2, 5.7, 6.9, 7.4]
    for dt_drop in drop_times:
        local_t = t - dt_drop
        if 0 < local_t < 0.05:
            drop += math.sin(2 * math.pi * (800 + 400 * local_t) * local_t) * math.exp(
                -local_t * 60) * 0.15
    loop_fade = 1.0
    fade_zone = 0.5
    if t < fade_zone:
        loop_fade = t / fade_zone
    elif t > dur - fade_zone:
        loop_fade = (dur - t) / fade_zone
    return (wave1 + wave2 + noise + drop) * loop_fade


def _gen_ripple_flash(t, dur):
    env = math.exp(-t * 8)
    freq = 300 + 500 * (t / dur)
    main = math.sin(2 * math.pi * freq * t) * 0.3
    harm = math.sin(2 * math.pi * freq * 2 * t) * 0.1 * env
    shimmer = math.sin(2 * math.pi * 1200 * t + math.sin(t * 80) * 3) * 0.08 * env
    return (main + harm + shimmer) * env


def _gen_waterfall(t, dur):
    low = math.sin(2 * math.pi * 90 * t + math.sin(t * 3.5) * 1.5) * 0.08
    mid = math.sin(2 * math.pi * 180 * t + math.sin(t * 5.2) * 2.0) * 0.05
    noise = (random.random() * 2 - 1) * 0.12
    flutter = (math.sin(t * 7.5) * 0.25 + 0.75)
    return (low + mid + noise) * flutter


def _gen_firefly(t, dur):
    env = math.exp(-t * 7.0)
    chirp = math.sin(2 * math.pi * (850 + 500 * t) * t) * 0.18
    shimmer = math.sin(2 * math.pi * 1400 * t + math.sin(t * 25) * 1.2) * 0.08
    return (chirp + shimmer) * env


# Fallback генераторы: имя → (duration, volume, generator)
FALLBACK_GENERATORS = {
    'throw':        (0.15, 0.5, _gen_throw),
    'bounce':       (0.1,  0.6, _gen_bounce),
    'splash':       (0.35, 0.5, _gen_splash),
    'ripple':       (0.5,  0.3, _gen_ripple),
    'ripple_flash': (0.3,  0.35, _gen_ripple_flash),
    'step1':        (0.08, 0.2, _gen_step),
    'step2':        (0.1,  0.2, _gen_step),
    'death':        (0.5,  0.7, _gen_death),
    'victory':      (1.0,  0.5, _gen_victory),
    'pickup':       (0.2,  0.4, _gen_pickup),
    'ambient':      (8.0,  0.15, _gen_ambient),
    'waterfall':    (1.0,  0.18, _gen_waterfall),
    'firefly':      (0.28, 0.22, _gen_firefly),
}


# ============== МЕНЕДЖЕР ЗВУКА ==============

class SoundManager:
    """
    Загружает звуки из папки sounds/.
    Поддерживает .wav, .mp3, .ogg.
    Если файл не найден — генерирует процедурно.

    Структура папки sounds/:
        sounds/
        ├── throw.wav        (или .mp3, .ogg)
        ├── bounce.wav
        ├── splash.wav
        ├── ripple.wav
        ├── ripple_flash.wav
        ├── step1.wav
        ├── step2.wav
        ├── death.wav
        ├── victory.wav
        ├── pickup.wav
        └── ambient.mp3      (фоновый, зацикленный)
    """

    def __init__(self, settings):
        self.settings = settings
        self.sounds = {}
        self.ambient_channel = None
        self.step_index = 0
        self.audio_enabled = False
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            pygame.mixer.set_num_channels(16)
            self.audio_enabled = True
        except pygame.error as exc:
            print(f"[Sound] Аудио отключено: {exc}")
            return
        self._load_all()

    def _find_file(self, base_name):
        """Ищет файл с любым поддерживаемым расширением"""
        for sound_dir in (USER_SOUND_DIR, RESOURCE_SOUND_DIR):
            for ext in SUPPORTED_FORMATS:
                path = os.path.join(sound_dir, base_name + ext)
                if os.path.exists(path):
                    return path
        return None

    def _load_all(self):
        """Загружает все звуки: файл если есть, иначе генерация"""
        if not self.audio_enabled:
            return
        # Папка пользовательских override-звуков
        if not os.path.exists(USER_SOUND_DIR):
            try:
                os.makedirs(USER_SOUND_DIR)
                print(f"[Sound] Создана папка пользовательских звуков: {USER_SOUND_DIR}")
            except OSError as exc:
                print(f"[Sound] Не удалось создать папку пользовательских звуков: {exc}")

        loaded_count = 0
        generated_count = 0

        for name, file_base in SOUND_FILES.items():
            path = self._find_file(file_base)

            if path:
                try:
                    self.sounds[name] = pygame.mixer.Sound(path)
                    loaded_count += 1
                    print(f"  ✓ Файл:     {os.path.basename(path)}")
                except Exception as e:
                    print(f"  ✗ Ошибка:   {os.path.basename(path)} — {e}")
                    self._generate_fallback(name)
                    generated_count += 1
            else:
                self._generate_fallback(name)
                generated_count += 1

        print(f"[Sound] Загружено: {loaded_count} файлов, "
              f"сгенерировано: {generated_count} звуков")

    def _generate_fallback(self, name):
        """Генерирует процедурный звук как замену отсутствующему файлу"""
        if not self.audio_enabled:
            return
        if name in FALLBACK_GENERATORS:
            dur, vol, gen = FALLBACK_GENERATORS[name]
            self.sounds[name] = _generate_sound(duration=dur, volume=vol, generator=gen)
            print(f"  ~ Генерация: {name}")
        else:
            # Тихая заглушка
            self.sounds[name] = _generate_sound(duration=0.01, volume=0, generator=lambda t, d: 0)
            print(f"  ? Заглушка:  {name}")

    def reload(self):
        """Перезагрузить все звуки (после добавления новых файлов)"""
        if not self.audio_enabled:
            return
        print("[Sound] Перезагрузка...")
        self._load_all()

    def _get_volume(self, base=1.0):
        master = self.settings.get('master_volume', 0.7)
        sfx = self.settings.get('sfx_volume', 0.8)
        return base * master * sfx

    def play(self, name, volume=1.0):
        if not self.audio_enabled:
            return
        if name not in self.sounds:
            return
        sound = self.sounds[name]
        sound.set_volume(self._get_volume(volume))
        sound.play()

    def play_spatial(self, name, source_x, source_y, listener_x, listener_y,
                     max_distance=400, base_volume=1.0):
        if not self.audio_enabled:
            return
        if name not in self.sounds:
            return
        dx = source_x - listener_x
        dy = source_y - listener_y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist > max_distance:
            return
        volume = max(0, 1.0 - (dist / max_distance) ** 0.7)
        final_vol = self._get_volume(volume * base_volume)
        if final_vol < 0.01:
            return
        sound = self.sounds[name]
        channel = sound.play()
        if channel:
            if dist > 1:
                pan = max(-1, min(1, dx / (max_distance * 0.5)))
                left = final_vol * min(1.0, 1.0 - pan * 0.7)
                right = final_vol * min(1.0, 1.0 + pan * 0.7)
                channel.set_volume(max(0, left), max(0, right))
            else:
                channel.set_volume(final_vol, final_vol)

    def play_step(self, player_x, player_y):
        name = 'step1' if self.step_index % 2 == 0 else 'step2'
        self.step_index += 1
        self.play(name, volume=0.3)

    def start_ambient(self):
        if not self.audio_enabled:
            return
        if 'ambient' in self.sounds:
            vol = self._get_volume(0.3)
            self.ambient_channel = self.sounds['ambient'].play(-1)
            if self.ambient_channel:
                self.ambient_channel.set_volume(vol, vol)

    def stop_ambient(self):
        if not self.audio_enabled:
            return
        if self.ambient_channel:
            self.ambient_channel.stop()
            self.ambient_channel = None

    def update_ambient_volume(self):
        if not self.audio_enabled:
            return
        if self.ambient_channel:
            vol = self._get_volume(0.3)
            self.ambient_channel.set_volume(vol, vol)

    def update(self, dt):
        pass
