// nebula.glsl - Real-Time Generative Cosmic Nebula Shader for iOS Motion Controller
// Uniforms:
//   uOrientation: (pitch_norm, roll_norm, yaw_norm, time)
//   uMotion:      (deg_pitch, deg_roll, deg_yaw, shake_intensity)

uniform vec4 uOrientation; // [0..1] normalized channels + time
uniform vec4 uMotion;      // degrees (-90..90, -180..180, -180..180) + shake (0..1)

out vec4 fragColor;

// Simplex 2D noise helpers
vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec2 mod289(vec2 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec3 permute(vec3 x) { return mod289(((x*34.0)+1.0)*x); }

float snoise(vec2 v) {
    const vec4 C = vec4(0.211324865405187,  // (3.0-sqrt(3.0))/6.0
                        0.366025403784439,  // 0.5*(sqrt(3.0)-1.0)
                       -0.577350269189626,  // -1.0 + 2.0 * C.x
                        0.024390243902439); // 1.0 / 41.0
    vec2 i  = floor(v + dot(v, C.yy) );
    vec2 x0 = v -   i + dot(i, C.xx);
    vec2 i1;
    i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
    vec4 x12 = x0.xyxy + C.xxzz;
    x12.xy -= i1;
    i = mod289(i);
    vec3 p = permute( permute( i.y + vec3(0.0, i1.y, 1.0 ))
        + i.x + vec3(0.0, i1.x, 1.0 ));
    vec3 m = max(0.5 - vec3(dot(x0,x0), dot(x12.xy,x12.xy), dot(x12.zw,x12.zw)), 0.0);
    m = m*m ;
    m = m*m ;
    vec3 x = 2.0 * fract(p * C.www) - 1.0;
    vec3 h = abs(x) - 0.5;
    vec3 ox = floor(x + 0.5);
    vec3 a0 = x - ox;
    m *= 1.79284291400159 - 0.85373472095314 * ( a0*a0 + h*h );
    vec3 g;
    g.x  = a0.x  * x0.x  + h.x  * x0.y;
    g.yz = a0.yz * x12.xz + h.yz * x12.yw;
    return 130.0 * dot(m, g);
}

// Fractional Brownian Motion
float fbm(vec2 uv) {
    float val = 0.0;
    float amp = 0.5;
    float freq = 1.0;
    for (int i = 0; i < 5; i++) {
        val += amp * snoise(uv * freq);
        freq *= 2.1;
        amp *= 0.48;
    }
    return val;
}

void main() {
    vec2 res = uTDOutputInfo.res.zw;
    vec2 uv = (gl_FragCoord.xy - 0.5 * res) / min(res.x, res.y);

    float t = uOrientation.w * 0.25;
    float pitch_norm = uOrientation.x; // 0..1 (tilt up/down)
    float roll_norm  = uOrientation.y; // 0..1 (bank left/right)
    float yaw_norm   = uOrientation.z; // 0..1 (turn heading)
    float shake      = uMotion.w;      // 0..1 (shake magnitude)

    // 1. Phone Gimbal Transform: Rotate UV coordinates matching Roll angle
    float roll_rad = (roll_norm - 0.5) * 6.2831853;
    float cosR = cos(roll_rad);
    float sinR = sin(roll_rad);
    vec2 rot_uv = mat2(cosR, -sinR, sinR, cosR) * uv;

    // Shift UV center by Pitch and Yaw
    rot_uv.y += (pitch_norm - 0.5) * 1.5;
    rot_uv.x += (yaw_norm - 0.5) * 2.0;

    // 2. Multi-Layer Domain Warping driven by Shake
    float warp_strength = 0.8 + shake * 2.5;
    vec2 q = vec2(fbm(rot_uv + vec2(0.0, t * 0.1)), fbm(rot_uv + vec2(5.2, 1.3)));
    vec2 r = vec2(fbm(rot_uv + warp_strength * q + vec2(1.7, 9.2) + t * 0.15),
                  fbm(rot_uv + warp_strength * q + vec2(8.3, 2.8) + t * 0.12));

    float f = fbm(rot_uv + 2.0 * r);

    // 3. Dynamic Color Palette: Hue steered by Roll & Pitch
    vec3 col1 = vec3(0.05, 0.12, 0.28); // Deep Cosmic Navy
    vec3 col2 = vec3(0.85, 0.25, 0.65); // Vibrant Magenta
    vec3 col3 = vec3(0.15, 0.85, 0.95); // Electric Cyan
    vec3 col4 = vec3(1.00, 0.95, 0.70); // Radiant Core Starlight

    // Modulate palette weights with phone orientation
    vec3 nebula_col = mix(col1, col2, clamp(f * f * 3.5, 0.0, 1.0));
    nebula_col = mix(nebula_col, col3, clamp(length(q) * roll_norm * 1.5, 0.0, 1.0));
    nebula_col = mix(nebula_col, col4, clamp(pow(r.x, 3.0) * (0.8 + shake * 2.0), 0.0, 1.0));

    // 4. Central Glowing Core & Vignette
    float dist = length(uv);
    float core = exp(-dist * 3.0) * (0.4 + 1.2 * shake);
    nebula_col += col4 * core;

    // Subtle edge fade
    float vignette = smoothstep(1.4, 0.3, dist);
    nebula_col *= vignette;

    fragColor = TDOutputSwizzle(vec4(nebula_col, 1.0));
}
