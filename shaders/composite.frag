#version 330 core

uniform sampler2D game_texture;

in vec2 v_texcoord;
out vec4 f_color;

void main() {
    f_color = texture(game_texture, v_texcoord);
}
