#!/usr/bin/env python3
"""relay.py - High-performance UDP OSC Splitter & Monitor for iOS Motion Controller.

Receives /phone/orientation [pitch, roll, yaw] packets from the iOS app on port 9000
and duplicates them to TouchDesigner (port 8000) and Ableton Live (port 8001).

Usage:
  python3 relay.py [--in-port 9000] [--td-port 8000] [--live-port 8001] [--monitor]
  python3 relay.py --simulate   # Synthesizes 30 FPS motion packets for offline testing
  python3 relay.py --test       # Runs self-test and verification
"""

import argparse
import math
import socket
import struct
import sys
import time

RAD_TO_DEG = 180.0 / math.pi
PI = math.pi
HALF_PI = math.pi / 2.0
TWO_PI = 2.0 * math.pi


def pack_osc_string(s: str) -> bytes:
    b = s.encode("utf-8") + b"\0"
    pad = (-len(b)) % 4
    return b + (b"\0" * pad)


def pack_osc_message(address: str, *args) -> bytes:
    """Builds a standard binary OSC packet for float arguments."""
    tags = "," + "".join("f" for _ in args)
    data = pack_osc_string(address) + pack_osc_string(tags)
    for arg in args:
        data += struct.pack(">f", float(arg))
    return data


def unpack_osc_message(raw_bytes: bytes):
    """Parses an OSC packet containing an address, type tags, and float arguments."""
    try:
        null_idx = raw_bytes.find(b"\0")
        if null_idx == -1:
            return None, []
        address = raw_bytes[:null_idx].decode("utf-8", errors="ignore")
        offset = ((null_idx // 4) + 1) * 4
        
        if offset >= len(raw_bytes) or raw_bytes[offset:offset+1] != b",":
            return address, []
        
        tag_null = raw_bytes.find(b"\0", offset)
        if tag_null == -1:
            return address, []
        tags = raw_bytes[offset:tag_null].decode("utf-8", errors="ignore")
        offset = ((tag_null // 4) + 1) * 4
        
        values = []
        for t in tags[1:]:
            if t == "f":
                if offset + 4 <= len(raw_bytes):
                    val = struct.unpack(">f", raw_bytes[offset:offset+4])[0]
                    values.append(val)
                    offset += 4
            elif t == "i":
                if offset + 4 <= len(raw_bytes):
                    val = struct.unpack(">i", raw_bytes[offset:offset+4])[0]
                    values.append(val)
                    offset += 4
        return address, values
    except Exception:
        return None, []


def run_relay(in_ip: str, in_port: int, td_ip: str, td_port: int, live_ip: str, live_port: int, monitor: bool):
    in_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    in_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    in_sock.bind((in_ip, in_port))

    out_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Send to both 8000 and 7000 so TouchDesigner receives on either default port
    td_addr = (td_ip, td_port)
    td_alt_addr = (td_ip, 7000 if td_port != 7000 else 8000)
    live_addr = (live_ip, live_port)

    print(f"============================================================")
    print(f"  iOS Motion Controller OSC Relay")
    print(f"============================================================")
    print(f"  • Listening on:      {in_ip}:{in_port} (UDP)")
    print(f"  • Relaying to TD:    {td_ip}:{td_port} & {td_ip}:{td_alt_addr[1]}")
    print(f"  • Relaying to Live:  {live_ip}:{live_port}")
    print(f"  • Monitor Mode:      {'ENABLED' if monitor else 'DISABLED'}")
    print(f"============================================================")
    print(f"Waiting for incoming /phone/orientation packets from iOS app...\n")

    pkt_count = 0
    last_stat_time = time.time()
    last_fps = 0.0

    try:
        while True:
            data, client_addr = in_sock.recvfrom(2048)
            now = time.time()
            pkt_count += 1

            # Ultra-low-latency direct forward to both TD ports and Live
            out_sock.sendto(data, td_addr)
            out_sock.sendto(data, td_alt_addr)
            out_sock.sendto(data, live_addr)

            if monitor:
                if now - last_stat_time >= 1.0:
                    last_fps = pkt_count / (now - last_stat_time)
                    pkt_count = 0
                    last_stat_time = now

                addr, vals = unpack_osc_message(data)
                if addr == "/phone/orientation" and len(vals) >= 3:
                    pitch, roll, yaw = vals[0], vals[1], vals[2]
                    # Compute normalized [0.0, 1.0]
                    norm_p = max(0.0, min(1.0, (pitch + HALF_PI) / PI))
                    norm_r = max(0.0, min(1.0, (roll + PI) / TWO_PI))
                    norm_y = max(0.0, min(1.0, (yaw + PI) / TWO_PI))
                    deg_p = pitch * RAD_TO_DEG
                    deg_r = roll * RAD_TO_DEG
                    deg_y = yaw * RAD_TO_DEG

                    sys.stdout.write(
                        f"\r[{client_addr[0]}] FPS: {last_fps:4.1f} | "
                        f"Pitch: {deg_p:+6.1f}° ({norm_p:.2f}) | "
                        f"Roll: {deg_r:+6.1f}° ({norm_r:.2f}) | "
                        f"Yaw: {deg_y:+6.1f}° ({norm_y:.2f})   "
                    )
                    sys.stdout.flush()
    except KeyboardInterrupt:
        print("\nRelay stopped by user.")
    finally:
        in_sock.close()
        out_sock.close()


def run_simulator(td_ip: str, td_port: int, live_ip: str, live_port: int, rate: float = 30.0):
    out_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    td_addr = (td_ip, td_port)
    live_addr = (live_ip, live_port)
    interval = 1.0 / rate

    print(f"============================================================")
    print(f"  iOS Motion Controller SIMULATOR (Test Generator)")
    print(f"============================================================")
    print(f"  • Generating 30 FPS /phone/orientation packets")
    print(f"  • Target TD:   {td_ip}:{td_port}")
    print(f"  • Target Live: {live_ip}:{live_port}")
    print(f"  • Press Ctrl+C to stop")
    print(f"============================================================")

    start_time = time.time()
    try:
        while True:
            t = time.time() - start_time
            # Realistic synthetic motion
            pitch = 0.8 * math.sin(t * 1.5)           # Nodding up and down
            roll  = 1.4 * math.sin(t * 0.9 + 0.5)     # Banking left and right
            yaw   = ((t * 0.6) % TWO_PI) - PI         # Slow turntable rotation

            pkt = pack_osc_message("/phone/orientation", pitch, roll, yaw)
            out_sock.sendto(pkt, td_addr)
            out_sock.sendto(pkt, live_addr)

            norm_p = (pitch + HALF_PI) / PI
            norm_r = (roll + PI) / TWO_PI
            norm_y = (yaw + PI) / TWO_PI

            sys.stdout.write(
                f"\r[SIMULATOR] "
                f"Pitch: {pitch * RAD_TO_DEG:+6.1f}° ({norm_p:.2f}) | "
                f"Roll: {roll * RAD_TO_DEG:+6.1f}° ({norm_r:.2f}) | "
                f"Yaw: {yaw * RAD_TO_DEG:+6.1f}° ({norm_y:.2f})   "
            )
            sys.stdout.flush()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nSimulator stopped.")
    finally:
        out_sock.close()


def run_selftest():
    print("Running OSC packet packing and unpacking self-test...")
    test_pitch = -0.785398
    test_roll = 1.570796
    test_yaw = -3.141592
    
    pkt = pack_osc_message("/phone/orientation", test_pitch, test_roll, test_yaw)
    assert len(pkt) == 40, f"Expected 40 bytes, got {len(pkt)}"
    
    addr, vals = unpack_osc_message(pkt)
    assert addr == "/phone/orientation", f"Expected /phone/orientation, got {addr}"
    assert len(vals) == 3, f"Expected 3 values, got {len(vals)}"
    assert abs(vals[0] - test_pitch) < 1e-5, f"Pitch mismatch: {vals[0]} vs {test_pitch}"
    assert abs(vals[1] - test_roll) < 1e-5, f"Roll mismatch: {vals[1]} vs {test_roll}"
    assert abs(vals[2] - test_yaw) < 1e-5, f"Yaw mismatch: {vals[2]} vs {test_yaw}"
    print("OSC Packet Packing/Unpacking Test: PASSED ✅")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="iOS Motion Controller OSC Relay & Splitter")
    parser.add_argument("--in-ip", default="0.0.0.0", help="IP to listen on (default: 0.0.0.0)")
    parser.add_argument("--in-port", type=int, default=9000, help="Port to listen for iOS app (default: 9000)")
    parser.add_argument("--td-ip", default="127.0.0.1", help="TouchDesigner IP (default: 127.0.0.1)")
    parser.add_argument("--td-port", type=int, default=8000, help="TouchDesigner OSC port (default: 8000)")
    parser.add_argument("--live-ip", default="127.0.0.1", help="Ableton Live IP (default: 127.0.0.1)")
    parser.add_argument("--live-port", type=int, default=8001, help="Ableton Live OSC port (default: 8001)")
    parser.add_argument("--monitor", action="store_true", help="Monitor and print incoming packet values and FPS")
    parser.add_argument("--simulate", action="store_true", help="Generate simulated 30 FPS motion packets")
    parser.add_argument("--test", action="store_true", help="Run self-test and exit")

    args = parser.parse_args()

    if args.test:
        run_selftest()
        sys.exit(0)

    if args.simulate:
        run_simulator(args.td_ip, args.td_port, args.live_ip, args.live_port)
    else:
        run_relay(args.in_ip, args.in_port, args.td_ip, args.td_port, args.live_ip, args.live_port, args.monitor)
