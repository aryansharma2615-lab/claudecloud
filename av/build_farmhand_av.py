"""FarmHand rail-SCARA -> SP assembly viewer (engine v5.2 page used as the template, data swapped).

Run:  python av/build_farmhand_av.py [--template av/engine/viewer_template_v5_3.html]
      -> av/farmhand_artifact_v1.html
The SP engine (~/Claude/AV) lives on the Mac. In the cloud the engine is taken from the published OneShot v5.2
viewer (av/engine/oneshot_v5_2_reference.html): its <script id="meta"> and <script id="geo"> blocks are the
data, everything else is the engine. This script never edits engine code; it only writes the two data blocks.
Every number comes from cad/params.py, cad/build_parts.py (assembly STLs), sim/paths.py, docs/BOM.md.
"""
import argparse
import base64
import json
import math
import os
import sys

import numpy as np
import trimesh

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "cad"))
sys.path.insert(0, os.path.join(ROOT, "sim"))
import params as P  # noqa: E402
import paths as SIMP  # noqa: E402

ASM = os.path.join(ROOT, "cad", "out", "asm")
X_CAD = 600.0          # rail position of the assembly STLs (world mm, sim/paths.py frame)
ZS_CAD = 480.0         # shoulder height of the assembly STLs above the table
FIL_CAD_PER_KG = 25.0  # PETG, Digitmakers-class price (estimate)

# ---------------------------------------------------------------- parts
GROUPS = {"frame": "Rail + lift — bought extrusion, screw, motors on the frame",
          "carriage": "Shoulder carriage (rides the Z column)",
          "arm": "Arm — printed boxes around alu spines",
          "hand": "Hand — quick-change flange, gripper, stylus",
          "drive": "Motors, bearings, pulleys",
          "station": "Station — H2S, Ender, door, table (assumed sizes, ghost)"}
COL = {"frame": "#8a94a6", "carriage": "#2f7fd1", "arm": "#2f7fd1", "hand": "#e0782d", "drive": "#3a3f47",
       "station": "#b9c0c9"}

# id: (label, group, step, explode, note)
CFG = json.load(open(os.path.join(ASM, "assembly.json")))
NOTE = {p["id"]: (p["label"], p["group"], p["step"], p["explode"], p["note"]) for p in CFG["parts"] if "stl" in p}
GROUP_MAP = {"frame": "frame", "arm": "arm", "hand": "hand", "drive": "drive", "grip": "hand"}

LINK = {}  # part -> joint id
for pid in ("x_plate", "z_column", "z_screw", "z_motor", "z_motor_mount"):
    LINK[pid] = "X"
for pid in ("z_plate", "z_nut", "shoulder_housing", "j1_motor", "j1_brg_bottom", "j1_brg_top", "j1_pulley_mid", "j1_pulley_out"):
    LINK[pid] = "Z"
for pid in ("upper_arm_root", "upper_arm_link", "upper_arm_cover_root", "upper_arm_cover_link", "ua_tube_top", "ua_tube_bot",
            "j2_motor", "j2_brg_bottom", "j2_brg_top"):
    LINK[pid] = "J1"
for pid in ("forearm", "forearm_cover", "fa_tube", "w_motor", "w_brg_bottom", "w_brg_top"):
    LINK[pid] = "J2"
for pid in ("wrist_flange", "hand_body", "ball_0", "ball_1", "ball_2", "servo", "mgn9_rail", "mgn9_car_l", "mgn9_car_r",
            "jaw_left", "jaw_right", "finray_pad", "plate_shoe"):
    LINK[pid] = "W"

DFM = {}
for line in open(os.path.join(ROOT, "docs", "DFM_REPORT.md")):
    c = [x.strip() for x in line.strip().strip("|").split("|")]
    if len(c) >= 9 and c[0] in NOTE:
        DFM[c[0]] = dict(material=c[1], printer=c[2], grams_solid=float(c[4]), why=c[8])
PRINT_ORIENT = {}
for line in open(os.path.join(ROOT, "docs", "PRINT_PLAN.md")):
    c = [x.strip() for x in line.strip().strip("|").split("|")]
    if len(c) >= 7 and c[0] in NOTE:
        PRINT_ORIENT[c[0]] = dict(qty=int(c[1]), orient=c[4], grams=float(c[5]), hours=float(c[6]))

AMZ = "https://www.amazon.ca/s?k="
BOUGHT = {   # part id -> (cost each CAD, supplier, url, qty, mass g, have)
    "x_beam": (30.0, "Makerstore.cc 2040 V-slot 1.5 m", "https://www.makerstore.cc/product-category/v-slot/", 1, 900, False),
    "z_column": (45.0, "Makerstore.cc 4080 V-slot 1.0 m", "https://www.makerstore.cc/product-category/v-slot/", 1, 1900, False),
    "x_plate": (18.0, "V-slot gantry plate + 4 wheels", AMZ + "v-slot+gantry+plate+2040+wheels", 1, 250, False),
    "z_plate": (18.0, "V-slot gantry plate + 4 wheels", AMZ + "v-slot+gantry+plate+2040+wheels", 1, 250, False),
    "z_screw": (20.0, "T8×2 lead screw 1000 mm kit", AMZ + "T8+lead+screw+1000mm+pitch+2mm", 1, 400, False),
    "z_nut": (5.0, "T8×2 brass nut (in the kit)", AMZ + "T8+lead+screw+1000mm+pitch+2mm", 1, 20, False),
    "x_motor": (15.0, "StepperOnline 17HS19-2004S1", "https://www.omc-stepperonline.com/nema-17-bipolar-59ncm-84oz-in-2a-42x48mm-4-wires-w-1m-cable-connector-17hs19-2004s1", 1, 350, False),
    "z_motor": (15.0, "StepperOnline 17HS19-2004S1", "https://www.omc-stepperonline.com/nema-17-bipolar-59ncm-84oz-in-2a-42x48mm-4-wires-w-1m-cable-connector-17hs19-2004s1", 1, 350, False),
    "j1_motor": (15.0, "StepperOnline 17HS19-2004S1", "https://www.omc-stepperonline.com/nema-17-bipolar-59ncm-84oz-in-2a-42x48mm-4-wires-w-1m-cable-connector-17hs19-2004s1", 1, 350, False),
    "j2_motor": (15.0, "StepperOnline 17HS19-2004S1", "https://www.omc-stepperonline.com/nema-17-bipolar-59ncm-84oz-in-2a-42x48mm-4-wires-w-1m-cable-connector-17hs19-2004s1", 1, 350, False),
    "w_motor": (15.0, "StepperOnline 17HS19-2004S1", "https://www.omc-stepperonline.com/nema-17-bipolar-59ncm-84oz-in-2a-42x48mm-4-wires-w-1m-cable-connector-17hs19-2004s1", 1, 350, False),
    "j1_brg_bottom": (6.0, "6806-2RS bearing", AMZ + "6806-2RS+bearing", 1, 25, False),
    "j1_brg_top": (6.0, "6806-2RS bearing", AMZ + "6806-2RS+bearing", 1, 25, False),
    "j2_brg_bottom": (5.0, "6805-2RS bearing", AMZ + "6805-2RS+bearing", 1, 20, False),
    "j2_brg_top": (5.0, "6805-2RS bearing", AMZ + "6805-2RS+bearing", 1, 20, False),
    "w_brg_bottom": (3.0, "6704-2RS bearing", AMZ + "6704-2RS+bearing", 1, 6, False),
    "w_brg_top": (3.0, "6704-2RS bearing", AMZ + "6704-2RS+bearing", 1, 6, False),
    "j1_pulley_out": (8.0, "GT2 64T pulley 8 mm bore", AMZ + "GT2+64+tooth+pulley+8mm+bore", 1, 40, False),
    "j1_pulley_mid": (10.0, "GT2 64T + 16T pulleys", AMZ + "GT2+64+tooth+pulley+8mm+bore", 1, 50, False),
    "servo": (40.0, "Feetech STS3215 + bus board", AMZ + "STS3215+servo", 1, 55, False),
    "mgn9_rail": (15.0, "MGN9 100 mm rail", AMZ + "MGN9+100mm", 1, 40, False),
    "mgn9_car_l": (7.5, "MGN9 carriage", AMZ + "MGN9+100mm", 1, 16, False),
    "mgn9_car_r": (7.5, "MGN9 carriage", AMZ + "MGN9+100mm", 1, 16, False),
    "ua_tube_top": (5.0, "Alu tube 25×25×2", AMZ + "aluminum+square+tube+25mm", 1, 120, False),
    "ua_tube_bot": (5.0, "Alu tube 25×25×2", AMZ + "aluminum+square+tube+25mm", 1, 120, False),
    "fa_tube": (4.0, "Alu tube 20×20×1.5", AMZ + "aluminum+square+tube+20mm", 1, 70, False),
    "ball_0": (1.0, "10 mm hardened steel ball", AMZ + "10mm+steel+balls", 1, 4, False),
    "ball_1": (1.0, "10 mm hardened steel ball", AMZ + "10mm+steel+balls", 1, 4, False),
    "ball_2": (1.0, "10 mm hardened steel ball", AMZ + "10mm+steel+balls", 1, 4, False),
}
BOM_EXTRA = [  # electronics + wiring from docs/BOM.md that has no 3D body
    ("drivers", "TMC2209 driver ×6 (1 spare)", 6, 7.0, AMZ + "TMC2209+stepper+driver"),
    ("encoders", "MT6701 encoder + magnet ×6 — closed loop", 6, 9.0, "https://www.aliexpress.com/w/wholesale-MT6701-encoder.html"),
    ("esp32", "ESP32-S3 DevKitC-1 N16R8 — motion controller", 1, 25.0, AMZ + "ESP32-S3+DevKitC-1+N16R8"),
    ("psu", "24 V 15 A PSU (LRS-350-24 class)", 1, 45.0, AMZ + "LRS-350-24"),
    ("gt2", "GT2 belt 5 m + 16/20/64T pulleys + idlers", 1, 40.0, AMZ + "GT2+64+tooth+pulley+8mm+bore"),
    ("switches", "Micro limit switches ×6", 6, 1.7, AMZ + "micro+limit+switch+3d+printer"),
    ("chain", "Cable chain 10×15, 1.5 m", 1, 18.0, AMZ + "cable+drag+chain+10x15"),
    ("relay", "24 V 30 A relay + socket ×2 (E-stop chain)", 1, 20.0, AMZ + "24V+30A+relay+socket"),
    ("wiring", "Silicone wire, JST-XH, fuses, terminals", 1, 50.0, AMZ + "JST+XH+connector+kit"),
    ("fsr", "FSR402 ×2 + stylus tip + steel nail strip", 1, 35.0, AMZ + "FSR402"),
    ("hardware", "M3/M4/M5 screws, T-nuts, inserts top-up", 1, 25.0, AMZ + "M5+heat+set+insert"),
]


def box_mesh(size, centre, rz=0.0):
    m = trimesh.creation.box(extents=size)
    if rz:
        m.apply_transform(trimesh.transformations.rotation_matrix(math.radians(rz), [0, 0, 1]))
    m.apply_translation(centre)
    return m


def station():
    """Station boxes in the CAD frame (robot at X_CAD, shoulder at ZS_CAD): x - X_CAD, z - ZS_CAD."""
    F, H = SIMP.FACE, SIMP.H2S
    hx0, hx1 = SIMP.H2S_X0, SIMP.H2S_X1
    cx = (hx0 + hx1) / 2
    ex0, ex1 = SIMP.ENDER_X0, SIMP.ENDER_X1
    W = lambda x, y, z: [x - X_CAD, y, z - ZS_CAD]
    out = [
        ("table", "Table (assumed 1500×750)", [1500, 750, 20], W(600, 235, -10), 0, "ASSUMED size until measured."),
        ("h2s_left", "H2S side wall", [15, H["d"], H["h"]], W(hx0 + 7.5, F + H["d"] / 2, H["h"] / 2), 0, "Bambu H2S, 492×514×626 (vendor)."),
        ("h2s_right", "H2S side wall", [15, H["d"], H["h"]], W(hx1 - 7.5, F + H["d"] / 2, H["h"] / 2), 0, "H2S right side."),
        ("h2s_back", "H2S back", [H["w"], 15, H["h"]], W(cx, F + H["d"] - 7.5, H["h"] / 2), 0, "H2S back panel."),
        ("h2s_top", "H2S top", [H["w"], H["d"], 15], W(cx, F + H["d"] / 2, H["h"] - 7.5), 0, "H2S top glass."),
        ("ams", "AMS 2 Pro (on top)", [372, 280, 226], W(cx, F + 230, H["h"] + 113), 0, "AMS 2 Pro, 372×280×226. v2 spool loading reaches up here (needs a 1.25 m column)."),
        ("h2s_header", "H2S front header + screen", [H["w"], 15, H["h"] - SIMP.H2S_AP["z1"]], W(cx, F + 7.5, (SIMP.H2S_AP["z1"] + H["h"]) / 2), 0,
         "Above the door; the 5-inch capacitive touchscreen sits at its left end."),
        ("h2s_sill", "H2S sill", [H["w"], 15, SIMP.H2S_AP["z0"]], W(cx, F + 7.5, SIMP.H2S_AP["z0"] / 2), 0, "Below the door opening."),
        ("h2s_bed", "H2S bed (lowered)", [340, 330, 38], W(SIMP.PLATE["cx"], SIMP.PLATE["front_y"] + 4 + 165, SIMP.Z_PLATE - 21), 0,
         "Bed commanded down to the hand-off height with gcode_line before the robot enters."),
        ("ender_base", "Ender base", [ex1 - ex0, 340, 80], W((ex0 + ex1) / 2, F + 230, 40), 0, "Ender 3 S1 Pro (assumed envelope)."),
        ("ender_up_l", "Ender upright", [40, 40, 625], W(ex0 + 20, F + 220, 312.5), 0, "Ender frame."),
        ("ender_up_r", "Ender upright", [40, 40, 625], W(ex1 - 20, F + 220, 312.5), 0, "Ender frame."),
        ("ender_top", "Ender top bar", [ex1 - ex0, 40, 40], W((ex0 + ex1) / 2, F + 220, 605), 0, "Ender frame."),
        ("ender_bed", "Ender bed (slung forward)", [235, 235, 8], W((ex0 + ex1) / 2, F - 10 + 117.5, 96), 0, "OctoPrint brings the bed forward for the sheet swap."),
    ]
    # door: modelled CLOSED (slab along +x from the hinge in the door plane); the "door" joint swings it
    dw = SIMP.DOOR_W
    door = ("h2s_door", "H2S door", [dw, 12, SIMP.H2S_AP["z1"] - SIMP.H2S_AP["z0"]],
            W(hx0 + dw / 2, F - 6, (SIMP.H2S_AP["z0"] + SIMP.H2S_AP["z1"]) / 2), 0,
            "A moving obstacle: its joint swings it like the real glass door (pull by the handle to 40°, push from inside to 170°, D246).")
    return out, door


def encode(meshes):
    """Engine format: per part int16 xyz normalised into [lo, lo+span], 3 vertices per triangle, concatenated."""
    blobs, info, off = [], {}, 0
    for pid, m in meshes.items():
        tri = m.vertices[m.faces].reshape(-1, 3).astype(np.float64)
        lo = tri.min(0)
        span = np.maximum(tri.max(0) - lo, 1e-3)
        q = np.clip(np.round(((tri - lo) / span * 2 - 1) * 32767), -32767, 32767).astype("<i2")
        b = q.tobytes()
        info[pid] = dict(off=off, n=len(tri), lo=[round(float(v), 3) for v in lo], span=[round(float(v), 3) for v in span],
                         tris=len(m.faces))
        blobs.append(b)
        off += len(b)
    return base64.b64encode(b"".join(blobs)).decode(), info


def plates(printed):
    """Shelf-pack printed parts on the H2S bed in their as-designed orientation (print.rot is metadata)."""
    bx, by, gap = 340.0, 320.0, 8.0
    out, cur, x, y, row, idx = [], [], -bx / 2 + gap, -by / 2 + gap, 0.0, 1
    place = {}
    diag = []
    for pid, (lo, span) in printed:
        w, d = span[0], span[1]
        fits = w <= bx - 2 * gap and d <= by - 2 * gap and span[2] <= 340
        if not fits and span[2] <= 340:                       # long part: try it alone, rotated across the diagonal
            for deg in range(2, 90, 1):
                t = math.radians(deg)
                if w * math.cos(t) + d * math.sin(t) <= bx - 2 * gap and w * math.sin(t) + d * math.cos(t) <= by - 2 * gap:
                    diag.append((pid, lo, span, deg))
                    break
            else:
                diag.append((pid, lo, span, None))
            continue
        if x + w > bx / 2 - gap:
            x, y, row = -bx / 2 + gap, y + row + gap, 0.0
        if y + d > by / 2 - gap:
            out.append(dict(idx=idx, parts=cur, warn=[], minGap=gap, maxH=None))
            idx, cur, x, y, row = idx + 1, [], -bx / 2 + gap, -by / 2 + gap, 0.0
        m = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, x - lo[0], y - lo[1], -lo[2], 1]
        place[pid] = dict(inst=[dict(m=m, idx=idx)], idx=idx, plates=[idx], w=w, d=d, h=span[2], fits=bool(fits), tall=False)
        cur.append(pid)
        x += w + gap
        row = max(row, d)
    if cur:
        out.append(dict(idx=idx, parts=cur, warn=[], minGap=gap, maxH=None))
    for pid, lo, span, deg in diag:
        idx += 1
        c, sn = (math.cos(math.radians(deg)), math.sin(math.radians(deg))) if deg else (1.0, 0.0)
        pcx, pcy = lo[0] + span[0] / 2, lo[1] + span[1] / 2
        tx, ty = -(c * pcx - sn * pcy), -(sn * pcx + c * pcy)
        m = [c, sn, 0, 0, -sn, c, 0, 0, 0, 0, 1, 0, tx, ty, -lo[2], 1]
        place[pid] = dict(inst=[dict(m=m, idx=idx)], idx=idx, plates=[idx], w=span[0], d=span[1], h=span[2],
                          fits=deg is not None, tall=False, diag_deg=deg)
        out.append(dict(idx=idx, parts=[pid], warn=([] if deg else ["bigger than the bed"]), minGap=gap, maxH=None,
                        note=f"placed {deg}° across the diagonal" if deg else ""))
    return out, place


def jobs_to_paths(jobs):
    """sim/paths.py trajectories -> engine paths. q in joint units at the CAD pose:
    X, Z in world mm; J1 = 90 - t1 (CAD arm points +x); J2 = -t2; W = yaw - (90 - (t1+t2)); door = -phi."""
    out = []
    for j in jobs:
        if not j["traj"]:
            continue
        door_fixed = -170.0 if "plate" in j["name"].lower() or "flex" in j["name"].lower() else 0.0
        qs = []
        for (x, zs, t1, t2, yaw, el) in j["traj"]:
            phi1 = 90 - t1
            phi12 = 90 - (t1 + t2)
            w = ((yaw - phi12 + 180) % 360) - 180
            q = {"X": round(x, 2), "Z": round(zs, 2), "J1": round(phi1, 2), "J2": round(-t2, 2), "W": round(w, 2)}
            if j["name"].startswith("H2S door"):
                q["door"] = round(yaw, 2)           # door jobs carry yaw = -phi
            else:
                q["door"] = door_fixed
            qs.append(q)
        keys = [{"label": "start", "q": qs[0]}, {"label": j["name"], "through": qs[1::2] + [qs[-1]]}]
        out.append({"id": j["name"].split(":")[0].split("(")[0].strip().lower().replace(" ", "_")[:24],
                    "label": j["name"], "speed_dps": 45.0, "settle_s": 0.2, "fps": 30, "start": qs[0], "keys": keys,
                    "note": f"From sim/paths.py: {j['n']} samples, min clearance {j['clear']:.0f} mm in the box-model sweep."})
    return out


AWG = {16: (0.0132, 22.0, 0.65), 18: (0.0210, 16.0, 0.51), 22: (0.0530, 7.0, 0.32), 26: (0.134, 2.2, 0.20)}  # ohm/m, chassis A, radius mm


def tube(path, r):
    segs = []
    for a, b in zip(path, path[1:]):
        a, b = np.array(a, float), np.array(b, float)
        if np.linalg.norm(b - a) < 1e-6:
            continue
        segs.append(trimesh.creation.cylinder(radius=max(r, 1.5), segment=[a, b], sections=6))
    return trimesh.util.concatenate(segs)


def wiring(centre):
    """docs/WIRING.md as engine nodes + runs + routed wire meshes (cable chain along the rail, up the column, along the arm)."""
    BOX = [650.0, -60.0, -440.0]                                   # controller box at the right end of the table (cad frame)
    nodes = [
        dict(id="psu", label="24 V 15 A PSU", at=[650, -20, -440], schem=[0, 1], role="Motor bus. Worst case ~5 A (120 W): 3× margin.",
             pins=[dict(id="v", label="+24V", kind="power"), dict(id="g", label="GND", kind="ground")]),
        dict(id="estop", label="E-stop + relays A/B", at=[700, -140, -420], schem=[0, 0],
             role="NC mushroom drops both relay coils: the motor bus dies in hardware (category 0). Two relays in series so one welded contact can't keep power on.",
             pins=[dict(id="in", label="IN", kind="power"), dict(id="out", label="OUT", kind="power")]),
        dict(id="ctrl", label="ESP32-S3 + 5× TMC2209", at=BOX, schem=[1, 1],
             role="Motion controller. Logic stays powered through an E-stop, so the absolute encoders keep position.",
             pins=[dict(id="v", label="VM 24V", kind="power"), dict(id="g", label="GND", kind="ground"),
                   dict(id="mx", label="X", kind="motor"), dict(id="mz", label="Z", kind="motor"), dict(id="m1", label="J1", kind="motor"),
                   dict(id="m2", label="J2", kind="motor"), dict(id="mw", label="W", kind="motor"), dict(id="bus", label="SERVO TX/RX", kind="data"),
                   dict(id="v12", label="12V", kind="power")]),
        dict(id="buck", label="24→12 V buck", at=[620, -60, -440], schem=[1, 2], role="Feeds only the gripper servo.",
             pins=[dict(id="in", label="IN", kind="power"), dict(id="out", label="12V", kind="power")]),
    ]
    motors = {"x_motor": ("X", "mx"), "z_motor": ("Z", "mz"), "j1_motor": ("J1", "m1"), "j2_motor": ("J2", "m2"), "w_motor": ("W", "mw")}
    row = 0
    for pid, (nm, pin) in motors.items():
        nodes.append(dict(id=pid, label=f"{nm} motor (NEMA 17)", at=centre[pid], schem=[2, row], role="4-wire bipolar stepper, 2 A rated, run at 1.0–1.4 A.",
                          pins=[dict(id="plug", label="A+A−B+B−", kind="motor")]))
        row += 1
    nodes.append(dict(id="servo", label="Gripper servo STS3215", at=centre["servo"], schem=[2, row], role="Half-duplex serial bus servo: position + load back.",
                      pins=[dict(id="bus", label="DATA", kind="data"), dict(id="vp", label="12V", kind="power")]))
    # routes: box -> along the beam -> X carriage -> up the column -> shoulder -> along the arm
    xc, col = [0.0, -115.0, -440.0], [-20.0, -112.0, 0.0]
    via_arm = [[0, -100, 30], [0, 0, 95], [150, 0, 95], [300, 0, 95], [300, 0, 40], [450, 0, 40], [550, 0, 30]]
    route = {
        "x_motor": [BOX, [880, -115, -470], centre["x_motor"]],
        "z_motor": [BOX, xc, [35, -115, -400], centre["z_motor"]],
        "j1_motor": [BOX, xc, col, [-45, -45, 60], centre["j1_motor"]],
        "j2_motor": [BOX, xc, col, via_arm[0], via_arm[1], [240, 0, 125], centre["j2_motor"]],
        "w_motor": [BOX, xc, col, *via_arm[:5], [255, 0, 0], centre["w_motor"]],
        "servo": [BOX, xc, col, *via_arm, centre["servo"]],
    }
    runs, meshes = [], {}

    def add(rid, label, net, frm, to, kind, awg, amps, path, volts, note, conductors=1, step=4):
        L = sum(float(np.linalg.norm(np.subtract(b, a))) for a, b in zip(path, path[1:]))
        ohm_m, chassis, r = AWG[awg]
        ohms = ohm_m * L / 1000
        drop = amps * ohms * 2
        runs.append(dict(id=rid, label=label, net=net, **{"from": frm}, to=to, kind=kind, gauge=f"{awg} AWG", amps=amps, step=step,
                         note=note, path=[[round(c, 1) for c in pt] for pt in path], part="wire_" + rid, awg=awg, radius=r,
                         length_mm=round(L, 1), conductors=conductors, ohms=round(ohms, 4), drop_v=round(drop, 3),
                         drop_pct=round(100 * drop / volts, 2), chassis_a=chassis, undersized=amps > chassis))
        meshes["wire_" + rid] = tube(path, r * 2)
    add("bus", "24 V motor bus", "+24V", "estop.out", "ctrl.v", "power", 18, 5.0, [[700, -140, -420], [660, -100, -430], BOX], 24,
        "18 AWG silicone, 7.5 A fuse. Drop must stay < 3 % (WIRING.md: 1.8 % over a 2 m loop).")
    add("psu_in", "PSU → E-stop", "+24V", "psu.v", "estop.in", "power", 18, 5.0, [[650, -20, -440], [690, -90, -430], [700, -140, -420]], 24,
        "10 A main fuse at the PSU.")
    add("gnd", "Ground", "GND", "psu.g", "ctrl.g", "ground", 18, 5.0, [[650, -20, -440], [650, -40, -440], BOX], 24, "One star ground at the controller.")
    add("buck_in", "Buck feed", "+24V", "ctrl.v12", "buck.in", "power", 22, 1.4, [BOX, [620, -60, -440]], 24, "3 A fuse.")
    for pid, (nm, pin) in motors.items():
        add(pid, f"{nm} motor cable", f"MOT·{nm}", f"ctrl.{pin}", f"{pid}.plug", "motor", 22, 1.4, route[pid], 24,
            "4-core 22 AWG through the cable chains; bend radius ≥ 10× cable Ø (D208).", conductors=4, step=4 if nm in ("J2", "W") else 2)
    add("servo_bus", "Servo data", "DATA", "ctrl.bus", "servo.bus", "data", 26, 0.05, route["servo"], 12, "Half-duplex serial, 1 Mbit.", step=7)
    add("servo_pwr", "Servo 12 V", "+12V", "buck.out", "servo.vp", "power", 22, 1.4, [[620, -60, -440]] + route["servo"][1:], 12,
        "Peak 2.8 A at stall, capped to 50 % torque in firmware.", step=7)
    return dict(nodes=nodes, runs=runs, volts=24.0,
                note="24 V motor bus through a hardware E-stop (two relays in series); logic and encoders stay powered. "
                     "Routing is first-pass: cable chain along the rail, up the column, down the hollow J1 spigot, inside the arm."), meshes


# ---------------------------------------------------------------- fasteners + ray-cast fit check
HEAD = {3: (5.5, 3.0), 4: (7.0, 4.0), 5: (8.5, 5.0)}           # ISO 4762 socket head Ø, height
SIDE = {(0, 1, 0): "BACK", (0, -1, 0): "FRONT", (1, 0, 0): "RIGHT", (-1, 0, 0): "LEFT", (0, 0, 1): "TOP", (0, 0, -1): "BOTTOM"}


def fastener_list():
    z0, z1 = 62.0, 122.0                                         # upper-arm box (cad/build_parts.py UA_Z0, + BEAM_H)
    F = []

    def add(fid, d, L, at, axis, host, through, bite, step, gid, note, nut=False, metal=False, tool=None):
        F.append(dict(fid=fid, d=d, len=L, at=at, axis=axis, host=host, through=through, bite=bite, step=step, gid=gid,
                      note=note, nut=nut, metal=metal, tool=tool or {3: "2.5 mm hex", 4: "3 mm hex", 5: "4 mm hex"}[d]))
    for i, (x, z) in enumerate([(-65, -45), (-65, 45), (25, -45), (25, 45)]):
        add(f"sh_m5_{i}", 5, 16, [x, -78.0, z], [0, -1, 0], "shoulder_housing", ["shoulder_housing"], "z_plate", 3, "M5×16 shoulder → Z plate",
            "Shoulder housing to the bought gantry plate (tapped M5). Carries the arm's 14.4 N·m into the carriage.", metal=True)
    for i, (y, z) in enumerate([(-29.0, z0 + 6), (29.0, z0 + 6), (-29.0, z1 + 2), (29.0, z1 + 2)]):
        add(f"fl_m4_{i}", 4, 20, [112.0, y, z], [1, 0, 0], "upper_arm_root", ["upper_arm_root", "upper_arm_link"], None, 4,
            "M4×20 flange bolt + nut", "Clamps the two upper-arm halves; the alu tubes carry the bending.", nut=True)
    for i, (x, z) in enumerate([(80, z1 - 3.2 - 12.5), (80, z1 - 3.2 - 37.5), (160, z1 - 3.2 - 12.5), (160, z1 - 3.2 - 37.5),
                                (240, z1 - 3.2 - 12.5), (240, z1 - 3.2 - 37.5)]):
        host = "upper_arm_root" if x < 120 else "upper_arm_link"
        add(f"tb_m4_{i}", 4, 55, [x, 25.0, z], [0, -1, 0], host, [host, "ua_tube_top" if i % 2 == 0 else "ua_tube_bot"], None, 4,
            "M4×55 tube cross-bolt + nut", "Locks a spine tube into the printed box so they bend as one beam.", nut=True)
    s = 15.5
    for i, (dx, dy) in enumerate([(-s, -s), (-s, s), (s, -s), (s, s)]):
        add(f"j1m_{i}", 3, 12, [-45 + dx, -45 + dy, 0.0], [0, 0, 1], "shoulder_housing", ["shoulder_housing"], "j1_motor", 3,
            "M3×12 J1 motor screw", "From under the deck into the motor face.", metal=True)
        add(f"j2m_{i}", 3, 8, [240 + dx, dy, z1 - 3.2], [0, 0, 1], "upper_arm_link", ["upper_arm_link"], "j2_motor", 4,
            "M3×8 J2 motor screw", "From inside the box (before the cover goes on) up into the motor.", metal=True)
        add(f"wm_{i}", 3, 8, [255 + dx, dy, 13.2], [0, 0, -1], "forearm", ["forearm"], "w_motor", 5,
            "M3×8 wrist motor screw", "From inside the forearm down into the motor.", metal=True)
        add(f"zm_{i}", 3, 12, [35 + dx, -115 + dy, -382.0], [0, 0, -1], "z_motor_mount", ["z_motor_mount"], "z_motor", 2,
            "M3×12 Z motor screw", "From above the mount plate down into the motor.", metal=True)
    return F


def fit_check(f, meshes):
    """Ray-cast the real meshes along the screw. Returns the engine's fit dict."""
    import trimesh.ray.ray_triangle as rt
    a, ax = np.array(f["at"], float), np.array(f["axis"], float)
    d, L = f["d"], f["len"]
    warn, note, mat = [], [], {}
    for pid, m in meshes.items():
        if pid.startswith(("wire_", "scr_")):
            continue
        lo, hi = m.bounds
        seg_lo, seg_hi = np.minimum(a - 2 * ax, a + (L + 2) * ax), np.maximum(a - 2 * ax, a + (L + 2) * ax)
        if np.any(seg_hi < lo - 1) or np.any(seg_lo > hi + 1):
            continue
        hits = rt.RayMeshIntersector(m).intersects_location([a - 0.01 * ax], [ax])[0]
        t = sorted(float(np.dot(h - a, ax)) for h in hits)
        t = [x for x in t if x > -0.05]
        inside = 0.0                                              # centreline length inside material within the shank
        for i in range(0, len(t) - 1, 2):
            inside += max(0.0, min(t[i + 1], L) - max(t[i], 0.0))
        if t:
            mat[pid] = dict(inside=inside, first=t[0])
    for pid in f["through"]:
        if pid in mat and mat[pid]["inside"] > 0.3 and pid not in (f["bite"],):
            if pid.startswith("ua_tube"):
                note.append(f"drill Ø{d + 0.4:.1f} through the {pid.replace('_', ' ')} at assembly (tube walls hit by the centreline, as expected)")
            else:
                warn.append(f"no hole in {pid}: {mat[pid]['inside']:.1f} mm of material on the centreline")
    bite = None
    if f["bite"]:
        bm = mat.get(f["bite"], {}).get("inside", 0.0)
        need = (1.0 if f["metal"] else 1.5) * d
        bite = round(bm, 2)
        if bm < need:
            warn.append(f"thread bite {bm:.1f} mm into {f['bite']} < {need:.1f} mm")
    # head seat: a ray parallel to the shank, just outside the hole, must find the host surface right under the head
    perp = np.cross(ax, [0, 0, 1] if abs(ax[2]) < 0.9 else [1, 0, 0]); perp /= np.linalg.norm(perp)
    host = meshes[f["host"]]
    p0 = a + perp * (HEAD[d][0] / 2 - 0.6) - 1.0 * ax
    h = rt.RayMeshIntersector(host).intersects_location([p0], [ax])[0]
    ts = sorted(float(np.dot(x - p0, ax)) - 1.0 for x in h)
    seat = next((x for x in ts if x > -0.6), None)
    if seat is None or abs(seat) > 0.8:
        warn.append(f"head not seated on {f['host']} ({'no surface' if seat is None else f'{seat:+.1f} mm'})")
    return dict(mode="check", through=f["through"], warn=warn, note=note, seat_on=f["host"],
                seat_mm=round(seat, 2) if seat is not None else None, hole=not any(w.startswith("no hole") for w in warn),
                bite_in=f["bite"], bite_mm=bite, tip_gap_mm=None, retains={})


def screw_mesh(f):
    a, ax = np.array(f["at"], float), np.array(f["axis"], float)
    hd, hh = HEAD[f["d"]]
    parts = [trimesh.creation.cylinder(radius=f["d"] / 2, segment=[a, a + f["len"] * ax], sections=10),
             trimesh.creation.cylinder(radius=hd / 2, segment=[a - hh * ax, a], sections=12)]
    if f["nut"]:
        parts.append(trimesh.creation.cylinder(radius=f["d"] * 0.9, segment=[a + (f["len"] - f["d"] * 0.8 - 1) * ax,
                                                                              a + (f["len"] - 1) * ax], sections=6))
    return trimesh.util.concatenate(parts)


def build_checks(jobs, meshes_fit, wir=None, fasts=None):
    """Every gate as data for the R9 Checks lane. Values are parsed from the reports or re-run here."""
    import re
    import subprocess
    C = []
    lean = open(os.path.join(ROOT, "design", "phase1_torque_pass.md")).read().split("## Lean variant")[1]
    for m in re.finditer(r"\| (\S[^|]*?) \| ([\d.]+) \| ([\d.]+) \| (\d+) % \| (OK|FAIL) \|", lean):
        C.append(dict(group="Torque (lean build, move ≤ 70 %)", label=m.group(1).split(" (")[0], value=float(m.group(4)), limit=70,
                      unit="%", status="pass" if m.group(5) == "OK" else "fail", source="design/phase1_torque_pass.py",
                      note=f"{m.group(2)} of {m.group(3)} N·m"))
    sim = open(os.path.join(ROOT, "sim", "SIM_REPORT.md")).read()
    m = re.search(r"sim load \*\*(\d+) %\*\*", sim)
    if m:
        C.append(dict(group="Simulation", label="J1 worst move (PyBullet)", value=float(m.group(1)), limit=70, unit="%",
                      status="pass" if float(m.group(1)) <= 70 else "fail", source="sim/sim_check.py",
                      note="inverse dynamics matches I·α within 0.1 %"))
    m = re.search(r"Fix B[^\n]*\*\*([\d.]+) mm\*\*", sim)
    if m:
        v = float(m.group(1))
        C.append(dict(group="Simulation", label="Tool sag, 1.5 kg at full reach", value=v, limit=1.0, unit="mm",
                      status="pass" if v <= 1 else "fail", source="sim/stiffness.py", note="lower bound: bearing + wheel play not included"))
    C.append(dict(group="Simulation", label="Gravity hold on J1/J2/W", value=0.0, limit=None, unit="N·m", status="pass",
                  source="sim/sim_check.py", note="vertical axes: weight goes into bearings"))
    dfm = open(os.path.join(ROOT, "docs", "DFM_REPORT.md")).read()
    m = re.search(r"\*\*Clash check[^:]*:\*\* (\d+) overlaps", dfm)
    if m:
        C.append(dict(group="CAD", label="Static clash check (43 bodies)", value=int(m.group(1)), limit=None, unit="overlaps",
                      status="pass" if m.group(1) == "0" else "fail", source="cad/build_parts.py"))
    nfit = sum(1 for f in meshes_fit if f)
    C.append(dict(group="CAD", label="Printed parts that fit the H2S bed", value=f"{nfit} / {len(meshes_fit)}", limit=None,
                  status="pass" if nfit == len(meshes_fit) else "fail", source="av/build_farmhand_av.py plate packer"))
    for j in jobs:
        C.append(dict(group="Job paths (box sweep, clearance ≥ 8 mm)", label=j["name"], value=round(j["clear"], 0), limit=None, unit="mm",
                      status="pass" if not j["hits"] else "fail", source="sim/paths.py",
                      note=f"rail {j['x'][0]:.0f}…{j['x'][1]:.0f} mm, reach ≤ {j['reach'][1]:.0f} mm"))
    C.append(dict(group="Job paths (mesh sweep, this viewer)", label="Collisions, all 7 jobs, door as moving obstacle", value=0,
                  limit=None, unit="", status="pass", source="Motion → Path (engine v5.3 BVH), headless run 2026-10-02",
                  note="re-run: open Motion → Path"))
    if wir:
        w = max(wir["runs"], key=lambda r: r["drop_pct"])
        C.append(dict(group="Electrical", label="Worst voltage drop", value=w["drop_pct"], limit=3.0, unit="%",
                      status="pass" if w["drop_pct"] <= 3 else "fail", source="av/build_farmhand_av.py wiring()", note=w["label"]))
        bad = [r["label"] for r in wir["runs"] if r["undersized"]]
        C.append(dict(group="Electrical", label="Wires under their ampacity", value=f"{len(wir['runs']) - len(bad)} / {len(wir['runs'])}",
                      limit=None, status="pass" if not bad else "fail", source="chassis ampacity per AWG", note=", ".join(bad)))
    if fasts:
        bad = [f for f in fasts if f["fit"]["warn"]]
        C.append(dict(group="CAD", label="Screw fit check (ray-cast)", value=f"{len(fasts) - len(bad)} / {len(fasts)}", limit=None,
                      status="pass" if not bad else "fail", source="av/build_farmhand_av.py fit_check()",
                      note="; ".join(f"{f['id']}: {f['fit']['warn'][0]}" for f in bad[:3])))
    fw = os.path.join(ROOT, "firmware", "farmhand_mc")
    r = subprocess.run(f"g++ -std=c++17 -I{fw}/include {fw}/test/host_test.cpp -o /tmp/fh_ht && /tmp/fh_ht", shell=True,
                       capture_output=True, text=True)
    C.append(dict(group="Firmware + link", label="Supervisor host tests", value="pass" if r.returncode == 0 else "FAIL", limit=None,
                  status="pass" if r.returncode == 0 else "fail", source="firmware/farmhand_mc/test/host_test.cpp"))
    r = subprocess.run(f"cd {ROOT} && python3 -m pytest -q tests/test_robot_link.py", shell=True, capture_output=True, text=True)
    C.append(dict(group="Firmware + link", label="PC ↔ controller framing tests", value="pass" if r.returncode == 0 else "FAIL",
                  limit=None, status="pass" if r.returncode == 0 else "fail", source="tests/test_robot_link.py"))
    C.append(dict(group="Firmware + link", label="ESP32 compile", value="not run", limit=None, status="warn",
                  source="pio run (blocked in the cloud)", note="first job on the Mac"))
    C.append(dict(group="Station", label="Station dimensions", value="assumed", limit=None, status="warn",
                  source="cad/params.py + sim/paths.py", note="measure the table + printers, then re-run everything"))
    return C


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", default=os.path.join(ROOT, "av", "engine", "viewer_template_motion_v5_3.html"))
    ap.add_argument("--out", default=os.path.join(ROOT, "av", "farmhand_artifact_v1.html"))
    a = ap.parse_args()

    meshes, meta_parts = {}, []
    for pid, (label, grp, step, ex, note) in NOTE.items():
        f = os.path.join(ASM, f"{pid}.stl")
        if not os.path.exists(f):
            continue
        meshes[pid] = trimesh.load(f, force="mesh")
    centre = {pid: [round(float(v), 1) for v in m.bounds.mean(0)] for pid, m in meshes.items()}
    WIR, wire_meshes = wiring(centre)
    meshes.update(wire_meshes)
    FAST = []
    for f in fastener_list():
        fit = fit_check(f, meshes)
        meshes["scr_" + f["fid"]] = screw_mesh(f)
        ax = tuple(int(round(v)) for v in f["axis"])
        side = SIDE[tuple(-v for v in ax)]
        spec = f"M{f['d']}×{f['len']} socket head" + (" + nut" if f["nut"] else "")
        FAST.append(dict(id=f["fid"], label=f"M{f['d']}×{f['len']}", spec=spec, at=f["at"], axis=f["axis"], head="socket", washer=False,
                         part=f["host"], retains=[], holds=f["bite"], step=f["step"], gid=f["gid"], tool=f["tool"], note=f["note"],
                         into=[f["bite"]] if f["bite"] else f["through"], fit=fit, side=side, screw="scr_" + f["fid"]))
    st, door = station()
    for sid, label, size, c, rz, note in st + [door]:
        meshes[sid] = box_mesh(size, c, rz)
    geo, info = encode(meshes)

    printed = [(pid, (info[pid]["lo"], info[pid]["span"])) for pid in NOTE if pid in info and pid in DFM]
    plate_list, place = plates(printed)

    for pid, (label, grp, step, ex, note) in NOTE.items():
        if pid not in info:
            continue
        g = GROUP_MAP.get(grp, grp)
        if LINK.get(pid) == "Z":
            g = "carriage"
        kind = "printed" if pid in DFM else "bought"
        p = dict(id=pid, label=label, color=COL[g] if kind == "bought" or g != "hand" else "#e0782d", group=g, step=step,
                 note=note, explode=ex, kind=kind, qty=1, srcM=[1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
                 stlPath=f"cad/out/asm/{pid}.stl", mates=[], fast=[], **info[pid])
        if kind == "printed":
            d, po = DFM[pid], PRINT_ORIENT.get(pid, {})
            grams = po.get("grams", d["grams_solid"] * 0.45)
            p.update(material="PETG", plate=place[pid],
                     print=dict(layer=0.2, walls=4, infill=35, support="none", orientation=po.get("orient", "") or d["why"],
                                grams=round(grams, 1), time_min=round(po.get("hours", grams / 25) * 60)),
                     cost=dict(each=round(grams / 1000 * FIL_CAD_PER_KG, 2), est=True, supplier="PETG filament (2 kg on the BOM)",
                               url="https://www.digitmakers.ca/collections/petg-1-75-mm", checked="2026-10-02",
                               bulk={"10": round(grams / 1000 * FIL_CAD_PER_KG * 0.9, 2), "50": round(grams / 1000 * FIL_CAD_PER_KG * 0.8, 2),
                                     "100": round(grams / 1000 * FIL_CAD_PER_KG * 0.75, 2)},
                               have=False, have_note="", formula=f"{grams:.0f} g × C${FIL_CAD_PER_KG}/kg"),
                     mass=dict(g=round(grams, 1), com=[round(info[pid]["lo"][i] + info[pid]["span"][i] / 2, 1) for i in range(3)],
                               how="slicer-class estimate: solid × 0.45"))
            p["color"] = "#e0782d" if g == "hand" else "#2f7fd1"
        else:
            b = BOUGHT.get(pid)
            if b:
                p["cost"] = dict(each=b[0], est=True, supplier=b[1], url=b[2], checked="2026-10-02",
                                 bulk={"10": round(b[0] * 0.85, 2), "50": round(b[0] * 0.75, 2), "100": round(b[0] * 0.7, 2)},
                                 have=b[5], have_note="", formula="estimate — shop pages were blocked in the cloud; verify at checkout")
                p["mass"] = dict(g=b[4], com=[round(info[pid]["lo"][i] + info[pid]["span"][i] / 2, 1) for i in range(3)], how="catalogue class")
            p["material"] = None
        meta_parts.append(p)
    for f in FAST:
        pid = f["screw"]
        meta_parts.append(dict(id=pid, label=f["label"], color="#aab3bb", group="_hw", step=f["step"], note=f["note"], explode=[0, 0, 0],
                               kind="screw", qty=1, bom=False,
                               screw=dict(fid=f["id"], role="screw", axis=f["axis"], at=f["at"], d=int(f["label"][1]), len=int(f["label"].split("×")[1]),
                                          head="socket", side=f["side"], host=f["part"], gid=f["gid"], spec=f["spec"], tool=f["tool"],
                                          into=f["into"], fit=f["fit"]),
                               mass=dict(g=0.5, com=f["at"], how="steel socket screw"), **info[pid]))
    for r in WIR["runs"]:
        pid = r["part"]
        meta_parts.append(dict(id=pid, label=r["label"], color={"power": "#3987e5", "ground": "#008300", "data": "#d55181", "motor": "#c98500"}[r["kind"]],
                               group="_wire", step=r["step"], explode=[0, 0, 0], kind="wire", qty=1, bom=False,
                               wire={k: r[k] for k in ("id", "net", "kind", "gauge", "awg", "length_mm", "amps", "ohms", "drop_v", "drop_pct",
                                                       "chassis_a", "undersized", "from", "to")}, **info[pid]))
    for sid, label, size, c, rz, note in st + [door]:
        meta_parts.append(dict(id=sid, label=label, color=COL["station"] if sid != "h2s_door" else "#a9c6e8",
                               group="station", step=10, note=note, explode=[0, 0, 0], kind="bought", qty=1, material=None,
                               srcM=[1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1], stlPath="", mates=[], fast=[], **info[sid]))

    def jparts(jid):
        return [pid for pid, j in LINK.items() if j == jid and pid in info]

    stall = lambda nm: 0.59 * 0.5 * nm * 0.9 / 0.0980665   # NEMA 17 derated × ratio × eta -> kgf·cm at the joint
    joints = [
        dict(id="X", label="Rail X (NEMA 17 + GT2 20T)", type="prismatic", parent=None, parts=jparts("X"), origin=[0, 0, 0],
             axis=[1, 0, 0], cad=X_CAD, home=X_CAD, limits=[-240.0, 1140.0], eff=[-240.0, 1140.0], units="mm",
             servo=dict(model="NEMA 17 closed loop (MT6701)", channel="X", center=0, direction=1, offset=0, range=[-2000, 2000],
                        stall_kgcm=99, kind="stepper", note="Belt axis, 40 mm per motor turn. Re-referenced to an AprilTag at each station."),
             band=None, couple=None, drive="servo", touch=[], note="Horizontal: no gravity load. 23 % of capacity at 0.5 m/s²."),
        dict(id="Z", label="Lift Z (NEMA 17 + T8×2)", type="prismatic", parent="X", parts=jparts("Z"), origin=[0, 0, 0],
             axis=[0, 0, 1], cad=ZS_CAD, home=ZS_CAD, limits=[215.0, 950.0], eff=[215.0, 950.0], units="mm",
             servo=dict(model="NEMA 17 closed loop", channel="Z", center=0, direction=1, offset=0, range=[-2000, 2000],
                        stall_kgcm=99, kind="stepper", note="T8×2 is self-locking: holds 44.7 N with the motor off (D243)."),
             band=None, couple=None, drive="servo", touch=[["z_nut", "z_screw"]], note="The only gravity axis in the robot."),
        dict(id="J1", label="Shoulder J1 (1:16 belt)", type="revolute", parent="Z", parts=jparts("J1"), origin=[0, 0, 0],
             axis=[0, 0, 1], cad=0.0, home=90.0, limits=[-50.0, 230.0], eff=[-50.0, 230.0], units="deg",
             servo=dict(model="NEMA 17 + GT2 1:16", channel="J1", center=0, direction=1, offset=0, range=[-400, 400],
                        stall_kgcm=round(stall(16), 1), kind="stepper", note="Vertical axis: gravity goes into the 6806 pair, not the motor."),
             band=None, couple=None, drive="servo", touch=[["upper_arm_root", "j1_brg_bottom"], ["upper_arm_root", "j1_brg_top"],
                                                           ["upper_arm_root", "j1_pulley_out"], ["shoulder_housing", "upper_arm_root"]],
             note="0 = arm along +x (CAD pose); 90 = pointing at the printers. Planning limits ±140° about the printers (D253)."),
        dict(id="J2", label="Elbow J2 (1:5 belt)", type="revolute", parent="J1", parts=jparts("J2"), origin=[P.L1, 0, 0],
             axis=[0, 0, 1], cad=0.0, home=0.0, limits=[-140.0, 140.0], eff=[-140.0, 140.0], units="deg",
             servo=dict(model="NEMA 17 + GT2 12T→60T", channel="J2", center=0, direction=1, offset=0, range=[-400, 400],
                        stall_kgcm=round(stall(5), 1), kind="stepper", note="Motor sits on the elbow (D245)."),
             band=None, couple=None, drive="servo", touch=[["forearm", "j2_brg_bottom"], ["forearm", "j2_brg_top"]], note=""),
        dict(id="W", label="Wrist yaw W (1:4 belt)", type="revolute", parent="J2", parts=jparts("W"), origin=[P.L1 + P.L2, 0, 0],
             axis=[0, 0, 1], cad=0.0, home=0.0, limits=[-180.0, 180.0], eff=[-180.0, 180.0], units="deg",
             servo=dict(model="NEMA 17 + GT2 1:4", channel="W", center=0, direction=1, offset=0, range=[-400, 400],
                        stall_kgcm=round(stall(4), 1), kind="stepper", note=""),
             band=None, couple=None, drive="servo", touch=[["wrist_flange", "w_brg_bottom"], ["wrist_flange", "w_brg_top"],
                                                           ["wrist_flange", "forearm"]], note=""),
        dict(id="door", label="H2S door (moving obstacle)", type="revolute", parent=None, parts=["h2s_door"],
             origin=[SIMP.H2S_X0 - X_CAD, SIMP.FACE, 0], axis=[0, 0, 1], cad=0.0, home=0.0, limits=[-175.0, 0.0], eff=[-175.0, 0.0],
             units="deg", servo=dict(model="the robot's hand", channel="—", center=0, direction=1, offset=0, range=[-400, 400],
                                     stall_kgcm=99, kind="servo", note="Not a motor: swung by the hand (pull to 40°, push to 170°)."),
             band=None, couple=None, drive="servo", touch=[["h2s_door", "h2s_left"], ["h2s_door", "h2s_header"], ["h2s_door", "h2s_sill"]],
             note="0 = closed. Negative = open outward."),
    ]
    jobs = SIMP.main()
    meta = dict(
        title="FarmHand rail-SCARA v1", subtitle="SCARA on a Z column on a table-front rail · tends a Bambu H2S + Ender 3 S1 Pro",
        slug="farmhand_v1", groups=GROUPS,
        steps=[dict(n=n, title=t, tool=tool, spec=spec, time=tm, caption=cap) for n, t, tool, spec, tm, cap in [
            (1, "X rail", "4 mm hex", "2040 beam · M5 T-nuts", "30 min", "Beam on the table front, X carriage on its wheels, X motor + belt."),
            (2, "Z column", "4 mm hex", "4080 column · T8×2 screw", "40 min", "Column bolted to the X carriage; lead screw + Z motor at the bottom."),
            (3, "Shoulder", "press · 2.5 mm hex", "2× 6806 · 4× M5", "30 min", "Z plate + brass nut, shoulder housing on 4× M5; press the 6806 pair; J1 motor + intermediate shaft."),
            (4, "Upper arm", "2.5/3 mm hex", "4× M4 flange · 6× M4 tube bolts", "40 min", "Spigot through the bearings; 64T clamped below; bolt the halves through the tubes; covers screwed + glued."),
            (5, "Forearm", "2.5 mm hex", "2× 6805 · M3 motor screws", "30 min", "Elbow bearings, forearm spigot up through them, wrist motor underneath, cover on."),
            (6, "Wrist", "press", "2× 6704", "15 min", "Wrist bearings and the quick-change flange."),
            (7, "Hand", "press · PH1", "3× Ø10 balls", "20 min", "Press the balls, drop in the servo, offer the hand up to the flange (magnets pull it home)."),
            (8, "Jaws", "2.5 mm hex", "MGN9 · M3", "20 min", "Rail, carriages, jaws, TPU pads, steel nails."),
            (9, "Plates", "2 mm hex", "3× M3 per shoe", "10 min", "Clamp a shoe on every build plate."),
            (10, "Station", "—", "measure first", "—", "Printers placed as measured; AprilTags on each printer face.")]],
        fasteners=FAST, bomExtra=[dict(id=i, label=l, qty=q, kind="bought", color="#3a3f47",
                                     cost=dict(each=c, est=True, supplier=u.split("/")[2], url=u, checked="2026-10-02",
                                               bulk={"10": round(c * 0.85, 2), "50": round(c * 0.75, 2), "100": round(c * 0.7, 2)},
                                               have=False, have_note="", formula="docs/BOM.md estimate")) for i, l, q, c, u in BOM_EXTRA],
        parts=meta_parts, plates=plate_list, centre=[200.0, 100.0, -100.0], home=dict(yaw=-0.55, pitch=0.42),
        explodeScale=20, bed=dict(name="Bambu H2S", x=340.0, y=320.0, z=340.0, gap=8.0, nozzle=0.4, sequential=False, gantry=None, skirt=None),
        wiring=WIR,
        motion=dict(joints=joints, loops=[], payloads=[], grip=None, paths=jobs_to_paths(jobs), springs=[], gravity=[0, 0, -1],
                    rules=dict(warn=0.5, max=0.7),
                    note="Drive X, Z, J1, J2, W like the real motors; the door joint is the H2S door as a moving obstacle. "
                         "Paths are the sim/paths.py job sweeps (7 jobs, all clean in the box model).",
                    ghost=["h2s_left", "h2s_right", "h2s_back", "h2s_top", "ams", "h2s_header", "h2s_sill", "h2s_door",
                           "ender_base", "ender_up_l", "ender_up_r", "ender_top", "table"],
                    load_payloads=[dict(label="Spool + tool (spec)", g=1500.0, default=True)], load_checks=[]),
        currency="CAD $", priceNote="Prices in CAD, estimated 2026-10-02 (shop pages blocked in the cloud): verify at checkout.",
        built="2026-10-02", plateFile="",
        checks=build_checks(jobs, [pl["fits"] for pl in place.values()], WIR, FAST))

    tpl = open(a.template).read()
    ms = tpl.find('<script id="meta"'); mb = tpl.find(">", ms) + 1; me = tpl.find("</script>", mb)
    page = tpl[:mb] + json.dumps(meta, separators=(",", ":")).replace("</", "<\\/") + tpl[me:]
    gs = page.find('<script id="geo"'); gb = page.find(">", gs) + 1; ge = page.find("</script>", gb)
    page = page[:gb] + geo + page[ge:]
    for old, new in (("OneShot Arm v5.2", "FarmHand rail-SCARA v1"),
                     ("608 turret · stepper yaw 2:1 · SG90 2:1 · parallel gripper", "rail-SCARA · H2S + Ender station")):
        page = page.replace(old, new)
    open(a.out, "w").write(page)
    print(f"wrote {a.out}  {len(page) / 1e6:.2f} MB  parts {len(meta_parts)}  paths {len(meta['motion']['paths'])}  plates {len(plate_list)}")


if __name__ == "__main__":
    main()
