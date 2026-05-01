#version 330 core

uniform float time;
uniform vec2  resolution;
uniform vec2  camera_pos;
uniform float cell_size;
uniform int   ripple_count;
uniform vec2  ripple_pos[16];
uniform float ripple_radius[16];
uniform float ripple_max[16];
uniform float ripple_lit[16];

in vec2 v_worldcoord;
out vec4 f_color;

vec3 gerstner_wave(vec2 pos, vec2 direction, float amplitude, float wavelength, float speed) {
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
    vec2 screen_px  = v_worldcoord * resolution;
    vec2 world_px   = screen_px + camera_pos;
    vec2 pos = world_px / 80.0;

    vec3 wave_sum = vec3(0.0);
    wave_sum += gerstner_wave(pos, normalize(vec2( 1.0,  0.3)), 0.018, 3.2, 0.6);
    wave_sum += gerstner_wave(pos, normalize(vec2(-0.4,  1.0)), 0.012, 2.1, 0.45);
    wave_sum += gerstner_wave(pos, normalize(vec2( 0.7, -0.6)), 0.008, 1.4, 0.8);
    wave_sum += gerstner_wave(pos, normalize(vec2(-1.0,  0.5)), 0.005, 0.9, 1.1);
    float height = wave_sum.z;

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

    vec3 color_deep    = vec3(0.012, 0.022, 0.038);
    vec3 color_surface = vec3(0.025, 0.048, 0.078);
    float t_wave = clamp(height * 8.0 + 0.5, 0.0, 1.0);
    vec3 base_color = mix(color_deep, color_surface, t_wave);

    float foam_threshold = 0.055;
    if (height > foam_threshold) {
        float foam_noise = fbm(pos * 2.0 + time * 0.15);
        float foam = smoothstep(foam_threshold, foam_threshold + 0.02, height + foam_noise * 0.015);
        vec3 foam_color = vec3(0.06, 0.09, 0.13);
        base_color = mix(base_color, foam_color, foam * 0.6);
    }

    vec3 light_dir = normalize(vec3(0.3, 0.8, 1.0));
    float diffuse = max(0.0, dot(normal, light_dir));
    base_color += diffuse * 0.008;
    float fine_noise = fbm(pos * 4.0 + time * 0.3) * 0.006;
    base_color += vec3(fine_noise * 0.6, fine_noise * 0.8, fine_noise);
    float depth_fade = 1.0 - length(v_worldcoord - 0.5) * 0.4;
    base_color *= depth_fade;

    vec3 ripple_light = vec3(0.0);
    for (int i = 0; i < ripple_count; i++) {
        if (ripple_lit[i] < 0.5) continue;
        float dist = length(world_px - ripple_pos[i]);
        float radius  = ripple_radius[i];
        float max_rad = ripple_max[i];
        float progress = radius / max_rad;
        float ring_width = 30.0;
        float ring_dist  = abs(dist - radius);
        float ring_glow  = max(0.0, 1.0 - ring_dist / ring_width);
        float inner_glow = 0.0;
        if (dist < radius) {
            inner_glow = (1.0 - dist / radius) * 0.15 * (1.0 - progress);
        }
        float fade = 1.0 - progress;
        fade = fade * fade;
        float intensity = (ring_glow * 0.8 + inner_glow) * fade;
        vec3 light_color = vec3(0.15, 0.35, 0.55);
        float normal_boost = ring_glow * fade * 0.3;
        float specular = pow(max(0.0, dot(normal, normalize(vec3(0.0, 0.0, 1.0)))), 8.0) * normal_boost;
        ripple_light += light_color * intensity * 0.4 + vec3(specular);
    }

    base_color += ripple_light;
    base_color = clamp(base_color, 0.0, 1.0);
    f_color = vec4(base_color, 1.0);
}
