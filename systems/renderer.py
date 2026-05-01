import moderngl
import pygame
import numpy as np
from array import array
from settings import CELL_SIZE
from core.paths import resource_dir


# Максимум рябей которые шейдер обрабатывает одновременно
# Больше не нужно — RIPPLE_COUNT = 3, и несколько бросков
MAX_RIPPLES = 16


class Renderer:
    """
    Рендерер на основе ModernGL.

    Слои (снизу вверх):
    1. Шейдер воды  — OpenGL, с динамическим светом от ряби
    2. Pygame surface — стены, туман, UI
    """

    DEFAULT_VERT_SHADER = """
        #version 330 core

        in vec2 in_position;

        out vec2 v_texcoord;
        out vec2 v_worldcoord;

        void main() {
            gl_Position = vec4(in_position, 0.0, 1.0);
            v_texcoord   = vec2(in_position.x * 0.5 + 0.5, -in_position.y * 0.5 + 0.5);
            v_worldcoord = in_position * 0.5 + 0.5;
        }
    """

    DEFAULT_WATER_FRAG_SHADER = """
        #version 330 core

        // ---- Базовые uniform ----
        uniform float time;
        uniform vec2  resolution;

        // ---- Камера ----
        uniform vec2  camera_pos;   // Позиция камеры в пикселях мира
        uniform float cell_size;    // Размер клетки в пикселях

        // ---- Рябь ----
        uniform int   ripple_count;
        uniform vec2  ripple_pos[16];    // Позиции в пикселях мира
        uniform float ripple_radius[16]; // Текущий радиус в пикселях
        uniform float ripple_max[16];    // Максимальный радиус
        uniform float ripple_lit[16];    // 1.0 = зажжена, 0.0 = нет

        in vec2 v_worldcoord;

        out vec4 f_color;

        // --------------------------------------------------------
        // Волна Герстнера
        // --------------------------------------------------------
        vec3 gerstner_wave(
            vec2 pos, vec2 direction,
            float amplitude, float wavelength, float speed
        ) {
            float k     = 2.0 * 3.14159 / wavelength;
            float phase = k * (dot(direction, pos) - speed * time);
            float s     = sin(phase);
            float c     = cos(phase);
            float steep = 0.5;
            return vec3(
                steep * amplitude * direction.x * c,
                steep * amplitude * direction.y * c,
                amplitude * s
            );
        }

        // --------------------------------------------------------
        // Шум
        // --------------------------------------------------------
        float hash(vec2 p) {
            p = fract(p * vec2(234.34, 435.345));
            p += dot(p, p + 34.23);
            return fract(p.x * p.y);
        }

        float noise(vec2 p) {
            vec2 i = floor(p);
            vec2 f = fract(p);
            f = f * f * (3.0 - 2.0 * f);
            float a = hash(i);
            float b = hash(i + vec2(1.0, 0.0));
            float c = hash(i + vec2(0.0, 1.0));
            float d = hash(i + vec2(1.0, 1.0));
            return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
        }

        float fbm(vec2 p) {
            float val  = 0.0;
            float amp  = 0.5;
            float freq = 1.0;
            for (int i = 0; i < 4; i++) {
                val  += noise(p * freq) * amp;
                freq *= 2.1;
                amp  *= 0.48;
            }
            return val;
        }

        void main() {
            // ---- Мировые координаты этого пикселя ----
            // v_worldcoord (0,0)-(1,1) → пиксели мира
            vec2 screen_px  = v_worldcoord * resolution;
            vec2 world_px   = screen_px + camera_pos;

            // ---- Координаты для волн ----
            vec2 pos = world_px / 80.0;

            // ---- Волны Герстнера ----
            vec3 wave_sum = vec3(0.0);
            wave_sum += gerstner_wave(pos, normalize(vec2( 1.0,  0.3)), 0.018, 3.2, 0.6);
            wave_sum += gerstner_wave(pos, normalize(vec2(-0.4,  1.0)), 0.012, 2.1, 0.45);
            wave_sum += gerstner_wave(pos, normalize(vec2( 0.7, -0.6)), 0.008, 1.4, 0.8);
            wave_sum += gerstner_wave(pos, normalize(vec2(-1.0,  0.5)), 0.005, 0.9, 1.1);
            float height = wave_sum.z;

            // ---- Нормаль ----
            vec2 eps = vec2(0.4, 0.0);
            vec3 wA  = vec3(0.0);
            vec3 wB  = vec3(0.0);
            wA += gerstner_wave(pos + eps.xy / 80.0, normalize(vec2( 1.0,  0.3)), 0.018, 3.2, 0.6);
            wA += gerstner_wave(pos + eps.xy / 80.0, normalize(vec2(-0.4,  1.0)), 0.012, 2.1, 0.45);
            wA += gerstner_wave(pos + eps.xy / 80.0, normalize(vec2( 0.7, -0.6)), 0.008, 1.4, 0.8);
            wA += gerstner_wave(pos + eps.xy / 80.0, normalize(vec2(-1.0,  0.5)), 0.005, 0.9, 1.1);
            wB += gerstner_wave(pos + eps.yx / 80.0, normalize(vec2( 1.0,  0.3)), 0.018, 3.2, 0.6);
            wB += gerstner_wave(pos + eps.yx / 80.0, normalize(vec2(-0.4,  1.0)), 0.012, 2.1, 0.45);
            wB += gerstner_wave(pos + eps.yx / 80.0, normalize(vec2( 0.7, -0.6)), 0.008, 1.4, 0.8);
            wB += gerstner_wave(pos + eps.yx / 80.0, normalize(vec2(-1.0,  0.5)), 0.005, 0.9, 1.1);
            vec3 normal = normalize(vec3(wA.z - height, wB.z - height, 0.08));

            // ---- Базовый цвет воды ----
            vec3 color_deep    = vec3(0.012, 0.022, 0.038);
            vec3 color_surface = vec3(0.025, 0.048, 0.078);
            float t_wave = clamp(height * 8.0 + 0.5, 0.0, 1.0);
            vec3 base_color = mix(color_deep, color_surface, t_wave);

            // ---- Пена ----
            float foam_threshold = 0.055;
            if (height > foam_threshold) {
                float foam_noise = fbm(pos * 2.0 + time * 0.15);
                float foam = smoothstep(foam_threshold,
                                        foam_threshold + 0.02,
                                        height + foam_noise * 0.015);
                vec3 foam_color = vec3(0.06, 0.09, 0.13);
                base_color = mix(base_color, foam_color, foam * 0.6);
            }

            // ---- Блики ----
            vec3 light_dir = normalize(vec3(0.3, 0.8, 1.0));
            float diffuse = max(0.0, dot(normal, light_dir));
            base_color += diffuse * 0.008;

            // ---- Мелкий шум ----
            float fine_noise = fbm(pos * 4.0 + time * 0.3) * 0.006;
            base_color += vec3(fine_noise * 0.6, fine_noise * 0.8, fine_noise);

            // ---- Глубина ----
            float depth_fade = 1.0 - length(v_worldcoord - 0.5) * 0.4;
            base_color *= depth_fade;

            // ====================================================
            // ДИНАМИЧЕСКИЙ СВЕТ ОТ РЯБИ
            // ====================================================
            vec3 ripple_light = vec3(0.0);

            for (int i = 0; i < ripple_count; i++) {
                // Только зажжённые ряби дают свет
                if (ripple_lit[i] < 0.5) continue;

                // Расстояние от пикселя до центра ряби (в пикселях мира)
                float dist = length(world_px - ripple_pos[i]);

                float radius  = ripple_radius[i];
                float max_rad = ripple_max[i];

                // Прогресс ряби: 0 = только появилась, 1 = исчезает
                float progress = radius / max_rad;

                // Яркость кольца — максимум у кольца, падает к центру и краям
                // Ширина кольца света = ~30px
                float ring_width = 30.0;
                float ring_dist  = abs(dist - radius);
                float ring_glow  = max(0.0, 1.0 - ring_dist / ring_width);

                // Заполнение внутри кольца — слабое
                float inner_glow = 0.0;
                if (dist < radius) {
                    inner_glow = (1.0 - dist / radius) * 0.15 * (1.0 - progress);
                }

                // Угасание со временем (чем больше радиус — тем тусклее)
                float fade = 1.0 - progress;
                fade = fade * fade; // Квадратичное угасание — резче

                // Итоговая интенсивность этой ряби
                float intensity = (ring_glow * 0.8 + inner_glow) * fade;

                // Цвет света — синевато-белый (как фосфоресценция воды)
                vec3 light_color = vec3(0.15, 0.35, 0.55);

                // Дополнительный эффект — рябь слегка искажает нормаль воды
                // Это создаёт блики на волнах вокруг кольца
                float normal_boost = ring_glow * fade * 0.3;
                float specular = pow(max(0.0, dot(normal, normalize(vec3(0.0, 0.0, 1.0)))),
                                     8.0) * normal_boost;

                ripple_light += light_color * intensity * 0.4 + vec3(specular);
            }

            base_color += ripple_light;

            // ---- Clamp чтобы не пересветить ----
            base_color = clamp(base_color, 0.0, 1.0);

            f_color = vec4(base_color, 1.0);
        }
    """

    DEFAULT_COMPOSITE_FRAG_SHADER = """
        #version 330 core

        uniform sampler2D game_texture;

        in vec2 v_texcoord;
        out vec4 f_color;

        void main() {
            f_color = texture(game_texture, v_texcoord);
        }
    """

    def __init__(self, width, height, debug=False):
        self.width  = width
        self.height = height
        self.time   = 0.0
        self.debug = debug

        # Данные ряби для шейдера
        self.ripple_positions = [(0.0, 0.0)] * MAX_RIPPLES
        self.ripple_radii     = [0.0] * MAX_RIPPLES
        self.ripple_maxes     = [1.0] * MAX_RIPPLES
        self.ripple_lit       = [0.0] * MAX_RIPPLES
        self.ripple_count     = 0

        # Позиция камеры
        self.camera_x = 0.0
        self.camera_y = 0.0

        self.ctx = moderngl.create_context()
        self.shader_dir = resource_dir("shaders")
        self.vert_shader_source = self._load_shader("water.vert", self.DEFAULT_VERT_SHADER)
        self.water_frag_shader_source = self._load_shader("water.frag", self.DEFAULT_WATER_FRAG_SHADER)
        self.composite_frag_shader_source = self._load_shader("composite.frag", self.DEFAULT_COMPOSITE_FRAG_SHADER)

        self.water_program = self.ctx.program(
            vertex_shader=self.vert_shader_source,
            fragment_shader=self.water_frag_shader_source,
        )
        self.composite_program = self.ctx.program(
            vertex_shader=self.vert_shader_source,
            fragment_shader=self.composite_frag_shader_source,
        )

        vertices = array('f', [
            -1.0,  1.0,
            -1.0, -1.0,
             1.0,  1.0,
             1.0, -1.0,
        ])
        self.vbo = self.ctx.buffer(vertices)

        self.water_vao = self.ctx.vertex_array(
            self.water_program,
            [(self.vbo, '2f', 'in_position')],
        )
        self.composite_vao = self.ctx.vertex_array(
            self.composite_program,
            [(self.vbo, '2f', 'in_position')],
        )

        self.game_texture = self.ctx.texture((width, height), 4)
        self.game_texture.filter = (moderngl.NEAREST, moderngl.NEAREST)

        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

        if self.debug:
            print(f"[Renderer] OpenGL {self.ctx.version_code // 100}."
                  f"{(self.ctx.version_code % 100) // 10}")
            print(f"[Renderer] GPU: {self.ctx.info['GL_RENDERER']}")

    def update(self, dt):
        self.time += dt

    def set_camera(self, camera_x, camera_y):
        """Обновляет позицию камеры для шейдера"""
        self.camera_x = camera_x
        self.camera_y = camera_y

    def set_ripples(self, ripples):
        """
        Принимает список объектов Ripple.
        Передаёт их данные в шейдер.
        """
        count = min(len(ripples), MAX_RIPPLES)
        self.ripple_count = count

        for i in range(MAX_RIPPLES):
            if i < count:
                r = ripples[i]
                self.ripple_positions[i] = (float(r.x), float(r.y))
                self.ripple_radii[i]     = float(r.radius)
                self.ripple_maxes[i]     = float(r.max_radius)
                self.ripple_lit[i]       = 1.0 if r.lit else 0.0
            else:
                self.ripple_positions[i] = (0.0, 0.0)
                self.ripple_radii[i]     = 0.0
                self.ripple_maxes[i]     = 1.0
                self.ripple_lit[i]       = 0.0

    def _upload_ripples_to_shader(self):
        """Загружает данные ряби в uniform переменные шейдера"""
        prog = self.water_program

        if 'ripple_count' in prog:
            prog['ripple_count'].value = self.ripple_count

        # Массивы uniform передаём поэлементно
        for i in range(MAX_RIPPLES):
            key_pos    = f'ripple_pos[{i}]'
            key_radius = f'ripple_radius[{i}]'
            key_max    = f'ripple_max[{i}]'
            key_lit    = f'ripple_lit[{i}]'

            if key_pos in prog:
                prog[key_pos].value    = self.ripple_positions[i]
            if key_radius in prog:
                prog[key_radius].value = self.ripple_radii[i]
            if key_max in prog:
                prog[key_max].value    = self.ripple_maxes[i]
            if key_lit in prog:
                prog[key_lit].value    = self.ripple_lit[i]

    def render(self, pygame_surface):
        self.ctx.clear(0.0, 0.0, 0.0, 1.0)

        # ---- Проход 1: Вода с динамическим светом ----
        prog = self.water_program
        if 'time'       in prog: prog['time'].value       = self.time
        if 'resolution' in prog: prog['resolution'].value = (float(self.width),
                                                              float(self.height))
        if 'camera_pos' in prog: prog['camera_pos'].value = (self.camera_x,
                                                              self.camera_y)
        if 'cell_size'  in prog: prog['cell_size'].value  = float(CELL_SIZE)

        self._upload_ripples_to_shader()
        self.water_vao.render(moderngl.TRIANGLE_STRIP)

        # ---- Проход 2: Pygame surface ----
        raw = pygame.image.tostring(pygame_surface, 'RGBA', False)
        self.game_texture.write(raw)
        self.game_texture.use(0)
        if 'game_texture' in self.composite_program:
            self.composite_program['game_texture'].value = 0
        self.composite_vao.render(moderngl.TRIANGLE_STRIP)

        if self.debug:
            print("Uniforms:", list(self.water_program._members.keys()))

        pygame.display.flip()

    def reload_shaders(self):
        """Перекомпилирует шейдеры в рантайме (например, по F5)."""
        try:
            self.vert_shader_source = self._load_shader("water.vert", self.DEFAULT_VERT_SHADER)
            self.water_frag_shader_source = self._load_shader("water.frag", self.DEFAULT_WATER_FRAG_SHADER)
            self.composite_frag_shader_source = self._load_shader("composite.frag", self.DEFAULT_COMPOSITE_FRAG_SHADER)
            old_water_program = self.water_program
            old_composite_program = self.composite_program
            old_water_vao = self.water_vao
            old_composite_vao = self.composite_vao

            self.water_program = self.ctx.program(
                vertex_shader=self.vert_shader_source,
                fragment_shader=self.water_frag_shader_source,
            )
            self.composite_program = self.ctx.program(
                vertex_shader=self.vert_shader_source,
                fragment_shader=self.composite_frag_shader_source,
            )

            self.water_vao = self.ctx.vertex_array(
                self.water_program,
                [(self.vbo, '2f', 'in_position')],
            )
            self.composite_vao = self.ctx.vertex_array(
                self.composite_program,
                [(self.vbo, '2f', 'in_position')],
            )

            old_water_vao.release()
            old_composite_vao.release()
            old_water_program.release()
            old_composite_program.release()

            if self.debug:
                print("[Renderer] Shaders reloaded")
        except Exception as exc:
            if self.debug:
                print(f"[Renderer] Shader reload failed: {exc}")

    def _load_shader(self, filename, fallback):
        shader_path = self.shader_dir / filename
        try:
            return shader_path.read_text(encoding="utf-8")
        except OSError:
            return fallback

    def release(self):
        self.water_vao.release()
        self.composite_vao.release()
        self.vbo.release()
        self.game_texture.release()
        self.water_program.release()
        self.composite_program.release()
