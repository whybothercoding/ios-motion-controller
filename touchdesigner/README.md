# Motion Visuals 🌌📱 (TouchDesigner Demo 3)

Real-time generative 3D visual scene responding to 3-axis continuous iOS motion data (`/phone/orientation`).

---

## Architecture

- **Ingest:** `oscin1` (OSC In CHOP) listening on UDP port `8000` (from `relay.py`) or port `9000` (direct from phone).
- **Processing:** `driver.py` (Execute DAT) computes radians-to-degrees, normalized `0..1` coordinates, and angular shake velocity.
- **Visuals:** `glsl_nebula` executes `nebula.glsl`, rendering a multi-layered domain-warped cosmic nebula whose camera tilt, hue shift, and turbulence lock 1:1 with phone movements.

---

## Quick Start

1. Ensure the relay is streaming:
   ```bash
   python3 /Users/theo.dev/Documents/misc/my-ableton/devices/ios-motion-controller/relay.py --monitor
   ```
2. Double-click `motion_visuals.toe` in TouchDesigner.
3. If running a blank canvas or re-initializing the network, run `setup_motion_network.py` inside the Textport (`Alt + T`):
   ```python
   import setup_motion_network
   setup_motion_network.setup()
   ```
4. Move and shake your phone to navigate the generative nebula.
