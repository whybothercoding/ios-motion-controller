// Night sky. Every star reads the droplet-glow texture at its own position and brightens/blooms with it.
uniform vec4 uTime;   // x = seconds
uniform vec4 uParams; // x = Speed (macro2), y = Color (macro4), z = Morph (macro1), w = Audio RMS
out vec4 fragColor;

float h21(vec2 p){ vec3 p3 = fract(vec3(p.xyx) * .1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
vec2  h22(vec2 p){ vec3 p3 = fract(vec3(p.xyx) * vec3(.1031, .1030, .0973)); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.xx + p3.yz) * p3.zy); }
float noise(vec2 p){ vec2 i = floor(p), f = fract(p); f = f*f*(3.-2.*f);
    return mix(mix(h21(i), h21(i+vec2(1,0)), f.x), mix(h21(i+vec2(0,1)), h21(i+vec2(1,1)), f.x), f.y); }
float fbm(vec2 p){ float a = .5, s = 0.; for(int i = 0; i < 5; i++){ s += a*noise(p); p *= 2.02; a *= .5; } return s; }

vec3 starLayer(vec2 uv, float aspect, float scale, float density, float rad, float seed, float t, float speed, float colorShift, float morph){
    vec2 q = uv * vec2(aspect, 1.) * scale;
    vec2 cell = floor(q);
    vec3 acc = vec3(0.);
    for (int j = -1; j <= 1; j++) for (int i = -1; i <= 1; i++) {
        vec2 c = cell + vec2(i, j);
        if (h21(c + seed) > density) continue;
        vec2 sp = c + 0.15 + 0.7 * h22(c + seed * 3.7);
        float mag = h21(c * 1.37 + seed * 9.1);
        float g = texture(sTD2DInputs[0], (sp / scale) / vec2(aspect, 1.)).r;   // droplet glow at this star
        float d2 = dot(q - sp, q - sp);
        float rr = rad * (0.5 + mag);
        float tw = 0.65 + 0.35 * sin(t * speed * (0.8 + 2.0 * mag) + mag * 40.);
        float base = 0.25 + 0.55 * mag * mag;
        float bright = base * tw + g * (4.0 + 3.0 * morph) * (0.5 + mag);
        float core = exp(-d2 / (rr * rr));
        float halo = exp(-d2 / (rr * rr * (6. + (30. + 40. * morph) * g))) * g;
        
        // Color palette morph: 0.0 = Ice Blue, 0.5 = Warm Bronze / Gold, 1.0 = Cosmic Magenta
        vec3 colCool = mix(vec3(0.65, 0.82, 1.0), vec3(0.85, 0.95, 1.0), h21(c + seed * 5.));
        vec3 colWarm = mix(vec3(1.0, 0.82, 0.45), vec3(1.0, 0.60, 0.30), h21(c + seed * 5.));
        vec3 colViolet = mix(vec3(0.95, 0.55, 1.0), vec3(0.65, 0.45, 1.0), h21(c + seed * 5.));
        vec3 tint = (colorShift < 0.5) 
            ? mix(colCool, colWarm, colorShift * 2.0)
            : mix(colWarm, colViolet, (colorShift - 0.5) * 2.0);
            
        acc += tint * (core * bright + halo * 0.7);
    }
    return acc;
}

void main() {
    vec2 uv = vUV.st;
    float aspect = uTDOutputInfo.res.z / uTDOutputInfo.res.w;
    float t = uTime.x;
    float glow = texture(sTD2DInputs[0], uv).r;

    // Parameters from Ableton
    float speed = 0.2 + 2.5 * clamp(uParams.x, 0.0, 1.0);
    float colorShift = clamp(uParams.y, 0.0, 1.0);
    float morph = clamp(uParams.z, 0.0, 1.0);
    float audioRms = clamp(uParams.w, 0.0, 1.0);

    // Deep space gradient
    vec3 col = mix(vec3(0.025, 0.035, 0.085), vec3(0.003, 0.005, 0.018), pow(uv.y, 0.7));
    
    // Cosmic dust / nebula (morph controls visibility & texture)
    float n = fbm(uv * vec2(aspect, 1.) * (2.0 + morph) + vec2(t * 0.01 * speed, 0.));
    vec3 nebulaTint = (colorShift < 0.5)
        ? mix(vec3(0.04, 0.07, 0.16), vec3(0.15, 0.09, 0.04), colorShift * 2.0)
        : mix(vec3(0.15, 0.09, 0.04), vec3(0.12, 0.04, 0.18), (colorShift - 0.5) * 2.0);
        
    col += nebulaTint * pow(n, 2.8 - 1.2 * morph) * (0.8 + 1.2 * audioRms);
    col += (nebulaTint * 2.0 + vec3(0.08)) * glow * (0.35 + n) * (0.6 + 0.4 * morph);

    // Star layers
    col += starLayer(uv, aspect, 12., 0.35 + 0.15 * morph, 0.05, 1., t, speed, colorShift, morph);
    col += starLayer(uv, aspect, 28., 0.40 + 0.10 * morph, 0.07, 2., t, speed, colorShift, morph);
    col += starLayer(uv, aspect, 55., 0.45, 0.10, 3., t, speed, colorShift, morph);

    // Tone curve & soft vignette
    col = 1. - exp(-col * (1.2 + 0.5 * morph));
    col *= 1. - 0.35 * dot(uv - .5, uv - .5);
    fragColor = TDOutputSwizzle(vec4(col, 1.));
}
