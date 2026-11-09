#!/usr/bin/env python3
"""build_device.py - Build the Motion Receiver Max for Live device (.amxd).

Features:
- UDP OSC Receiver for /phone/orientation [pitch, roll, yaw] on port 8001.
- CoreMotion Radian -> [0.0, 1.0] Normalization with mathematical precision.
- Tare / Centering Button to establish comfortable stage holding angle.
- Jitter Smoothing (slide filter) with adjustable response dial.
- 6 Live API Parameter Mapping Slots (P1, P2, R1, R2, Y1, Y2) via live.map and live.remote~.
- Full independent Min % and Max % scaling dials with sweep inversion support.
- Live orientation readout dials for Pitch (-90°..+90°), Roll (-180°..+180°), and Yaw (-180°..+180°).
- 100% Transparent stereo audio pass-through (plugin~ -> plugout~).
"""

import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
M4L_COMMON = os.path.join(HERE, "..", "finishing-kit", "m4l")
if M4L_COMMON not in sys.path:
    sys.path.insert(0, M4L_COMMON)

import amxd

USER_LIBRARY_DIR = "/Volumes/Libraries/MY_MUSIC/_ABLETON/User Library/Presets/Audio Effects/Max Audio Effect"


def box(id_, maxclass, rect, **kw):
    b = {"id": id_, "maxclass": maxclass, "patching_rect": rect}
    b.update(kw)
    return {"box": b}


def newobj(id_, text, rect, inlets=1, outlets=1, outlettype=None, **kw):
    if outlettype is None:
        outlettype = [""]
    return box(id_, "newobj", rect, text=text, numinlets=inlets, numoutlets=outlets, outlettype=outlettype, **kw)


def message(id_, text, rect, inlets=2, outlets=1, **kw):
    return box(id_, "message", rect, text=text, numinlets=inlets, numoutlets=outlets, outlettype=[""], **kw)


def live_dial(id_, name, rect, pres, lo=0.0, hi=1.0, init=0.5, unitstyle=1, shortname=None):
    if shortname is None:
        shortname = name
    valueof = {
        "parameter_longname": name,
        "parameter_shortname": shortname,
        "parameter_type": 0,
        "parameter_mmin": lo,
        "parameter_mmax": hi,
        "parameter_initial": [init],
        "parameter_initial_enable": 1,
        "parameter_unitstyle": unitstyle,
        "parameter_speedlim": 0.0
    }
    return box(id_, "live.dial", rect, numinlets=1, numoutlets=2, outlettype=["", "float"],
               parameter_enable=1, varname=name, presentation=1, presentation_rect=pres,
               saved_attribute_attributes={"valueof": valueof})


def live_pct_dial(id_, name, rect, pres, init=0.0):
    valueof = {
        "parameter_longname": name,
        "parameter_shortname": name.split()[-1],
        "parameter_type": 0,
        "parameter_mmin": 0.0,
        "parameter_mmax": 100.0,
        "parameter_initial": [init],
        "parameter_initial_enable": 1,
        "parameter_unitstyle": 5,  # %
        "parameter_speedlim": 0.0
    }
    return box(id_, "live.dial", rect, numinlets=1, numoutlets=2, outlettype=["", "float"],
               parameter_enable=1, varname=name, presentation=1, presentation_rect=pres,
               saved_attribute_attributes={"valueof": valueof})


def live_toggle_btn(id_, name, text_off, text_on, rect, pres, shortname="Map"):
    valueof = {
        "parameter_longname": name,
        "parameter_shortname": shortname,
        "parameter_type": 2,
        "parameter_mmax": 1.0,
        "parameter_enum": ["off", "on"]
    }
    return box(id_, "live.text", rect, numinlets=1, numoutlets=2, outlettype=["", "float"],
               parameter_enable=1, varname=name, presentation=1, presentation_rect=pres,
               text=text_off, texton=text_on, mode=1,
               saved_attribute_attributes={"valueof": valueof})


def live_trigger_btn(id_, name, text, rect, pres, shortname="Tare"):
    valueof = {
        "parameter_longname": name,
        "parameter_shortname": shortname,
        "parameter_type": 2,
        "parameter_mmax": 1.0,
        "parameter_enum": ["off", "on"]
    }
    return box(id_, "live.text", rect, numinlets=1, numoutlets=2, outlettype=["", "float"],
               parameter_enable=1, varname=name, presentation=1, presentation_rect=pres,
               text=text, texton=text, mode=0,
               saved_attribute_attributes={"valueof": valueof})


def live_unmap_btn(id_, name, rect, pres):
    valueof = {
        "parameter_longname": name,
        "parameter_shortname": "✕",
        "parameter_type": 2,
        "parameter_mmax": 1.0,
        "parameter_enum": ["off", "on"]
    }
    return box(id_, "live.text", rect, numinlets=1, numoutlets=2, outlettype=["", "float"],
               parameter_enable=1, varname=name, presentation=1, presentation_rect=pres,
               text="✕", texton="✕", mode=0,
               saved_attribute_attributes={"valueof": valueof})


def comment(id_, text, rect, pres=None, fontsize=10.0, fontface=0):
    kw = {"fontsize": fontsize, "fontface": fontface}
    if pres:
        kw.update({"presentation": 1, "presentation_rect": pres})
    return box(id_, "comment", rect, text=text, numinlets=1, numoutlets=0, **kw)


def build_device():
    with open(os.path.join(M4L_COMMON, "spike_a_trim.json")) as f:
        p = json.load(f)

    pt = p["patcher"]
    pt["rect"] = [80.0, 80.0, 1300.0, 900.0]
    pt["openrect"] = [0.0, 0.0, 792.0, 135.0]
    pt["devicewidth"] = 792.0
    pt["description"] = "Motion Receiver - iOS CoreMotion 3-Axis OSC Controller for Ableton Live"

    boxes = [
        # Audio Pass-through
        newobj("obj-1", "plugin~", [20.0, 20.0, 53.0, 20.0], inlets=2, outlets=2, outlettype=["signal", "signal"]),
        newobj("obj-2", "plugout~", [20.0, 80.0, 53.0, 20.0], inlets=2, outlets=2, outlettype=["signal", "signal"]),

        # UDP Receive on port 8001
        newobj("obj-3", "udpreceive 8001", [120.0, 20.0, 115.0, 20.0], inlets=1, outlets=1, outlettype=[""]),

        # Route /phone/orientation [pitch, roll, yaw]
        newobj("obj-4", "route /phone/orientation", [120.0, 60.0, 140.0, 20.0], inlets=1, outlets=2, outlettype=["", ""]),

        # Unpack 3 floats (Pitch, Roll, Yaw) in Radians
        newobj("obj-5", "unpack 0. 0. 0.", [120.0, 95.0, 105.0, 20.0], inlets=1, outlets=3, outlettype=["float", "float", "float"]),

        # Normalization math to [0.0, 1.0]:
        # Pitch: (x + pi/2) / pi
        newobj("obj-6", "expr ($f1 + 1.5707963) * 0.31830988", [120.0, 135.0, 195.0, 20.0], inlets=1, outlets=1, outlettype=["float"]),
        newobj("obj-7", "clip 0. 1.", [120.0, 165.0, 65.0, 20.0], inlets=3, outlets=1, outlettype=["float"]),

        # Roll: (x + pi) / 2pi
        newobj("obj-8", "expr ($f1 + 3.14159265) * 0.15915494", [330.0, 135.0, 205.0, 20.0], inlets=1, outlets=1, outlettype=["float"]),
        newobj("obj-9", "clip 0. 1.", [330.0, 165.0, 65.0, 20.0], inlets=3, outlets=1, outlettype=["float"]),

        # Yaw: (x + pi) / 2pi
        newobj("obj-10", "expr ($f1 + 3.14159265) * 0.15915494", [550.0, 135.0, 205.0, 20.0], inlets=1, outlets=1, outlettype=["float"]),
        newobj("obj-11", "clip 0. 1.", [550.0, 165.0, 65.0, 20.0], inlets=3, outlets=1, outlettype=["float"]),

        # Tare / Center Engine
        # Default tare reference is 0.5 for each axis
        newobj("obj-12", "f 0.5", [150.0, 205.0, 40.0, 20.0], inlets=2, outlets=1, outlettype=["float"]),
        newobj("obj-13", "f 0.5", [360.0, 205.0, 40.0, 20.0], inlets=2, outlets=1, outlettype=["float"]),
        newobj("obj-14", "f 0.5", [580.0, 205.0, 40.0, 20.0], inlets=2, outlets=1, outlettype=["float"]),

        # Tare calculation: Output = clip(0.5 + (Raw - TareRef), 0., 1.)
        newobj("obj-15", "expr 0.5 + ($f1 - $f2)", [120.0, 240.0, 140.0, 20.0], inlets=2, outlets=1, outlettype=["float"]),
        newobj("obj-16", "clip 0. 1.", [120.0, 270.0, 65.0, 20.0], inlets=3, outlets=1, outlettype=["float"]),

        newobj("obj-17", "expr 0.5 + ($f1 - $f2)", [330.0, 240.0, 140.0, 20.0], inlets=2, outlets=1, outlettype=["float"]),
        newobj("obj-18", "clip 0. 1.", [330.0, 270.0, 65.0, 20.0], inlets=3, outlets=1, outlettype=["float"]),

        newobj("obj-19", "expr 0.5 + ($f1 - $f2)", [550.0, 240.0, 140.0, 20.0], inlets=2, outlets=1, outlettype=["float"]),
        newobj("obj-20", "clip 0. 1.", [550.0, 270.0, 65.0, 20.0], inlets=3, outlets=1, outlettype=["float"]),

        # Tare Trigger Button in Presentation
        live_trigger_btn("obj-21", "Tare Button", "TARE", [20.0, 160.0, 50.0, 22.0], pres=[8.0, 42.0, 44.0, 24.0], shortname="Tare"),
        # Trigger button bangs obj-12, obj-13, obj-14 to store current raw values as tare reference
        newobj("obj-22", "t b b b", [20.0, 195.0, 55.0, 20.0], inlets=1, outlets=3, outlettype=["bang", "bang", "bang"]),

        # Smooth Dial (1..30 samples, init 4)
        live_dial("obj-23", "Smooth", [20.0, 230.0, 44.0, 48.0], pres=[56.0, 36.0, 38.0, 42.0], lo=1.0, hi=30.0, init=4.0, unitstyle=0, shortname="Smooth"),
        newobj("obj-24", "i 4", [20.0, 290.0, 30.0, 20.0], inlets=2, outlets=1, outlettype=["int"]),

        # Slide Filters for each axis
        newobj("obj-25", "slide 4 4", [120.0, 310.0, 60.0, 20.0], inlets=3, outlets=1, outlettype=["float"]),
        newobj("obj-26", "slide 4 4", [330.0, 310.0, 60.0, 20.0], inlets=3, outlets=1, outlettype=["float"]),
        newobj("obj-27", "slide 4 4", [550.0, 310.0, 60.0, 20.0], inlets=3, outlets=1, outlettype=["float"]),

        # Live Display Readouts in Presentation: Pitch (-90°..+90°), Roll (-180°..+180°), Yaw (-180°..+180°)
        # Scale smoothed 0..1 to degrees for visual meters
        newobj("obj-28", "scale 0. 1. -90 90", [120.0, 345.0, 120.0, 20.0], inlets=5, outlets=1, outlettype=["float"]),
        newobj("obj-29", "i", [120.0, 375.0, 30.0, 20.0], inlets=2, outlets=1, outlettype=["int"]),
        live_dial("obj-30", "Pitch Readout", [120.0, 405.0, 44.0, 48.0], pres=[6.0, 82.0, 36.0, 42.0], lo=-90.0, hi=90.0, init=0.0, unitstyle=0, shortname="P°"),

        newobj("obj-31", "scale 0. 1. -180 180", [330.0, 345.0, 125.0, 20.0], inlets=5, outlets=1, outlettype=["float"]),
        newobj("obj-32", "i", [330.0, 375.0, 30.0, 20.0], inlets=2, outlets=1, outlettype=["int"]),
        live_dial("obj-33", "Roll Readout", [330.0, 405.0, 44.0, 48.0], pres=[44.0, 82.0, 36.0, 42.0], lo=-180.0, hi=180.0, init=0.0, unitstyle=0, shortname="R°"),

        newobj("obj-34", "scale 0. 1. -180 180", [550.0, 345.0, 125.0, 20.0], inlets=5, outlets=1, outlettype=["float"]),
        newobj("obj-35", "i", [550.0, 375.0, 30.0, 20.0], inlets=2, outlets=1, outlettype=["int"]),
        live_dial("obj-36", "Yaw Readout", [550.0, 405.0, 44.0, 48.0], pres=[82.0, 82.0, 36.0, 42.0], lo=-180.0, hi=180.0, init=0.0, unitstyle=0, shortname="Y°"),

        # Presentation Headers & Labels
        comment("obj-40", "MOTION RECEIVER", [20.0, 480.0, 140.0, 20.0], pres=[8.0, 6.0, 114.0, 16.0], fontsize=10.0, fontface=1),
        comment("obj-41", "iOS OSC :8001", [20.0, 505.0, 100.0, 16.0], pres=[8.0, 22.0, 85.0, 13.0], fontsize=8.0),

        # Column 1: Pitch (Nod)
        comment("obj-42", "PITCH (NOD)", [120.0, 480.0, 100.0, 18.0], pres=[126.0, 6.0, 110.0, 15.0], fontsize=9.0, fontface=1),
        comment("obj-43", "Forward / Backward", [120.0, 505.0, 120.0, 16.0], pres=[126.0, 20.0, 110.0, 12.0], fontsize=7.5),

        # Column 2: Roll (Tilt)
        comment("obj-44", "ROLL (TILT)", [330.0, 480.0, 100.0, 18.0], pres=[348.0, 6.0, 110.0, 15.0], fontsize=9.0, fontface=1),
        comment("obj-45", "Left / Right Bank", [330.0, 505.0, 120.0, 16.0], pres=[348.0, 20.0, 110.0, 12.0], fontsize=7.5),

        # Column 3: Yaw (Turn)
        comment("obj-46", "YAW (TURN)", [550.0, 480.0, 100.0, 18.0], pres=[570.0, 6.0, 110.0, 15.0], fontsize=9.0, fontface=1),
        comment("obj-47", "Compass Heading", [550.0, 505.0, 120.0, 16.0], pres=[570.0, 20.0, 110.0, 12.0], fontsize=7.5),
    ]

    # Slot builder helper for 6 mapping slots
    def add_slot(prefix, base_id, py_base, map_pres, lbl_pres, min_pres, max_pres, unm_pres):
        b = []
        b.append(live_toggle_btn(f"obj-{base_id}", f"Map {prefix}", "Map", "Mapping...", [py_base, 100.0, 45.0, 20.0], pres=map_pres))
        b.append(message(f"obj-{base_id+1}", "mapping $1", [py_base, 130.0, 70.0, 20.0]))
        b.append(newobj(f"obj-{base_id+2}", "live.map", [py_base, 160.0, 60.0, 20.0], inlets=1, outlets=5, outlettype=["", "", "", "int", ""]))
        b.append(newobj(f"obj-{base_id+3}", "live.remote~ @normalized 1", [py_base, 190.0, 150.0, 20.0], inlets=2, outlets=2, outlettype=["", ""]))
        b.append(newobj(f"obj-{base_id+4}", "prepend set", [py_base, 220.0, 75.0, 20.0], inlets=1, outlets=1, outlettype=[""]))
        b.append(comment(f"obj-{base_id+5}", "[Unmapped]", [py_base, 250.0, 100.0, 20.0], pres=lbl_pres, fontsize=8.0))
        b.append(live_unmap_btn(f"obj-{base_id+6}", f"Unmap {prefix}", [py_base, 280.0, 25.0, 20.0], pres=unm_pres))
        b.append(message(f"obj-{base_id+7}", "unmap", [py_base, 310.0, 50.0, 20.0]))
        b.append(message(f"obj-{base_id+8}", "id 0", [py_base, 335.0, 40.0, 20.0]))
        b.append(message(f"obj-{base_id+9}", "set [Unmapped]", [py_base, 360.0, 95.0, 20.0]))
        b.append(message(f"obj-{base_id+10}", "0", [py_base, 385.0, 30.0, 20.0]))
        b.append(live_pct_dial(f"obj-{base_id+11}", f"Min {prefix}", [py_base, 410.0, 44.0, 44.0], pres=min_pres, init=0.0))
        b.append(live_pct_dial(f"obj-{base_id+12}", f"Max {prefix}", [py_base, 460.0, 44.0, 44.0], pres=max_pres, init=100.0))
        b.append(newobj(f"obj-{base_id+13}", "expr $f1 * (($f3 - $f2) * 0.01) + ($f2 * 0.01)", [py_base, 510.0, 240.0, 20.0], inlets=3, outlets=1, outlettype=["float"]))
        b.append(newobj(f"obj-{base_id+14}", "clip 0. 1.", [py_base, 540.0, 65.0, 20.0], inlets=3, outlets=1, outlettype=["float"]))
        return b

    # Pitch Slots (P1, P2)
    boxes.extend(add_slot("P1", 100, 750.0,
                          map_pres=[126.0, 36.0, 36.0, 20.0],
                          lbl_pres=[166.0, 38.0, 68.0, 16.0],
                          min_pres=[236.0, 26.0, 34.0, 42.0],
                          max_pres=[272.0, 26.0, 34.0, 42.0],
                          unm_pres=[308.0, 36.0, 18.0, 20.0]))

    boxes.extend(add_slot("P2", 120, 850.0,
                          map_pres=[126.0, 82.0, 36.0, 20.0],
                          lbl_pres=[166.0, 84.0, 68.0, 16.0],
                          min_pres=[236.0, 72.0, 34.0, 42.0],
                          max_pres=[272.0, 72.0, 34.0, 42.0],
                          unm_pres=[308.0, 82.0, 18.0, 20.0]))

    # Roll Slots (R1, R2)
    boxes.extend(add_slot("R1", 140, 950.0,
                          map_pres=[348.0, 36.0, 36.0, 20.0],
                          lbl_pres=[388.0, 38.0, 68.0, 16.0],
                          min_pres=[458.0, 26.0, 34.0, 42.0],
                          max_pres=[494.0, 26.0, 34.0, 42.0],
                          unm_pres=[530.0, 36.0, 18.0, 20.0]))

    boxes.extend(add_slot("R2", 160, 1050.0,
                          map_pres=[348.0, 82.0, 36.0, 20.0],
                          lbl_pres=[388.0, 84.0, 68.0, 16.0],
                          min_pres=[458.0, 72.0, 34.0, 42.0],
                          max_pres=[494.0, 72.0, 34.0, 42.0],
                          unm_pres=[530.0, 82.0, 18.0, 20.0]))

    # Yaw Slots (Y1, Y2)
    boxes.extend(add_slot("Y1", 180, 1150.0,
                          map_pres=[570.0, 36.0, 36.0, 20.0],
                          lbl_pres=[610.0, 38.0, 68.0, 16.0],
                          min_pres=[680.0, 26.0, 34.0, 42.0],
                          max_pres=[716.0, 26.0, 34.0, 42.0],
                          unm_pres=[752.0, 36.0, 18.0, 20.0]))

    boxes.extend(add_slot("Y2", 200, 1250.0,
                          map_pres=[570.0, 82.0, 36.0, 20.0],
                          lbl_pres=[610.0, 84.0, 68.0, 16.0],
                          min_pres=[680.0, 72.0, 34.0, 42.0],
                          max_pres=[716.0, 72.0, 34.0, 42.0],
                          unm_pres=[752.0, 82.0, 18.0, 20.0]))

    cords = [
        # Audio Pass-through
        (["obj-1", 0], ["obj-2", 0]),
        (["obj-1", 1], ["obj-2", 1]),

        # UDP -> Route
        (["obj-3", 0], ["obj-4", 0]),
        # Route -> Unpack [pitch, roll, yaw]
        (["obj-4", 0], ["obj-5", 0]),

        # Pitch unpack -> expr normalization -> clip
        (["obj-5", 0], ["obj-6", 0]),
        (["obj-6", 0], ["obj-7", 0]),

        # Roll unpack -> expr normalization -> clip
        (["obj-5", 1], ["obj-8", 0]),
        (["obj-8", 0], ["obj-9", 0]),

        # Yaw unpack -> expr normalization -> clip
        (["obj-5", 2], ["obj-10", 0]),
        (["obj-10", 0], ["obj-11", 0]),

        # Tare Trigger -> t b b b -> triggers tare reference storage
        (["obj-21", 0], ["obj-22", 0]),
        (["obj-22", 0], ["obj-12", 0]),
        (["obj-22", 1], ["obj-13", 0]),
        (["obj-22", 2], ["obj-14", 0]),

        # Raw values also connect to cold inlets of Tare reference boxes
        (["obj-7", 0], ["obj-12", 1]),
        (["obj-9", 0], ["obj-13", 1]),
        (["obj-11", 0], ["obj-14", 1]),

        # Raw values into Tare calculation hot inlets ($f1)
        (["obj-7", 0], ["obj-15", 0]),
        (["obj-12", 0], ["obj-15", 1]),
        (["obj-15", 0], ["obj-16", 0]),

        (["obj-9", 0], ["obj-17", 0]),
        (["obj-13", 0], ["obj-17", 1]),
        (["obj-17", 0], ["obj-18", 0]),

        (["obj-11", 0], ["obj-19", 0]),
        (["obj-14", 0], ["obj-19", 1]),
        (["obj-19", 0], ["obj-20", 0]),

        # Smooth dial -> slide up & down inlets
        (["obj-23", 0], ["obj-24", 0]),
        (["obj-24", 0], ["obj-25", 1]),
        (["obj-24", 0], ["obj-25", 2]),
        (["obj-24", 0], ["obj-26", 1]),
        (["obj-24", 0], ["obj-26", 2]),
        (["obj-24", 0], ["obj-27", 1]),
        (["obj-24", 0], ["obj-27", 2]),

        # Post-tare signals into slide filters
        (["obj-16", 0], ["obj-25", 0]),
        (["obj-18", 0], ["obj-26", 0]),
        (["obj-20", 0], ["obj-27", 0]),

        # Readout meters: scale -> int -> live.dial
        (["obj-25", 0], ["obj-28", 0]),
        (["obj-28", 0], ["obj-29", 0]),
        (["obj-29", 0], ["obj-30", 0]),

        (["obj-26", 0], ["obj-31", 0]),
        (["obj-31", 0], ["obj-32", 0]),
        (["obj-32", 0], ["obj-33", 0]),

        (["obj-27", 0], ["obj-34", 0]),
        (["obj-34", 0], ["obj-35", 0]),
        (["obj-35", 0], ["obj-36", 0]),
    ]

    # Slot wiring helper
    def wire_slot(base_id, input_source):
        return [
            # Map button -> message mapping $1 -> live.map
            ([f"obj-{base_id}", 0], [f"obj-{base_id+1}", 0]),
            ([f"obj-{base_id+1}", 0], [f"obj-{base_id+2}", 0]),

            # live.map outlet 1 (id) -> live.remote~ inlet 1
            ([f"obj-{base_id+2}", 1], [f"obj-{base_id+3}", 1]),

            # live.map outlet 2 (name) -> prepend set -> comment
            ([f"obj-{base_id+2}", 2], [f"obj-{base_id+4}", 0]),
            ([f"obj-{base_id+4}", 0], [f"obj-{base_id+5}", 0]),

            # live.map outlet 3 (mapping finished 0) -> turn off Map toggle button
            ([f"obj-{base_id+2}", 3], [f"obj-{base_id}", 0]),

            # Unmap button triggers 4 messages:
            ([f"obj-{base_id+6}", 0], [f"obj-{base_id+7}", 0]),  # unmap -> live.map
            ([f"obj-{base_id+7}", 0], [f"obj-{base_id+2}", 0]),
            ([f"obj-{base_id+6}", 0], [f"obj-{base_id+8}", 0]),  # id 0 -> live.remote~
            ([f"obj-{base_id+8}", 0], [f"obj-{base_id+3}", 1]),
            ([f"obj-{base_id+6}", 0], [f"obj-{base_id+9}", 0]),  # set [Unmapped] -> label
            ([f"obj-{base_id+9}", 0], [f"obj-{base_id+5}", 0]),
            ([f"obj-{base_id+6}", 0], [f"obj-{base_id+10}", 0]), # 0 -> Map button
            ([f"obj-{base_id+10}", 0], [f"obj-{base_id}", 0]),

            # Gesture input (smoothed 0..1) -> expr inlet 0
            (input_source, [f"obj-{base_id+13}", 0]),

            # Min / Max dials -> expr inlets 1 & 2
            ([f"obj-{base_id+11}", 0], [f"obj-{base_id+13}", 1]),
            ([f"obj-{base_id+12}", 0], [f"obj-{base_id+13}", 2]),

            # expr -> clip -> live.remote~ inlet 0
            ([f"obj-{base_id+13}", 0], [f"obj-{base_id+14}", 0]),
            ([f"obj-{base_id+14}", 0], [f"obj-{base_id+3}", 0]),
        ]

    # Wire Pitch slots (input: obj-25)
    cords.extend(wire_slot(100, ["obj-25", 0])) # P1
    cords.extend(wire_slot(120, ["obj-25", 0])) # P2

    # Wire Roll slots (input: obj-26)
    cords.extend(wire_slot(140, ["obj-26", 0])) # R1
    cords.extend(wire_slot(160, ["obj-26", 0])) # R2

    # Wire Yaw slots (input: obj-27)
    cords.extend(wire_slot(180, ["obj-27", 0])) # Y1
    cords.extend(wire_slot(200, ["obj-27", 0])) # Y2

    # Assemble lines
    lines = []
    for (src_obj, src_out), (dst_obj, dst_in) in cords:
        lines.append({
            "patchline": {
                "source": [src_obj, src_out],
                "destination": [dst_obj, dst_in]
            }
        })

    # Assemble parameter dictionary
    params = {
        "obj-21": ["Tare Button", "Tare", 0],
        "obj-23": ["Smooth", "Smooth", 0],
        "obj-30": ["Pitch Readout", "P°", 0],
        "obj-33": ["Roll Readout", "R°", 0],
        "obj-36": ["Yaw Readout", "Y°", 0],
    }

    for slot_name, base_id in [("P1", 100), ("P2", 120), ("R1", 140), ("R2", 160), ("Y1", 180), ("Y2", 200)]:
        params[f"obj-{base_id}"] = [f"Map {slot_name}", "Map", 0]
        params[f"obj-{base_id+6}"] = [f"Unmap {slot_name}", "✕", 0]
        params[f"obj-{base_id+11}"] = [f"Min {slot_name}", f"Min {slot_name}", 0]
        params[f"obj-{base_id+12}"] = [f"Max {slot_name}", f"Max {slot_name}", 0]

    pt["boxes"] = boxes
    pt["lines"] = lines
    pt["parameters"] = params

    json_str = json.dumps(p, indent="\t")
    json_bytes = json_str.encode("utf-8") + b"\0"

    device_name = "Motion_Receiver.amxd"
    amxd_bytes = amxd.pack_plain(json_bytes, kind=b"aaaa")

    local_out = os.path.join(HERE, device_name)
    with open(local_out, "wb") as f:
        f.write(amxd_bytes)
    print(f"Built {local_out} ({len(amxd_bytes)} bytes) ✅")

    # Install to Live User Library if available
    if os.path.isdir(USER_LIBRARY_DIR):
        lib_out = os.path.join(USER_LIBRARY_DIR, device_name)
        shutil.copyfile(local_out, lib_out)
        print(f"Installed to Live User Library: {lib_out} ✅")
    else:
        print(f"User Library not available at {USER_LIBRARY_DIR}, skipped install.")


if __name__ == "__main__":
    build_device()
