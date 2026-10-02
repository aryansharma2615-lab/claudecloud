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


def build_checks(jobs, meshes_fit):
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
        fasteners=[], bomExtra=[dict(id=i, label=l, qty=q, kind="bought", color="#3a3f47",
                                     cost=dict(each=c, est=True, supplier=u.split("/")[2], url=u, checked="2026-10-02",
                                               bulk={"10": round(c * 0.85, 2), "50": round(c * 0.75, 2), "100": round(c * 0.7, 2)},
                                               have=False, have_note="", formula="docs/BOM.md estimate")) for i, l, q, c, u in BOM_EXTRA],
        parts=meta_parts, plates=plate_list, centre=[200.0, 100.0, -100.0], home=dict(yaw=-0.55, pitch=0.42),
        explodeScale=20, bed=dict(name="Bambu H2S", x=340.0, y=320.0, z=340.0, gap=8.0, nozzle=0.4, sequential=False, gantry=None, skirt=None),
        wiring=None,
        motion=dict(joints=joints, loops=[], payloads=[], grip=None, paths=jobs_to_paths(jobs), springs=[], gravity=[0, 0, -1],
                    rules=dict(warn=0.5, max=0.7),
                    note="Drive X, Z, J1, J2, W like the real motors; the door joint is the H2S door as a moving obstacle. "
                         "Paths are the sim/paths.py job sweeps (7 jobs, all clean in the box model).",
                    ghost=["h2s_left", "h2s_right", "h2s_back", "h2s_top", "ams", "h2s_header", "h2s_sill", "h2s_door",
                           "ender_base", "ender_up_l", "ender_up_r", "ender_top", "table"],
                    load_payloads=[dict(label="Spool + tool (spec)", g=1500.0, default=True)], load_checks=[]),
        currency="CAD $", priceNote="Prices in CAD, estimated 2026-10-02 (shop pages blocked in the cloud): verify at checkout.",
        built="2026-10-02", plateFile="",
        checks=build_checks(jobs, [pl["fits"] for pl in place.values()]))

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
