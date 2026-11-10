# iOS Motion Controller (Demo 3) 📱✨🎛️

An expressive, low-latency audiovisual controller bridging a custom iOS CoreMotion app to **Ableton Live 12** and **TouchDesigner**.

Utilizes 3-axis continuous spatial orientation (`/phone/orientation [pitch, roll, yaw]`) streamed over Wi-Fi UDP at 30 FPS to simultaneously manipulate sound synthesis in Live and generative 3D visuals in TouchDesigner.

---

## Architecture Overview

```
                      ┌─────────────────────────────────┐
                      │           iOS Device            │
                      │   /phone/orientation [p, r, y]  │
                      └────────────────┬────────────────┘
                                       │ UDP Wi-Fi (30 FPS)
                                       │ :9000
                                       ▼
                      ┌─────────────────────────────────┐
                      │            relay.py             │
                      │  High-Performance UDP Splitter  │
                      └────────┬───────────────┬────────┘
                               │               │
                 UDP Port :8000│               │ UDP Port :8001
                               ▼               ▼
           ┌───────────────────────┐       ┌───────────────────────┐
           │     TouchDesigner     │       │     Ableton Live      │
           │  (motion_visuals.toe) │       │ (Motion_Receiver.amxd)│
           ├───────────────────────┤       ├───────────────────────┤
           │ • 1:1 Gimbal Camera   │       │ • CoreMotion [0..1]   │
           │ • Cosmic Nebula GLSL  │       │ • Tare / Zero button  │
           │ • Angular shake burst │       │ • Jitter slide filter │
           │ • Dynamic Hue Shift   │       │ • 6 Mappable controls │
           └───────────────────────┘       └───────────────────────┘
```

---

## Features

### 1. Ableton Live: `Motion_Receiver.amxd`
- **Zero-Latency Audio Pass-Through:** `plugin~` to `plugout~` stereo routing. Drop onto any audio track, return track, instrument, or the master bus.
- **Accurate CoreMotion Math:** Automatically translates CoreMotion Radians to normalized `[0.0, 1.0]` with sub-millimeter precision.
- **One-Click Tare / Zeroing:** Press **TARE** while holding your phone in whatever posture feels natural; that position instantly becomes the 50% neutral center point.
- **Wi-Fi Jitter Smoothing:** Adjustable `Smooth` dial (slide filter) converts 30 FPS discrete packets into silky 60+ FPS parameter sweeps.
- **6 Parameter Mapping Matrix:**
  - **PITCH (Nodding forward/back):** 2 independent mapping slots (**P1**, **P2**)
  - **ROLL (Tilting left/right):** 2 independent mapping slots (**R1**, **R2**)
  - **YAW (Heading/Compass rotation):** 2 independent mapping slots (**Y1**, **Y2**)
  - Each slot features:
    - **Map:** Click to activate, then click any knob/slider in Live to link.
    - **✕ (Unmap):** Instantly disconnects parameter.
    - **Min % & Max %:** Sets modulation boundary; invert sweeps by setting Min > Max.
- **Live Degree Displays:** Real-time monitors showing physical angles (`-90°..+90°` Pitch, `-180°..+180°` Roll, `-180°..+180°` Yaw).

### 2. High-Performance UDP Relay (`relay.py`)
- Python 3 standard library only (zero external pip dependencies).
- Binds `:9000` and duplicates raw UDP packets to TouchDesigner (`:8000`) and Live (`:8001`).
- `--monitor`: Live CLI dashboard displaying real-time FPS and orientation angles.
- `--simulate`: Generates realistic 30 FPS synthetic motion for offline testing.

### 3. TouchDesigner Generative Scene (`touchdesigner/motion-visuals/`)
- Real-time cosmic nebula GLSL shader reacting to 3D orientation.
- Camera gimbal matching physical phone tilt and heading 1:1.
- First-derivative velocity detector triggering dynamic bloom and particle bursts on quick shakes or flicks.

---

## Quick Start Guide

### Step 1: Start the Relay
In your terminal, start the relay with the live monitor:

```bash
cd /Users/theo.dev/Documents/misc/my-ableton/devices/ios-motion-controller
python3 relay.py --monitor
```

*(Note: To test without the physical phone, run `python3 relay.py --simulate`).*

### Step 2: Configure Your iOS App
- **Destination IP:** Enter your Mac's local Wi-Fi IP (e.g., `192.168.1.xxx`).
  *(Find your Mac IP with: `ipconfig getifaddr en0`)*
- **Destination Port:** `9000`
- Turn on transmission. You will immediately see the FPS counter and angle readouts update in your terminal!

### Step 3: Load the Device in Ableton Live
1. Open Ableton Live.
2. In the Live Browser, navigate to:
   ```text
   User Library ──► Presets ──► Audio Effects ──► Max Audio Effect ──► Motion_Receiver.amxd
   ```
3. Drag **`Motion_Receiver.amxd`** onto any track (e.g. an instrument lead, synth bass, or master bus).
4. Watch the `P°`, `R°`, and `Y°` dials respond to your phone!
5. Click **Map** on **P1** and click any parameter (e.g. Filter Cutoff).
6. Click **TARE** to center your preferred physical grip.

### Step 4: Open TouchDesigner Visuals
1. Open TouchDesigner.
2. Open **`touchdesigner/motion_visuals.toe`**.
3. Tilt, bank, and turn your phone to fly through the generative cosmic nebula!

---

## OSC Specification Reference

| Parameter | OSC Address | Argument Type | Range (Radians) | Equivalent Degrees | Normalized `[0.0, 1.0]` |
|---|---|---|---|---|---|
| **Pitch** (Nod) | `/phone/orientation` | Float32 (arg 0) | `[-π/2, +π/2]` | `-90.0°` to `+90.0°` | `(Pitch + π/2) / π` |
| **Roll** (Tilt) | `/phone/orientation` | Float32 (arg 1) | `[-π, +π]` | `-180.0°` to `+180.0°` | `(Roll + π) / (2π)` |
| **Yaw** (Turn) | `/phone/orientation` | Float32 (arg 2) | `[-π, +π]` | `-180.0°` to `+180.0°` | `(Yaw + π) / (2π)` |
