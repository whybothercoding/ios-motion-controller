#!/usr/bin/env python3
"""test_pipeline.py - Automated verification of the Demo 3 OSC pipeline."""

import os
import socket
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import relay

USER_LIB_M4L = "/Volumes/Libraries/MY_MUSIC/_ABLETON/User Library/Presets/Audio Effects/Max Audio Effect/Motion_Receiver.amxd"


def test_pipeline():
    print("==================================================")
    print("  Demo 3: End-to-End Pipeline Verification")
    print("==================================================")

    # 1. Verify AMXD device files
    local_amxd = os.path.join(HERE, "Motion_Receiver.amxd")
    assert os.path.isfile(local_amxd), f"Missing {local_amxd}"
    print(f"1. Local Motion_Receiver.amxd: Found ({os.path.getsize(local_amxd)} bytes) ✅")

    if os.path.isfile(USER_LIB_M4L):
        print(f"2. User Library Motion_Receiver.amxd: Verified installed ✅")
    else:
        print(f"2. User Library AMXD not present at {USER_LIB_M4L} (drive may be unmounted)")

    # 2. Test Relay Socket Splitting
    # Set up mock receivers for TD (8000) and Live (8001)
    td_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    td_sock.bind(("127.0.0.1", 8000))
    td_sock.settimeout(2.0)

    live_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    live_sock.bind(("127.0.0.1", 8001))
    live_sock.settimeout(2.0)

    # Launch relay in background
    relay_proc = subprocess.Popen(
        [sys.executable, os.path.join(HERE, "relay.py"), "--in-port", "9000", "--td-port", "8000", "--live-port", "8001"]
    )
    time.sleep(0.5)

    try:
        # Send synthetic packet to port 9000
        client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        test_pitch = 0.523598   # +30 degrees
        test_roll = -1.047197   # -60 degrees
        test_yaw = 2.094395     # +120 degrees

        test_packet = relay.pack_osc_message("/phone/orientation", test_pitch, test_roll, test_yaw)
        client_sock.sendto(test_packet, ("127.0.0.1", 9000))

        # Check TD receiver
        data_td, _ = td_sock.recvfrom(1024)
        addr_td, vals_td = relay.unpack_osc_message(data_td)
        assert addr_td == "/phone/orientation", f"TD Address mismatch: {addr_td}"
        assert abs(vals_td[0] - test_pitch) < 1e-4, f"TD Pitch mismatch: {vals_td[0]}"
        print(f"3. TouchDesigner Ingest (:8000): Packet received & verified ✅")

        # Check Live receiver
        data_live, _ = live_sock.recvfrom(1024)
        addr_live, vals_live = relay.unpack_osc_message(data_live)
        assert addr_live == "/phone/orientation", f"Live Address mismatch: {addr_live}"
        assert abs(vals_live[1] - test_roll) < 1e-4, f"Live Roll mismatch: {vals_live[1]}"
        assert abs(vals_live[2] - test_yaw) < 1e-4, f"Live Yaw mismatch: {vals_live[2]}"
        print(f"4. Ableton Live Ingest (:8001): Packet received & verified ✅")

        print("==================================================")
        print("  ALL VERIFICATION CHECKS PASSED SUCCESSFULLY! ✅")
        print("==================================================")
    finally:
        relay_proc.terminate()
        relay_proc.wait()
        td_sock.close()
        live_sock.close()


if __name__ == "__main__":
    test_pipeline()
