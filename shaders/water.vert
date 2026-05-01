#version 330 core

in vec2 in_position;

out vec2 v_texcoord;
out vec2 v_worldcoord;

void main() {
    gl_Position = vec4(in_position, 0.0, 1.0);
    // UV из позиции (как у прежнего буфера 2f+2f), иначе на части драйверов
    // in_texcoord выкидывается из программы water+frag — там v_texcoord не читается.
    v_texcoord   = vec2(in_position.x * 0.5 + 0.5, -in_position.y * 0.5 + 0.5);
    v_worldcoord = in_position * 0.5 + 0.5;
}
