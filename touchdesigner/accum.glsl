// Glow memory: keeps the brightest of (new droplet, previous glow * decay). Needs a 16-bit float format.
uniform vec4 uDecay; // x = per-frame decay
out vec4 fragColor;
void main() {
    vec2 uv = vUV.st;
    float now  = texture(sTD2DInputs[0], uv).r;
    float prev = texture(sTD2DInputs[1], uv).r;
    float g = max(now, prev * uDecay.x);
    fragColor = TDOutputSwizzle(vec4(g, g, g, 1.0));
}
