# driver.py - Universal Motion Controller Driver for TouchDesigner
# Supports both:
# 1. Droplet Sky generative starfield (already wired in motion_visuals.toe)
# 2. 3D Camera Gimbal & GLSL Nebula

import math
import random
import time

_last_p = 0.0
_last_r = 0.0
_last_y = 0.0
_shake = 0.0
_last_flash_time = 0.0

HALF_PI = math.pi / 2.0
PI = math.pi
TWO_PI = 2.0 * math.pi
RAD_TO_DEG = 180.0 / math.pi


def onFrameStart(frame):
    global _last_p, _last_r, _last_y, _shake, _last_flash_time

    p1 = op('/project1') or op('.')
    osc = p1.op('oscin1')
    if not osc:
        return

    # Check for phone orientation channels (TouchDesigner formats: phone/orientation1, 2, 3)
    ch_p = osc.chan('phone/orientation1') or osc.chan('*orientation*1') or osc.chan('pitch')
    ch_r = osc.chan('phone/orientation2') or osc.chan('*orientation*2') or osc.chan('roll')
    ch_y = osc.chan('phone/orientation3') or osc.chan('*orientation*3') or osc.chan('yaw')

    if ch_p is None or ch_r is None or ch_y is None:
        # Fallback if phone/orientation is the only stream
        if len(osc.chans()) >= 3 and not osc.chan('live/rms'):
            p_raw = float(osc[0].eval())
            r_raw = float(osc[1].eval())
            y_raw = float(osc[2].eval())
        else:
            return
    else:
        p_raw = float(ch_p.eval())
        r_raw = float(ch_r.eval())
        y_raw = float(ch_y.eval())

    # 1. Normalization [0.0, 1.0]
    p_norm = max(0.0, min(1.0, (p_raw + HALF_PI) / PI))
    r_norm = max(0.0, min(1.0, (r_raw + PI) / TWO_PI))
    y_norm = max(0.0, min(1.0, (y_raw + PI) / TWO_PI))

    # 2. Degrees for 3D Camera / Angle transforms
    p_deg = p_raw * RAD_TO_DEG
    r_deg = r_raw * RAD_TO_DEG
    y_deg = y_raw * RAD_TO_DEG

    # 3. Dynamic Shake / Angular Velocity Detection
    dp = abs(p_raw - _last_p)
    dr = abs(r_raw - _last_r)
    dy = abs(y_raw - _last_y)
    _last_p = p_raw
    _last_r = r_raw
    _last_y = y_raw

    instant_velocity = dp + dr + dy
    _shake = max(instant_velocity * 4.0, _shake * 0.90)
    _shake = min(1.0, _shake)

    now = time.time()

    # -------------------------------------------------------------
    # 4. Drive Starry Sky Scene (sky_sky, sky_flash, sky_accum)
    # -------------------------------------------------------------
    sky = p1.op('sky_sky')
    if sky:
        sky.par.vec1name = 'uParams'
        sky.par.vec1valuex = 0.2 + y_norm * 1.5   # Speed / Twinkle driven by Yaw
        sky.par.vec1valuey = r_norm               # Palette Shift (Blue->Bronze->Violet) driven by Roll
        sky.par.vec1valuez = p_norm               # Morph / Nebula Density driven by Pitch
        sky.par.vec1valuew = _shake               # Star Brightness boost driven by Shake

    accum = p1.op('sky_accum')
    if accum:
        accum.par.vec0name = 'uDecay'
        accum.par.vec0valuex = 0.92 + 0.07 * (1.0 - _shake * 0.5)

    flash = p1.op('sky_flash')
    if flash:
        # Trigger star flash on shake impulse or tap
        if _shake > 0.35 and (now - _last_flash_time) > 0.12:
            _last_flash_time = now
            flash.par.vec0name = 'uPos'
            flash.par.vec0valuex = max(0.1, min(0.9, r_norm + random.uniform(-0.1, 0.1)))
            flash.par.vec0valuey = max(0.1, min(0.9, p_norm + random.uniform(-0.1, 0.1)))
            flash.par.vec1name = 'uAmp'
            flash.par.vec1valuex = min(1.0, 0.4 + _shake * 0.8)
        else:
            flash.par.vec1name = 'uAmp'
            flash.par.vec1valuex = 0.0

    # -------------------------------------------------------------
    # 5. Drive GLSL Nebula / 3D Gimbal Scene (if present)
    # -------------------------------------------------------------
    nebula = p1.op('glsl_nebula')
    if nebula:
        nebula.par.vec0name = 'uOrientation'
        nebula.par.vec0valuex = p_norm
        nebula.par.vec0valuey = r_norm
        nebula.par.vec0valuez = y_norm
        nebula.par.vec0valuew = abs(now % 10000.0)

        nebula.par.vec1name = 'uMotion'
        nebula.par.vec1valuex = p_deg
        nebula.par.vec1valuey = r_deg
        nebula.par.vec1valuez = y_deg
        nebula.par.vec1valuew = _shake

    cam = p1.op('cam1')
    if cam:
        cam.par.rx = p_deg
        cam.par.ry = y_deg
        cam.par.rz = -r_deg
