// One droplet "landing": a soft gaussian blob at uPos (uv), strength uAmp. Drawn for a single frame per droplet.
uniform vec4 uPos;   // xy = position in 0..1
uniform vec4 uAmp;   // x = strength (0 = nothing)
out vec4 fragColor;
void main() {
    vec2 uv = vUV.st;
    float aspect = uTDOutputInfo.res.z / uTDOutputInfo.res.w;
    vec2 d = (uv - uPos.xy) * vec2(aspect, 1.0);
    float r = 0.09 + 0.07 * uAmp.x;
    float g = uAmp.x * exp(-dot(d, d) / (r * r));
    fragColor = TDOutputSwizzle(vec4(g, g, g, 1.0));
}
