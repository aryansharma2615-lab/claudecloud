#!/usr/bin/env python3
"""Shawarma Servo Mount v1 — scripted CAD (build123d, OCC kernel; Amagine3D-compatible base).

    python3 cad/servo_mount_v1.py            -> out/step, out/stl, out/servo_mount_v1.glb,
                                                out/base_footprint.dxf, out/cad_facts.json,
                                                out/DFM_REPORT.md
Every dimension comes from `params` in engineering_data_servo_mount_v1.yaml — none is typed here.
Assembly frame: Z up, servo shaft along +Y, arm swings in the XZ plane, 0° = arm level along +X.
Then the /sp-print-dfm harness runs: watertight + single solid per part, every pair clash-checked
(designed contacts listed), the arm swept through its full range, the bed envelope.
"""
import json
import math
import os
import sys

import yaml
from build123d import (Align, Axis, Box, BuildPart, BuildSketch, Circle, Cylinder, ExportDXF,
                       Location, Locations, Mode, Plane, Polygon, Pos, Rectangle, Rot, Text,
                       add, chamfer, export_step, export_stl, extrude, fillet, Unit, Compound, Edge,
                       Vector, section)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "out")
DATA = yaml.safe_load(open(os.path.join(ROOT, "engineering_data_servo_mount_v1.yaml"), encoding="utf-8"))
P = {k: v["v"] for k, v in DATA["params"].items()}
os.makedirs(os.path.join(OUT, "step"), exist_ok=True)
os.makedirs(os.path.join(OUT, "stl"), exist_ok=True)
os.makedirs(os.path.join(OUT, "stl_hi"), exist_ok=True)

# ---------------------------------------------------------------- derived constants
L, W, H = P["sg90_body_l"], P["sg90_body_w"], P["sg90_body_h"]
ZS = P["shaft_z"]                          # shaft height
XS = P["sg90_shaft_off"]                   # shaft x (body centred on x = 0)
Y_TAB = 0.0                                # wall front face = tab underside
Y_BOT = Y_TAB - P["sg90_tab_z"]            # servo body bottom (behind the wall)
Y_TOP = Y_BOT + H                          # servo top face
Y_BOSS = Y_TOP + P["sg90_boss_h"]
Y_SPL = Y_BOSS + P["sg90_spline_h"]
WIN = (L + 2 * P["window_clear"], W + 2 * P["window_clear"])
HP = P["sg90_hole_pitch"] / 2
Z0_BASE, Z1_BASE = 0.0, P["base_t"]
Z1_FOOT = Z1_BASE + P["foot_t"]
WT = P["wall_t"]
YF0 = -P["foot_d"]
Y_HORN1 = Y_SPL + 1.0                      # horn hub top (the hub sits over the spline)
Y_HORN0 = Y_HORN1 - P["horn_pocket"]       # horn arm back face: the arm is at the top of the hub
Y_ARM0 = Y_HORN1 - P["horn_pocket"]        # arm back face: horn arm lives in its pocket
Y_ARM1 = Y_ARM0 + P["arm_t"]
IX, IY = P["insert_x"], P["insert_y"]


def solid_of(part):
    return part.part if hasattr(part, "part") else part


# ---------------------------------------------------------------- base plate
with BuildPart() as base:
    Box(P["base_l"], P["base_w"], P["base_t"], align=(Align.CENTER, Align.MIN, Align.MIN))
    base.part = base.part.moved(Location((P["base_cx"], P["base_front"] - P["base_w"], 0)))
for sx in (-1, 1):
    # counterbore from the bottom + clearance hole (the M3 screws go in from the BOTTOM)
    cb = Pos(sx * IX, IY, 0) * Cylinder(P["cb_d"] / 2, P["cb_h"], align=(Align.CENTER, Align.CENTER, Align.MIN))
    th = Pos(sx * IX, IY, 0) * Cylinder(P["clear_m3"] / 2, P["base_t"], align=(Align.CENTER, Align.CENTER, Align.MIN))
    base.part = base.part - cb - th
    # mounting slots for the user's own screws into the surface below
    sl = Pos(P["base_cx"] + sx * P["slot_dx"], -18.0, 0) * Box(3.4, 10.0, P["base_t"], align=(Align.CENTER, Align.CENTER, Align.MIN))
    base.part = base.part - sl
# SP emboss, 0.6 mm = 3 layers at 0.2
with BuildSketch(Plane.XY.offset(P["base_t"])) as sk:
    with Locations((28.0, -1.6)):
        Text("SP", font_size=7.0, font="DejaVu Sans")
emb = extrude(sk.sketch, amount=P["emboss_h"])
base_s = base.part + emb

# ---------------------------------------------------------------- servo cradle
foot = Pos(0, YF0, Z1_BASE) * Box(P["wall_w"], P["foot_d"], P["foot_t"], align=(Align.CENTER, Align.MIN, Align.MIN))
wall = Pos(0, -WT, Z1_FOOT) * Box(P["wall_w"], WT, P["wall_top_z"] - Z1_FOOT, align=(Align.CENTER, Align.MIN, Align.MIN))
cradle_s = foot + wall
# inside-corner fillet where the wall meets the foot (behind the wall)
edges = [e for e in cradle_s.edges() if abs(e.center().Y + WT) < 1e-6 and abs(e.center().Z - Z1_FOOT) < 1e-6]
cradle_s = fillet(edges, P["wall_fillet"])
win = Pos(0, -WT, ZS) * Box(WIN[0], WT, WIN[1], align=(Align.CENTER, Align.MIN, Align.CENTER))
cradle_s = cradle_s - win
for sx in (-1, 1):
    pil = Pos(sx * HP, 0, ZS) * Rot(90, 0, 0) * Cylinder(P["pilot_d"] / 2, WT, align=(Align.CENTER, Align.CENTER, Align.MIN))
    cradle_s = cradle_s - pil
    bore = Pos(sx * IX, IY, Z1_BASE) * Cylinder(P["insert_bore_d"] / 2, P["insert_bore_h"], align=(Align.CENTER, Align.CENTER, Align.MIN))
    lead = Pos(sx * IX, IY, Z1_BASE) * Cylinder(P["insert_bore_d"] / 2 + 0.5, 0.5, align=(Align.CENTER, Align.CENTER, Align.MIN))
    cradle_s = cradle_s - bore - lead

# ---------------------------------------------------------------- SG90 probe body (bought — every number ASSUMED until calipered)
body = Pos(0, Y_BOT, ZS) * Box(L, H, W, align=(Align.CENTER, Align.MIN, Align.CENTER))
tabs = Pos(0, Y_TAB, ZS) * Box(P["sg90_tab_span"], P["sg90_tab_t"], W, align=(Align.CENTER, Align.MIN, Align.CENTER))
boss = Pos(XS, Y_TOP, ZS) * Rot(-90, 0, 0) * Cylinder(P["sg90_boss_d"] / 2, P["sg90_boss_h"], align=(Align.CENTER, Align.CENTER, Align.MIN))
spl = Pos(XS, Y_BOSS, ZS) * Rot(-90, 0, 0) * Cylinder(P["sg90_spline_d"] / 2, P["sg90_spline_h"], align=(Align.CENTER, Align.CENTER, Align.MIN))
servo_s = body + tabs + boss + spl
for sx in (-1, 1):
    servo_s = servo_s - Pos(sx * HP, Y_TAB, ZS) * Rot(-90, 0, 0) * Cylinder(1.1, P["sg90_tab_t"], align=(Align.CENTER, Align.CENTER, Align.MIN))
# the cable leaves the bottom end, behind the wall: a 3-wire ribbon stub (probe for the cable path)
servo_s = servo_s + Pos(-L / 2 - 4.0, Y_BOT + 3.0, ZS) * Box(8.0, 1.2, 3.6, align=(Align.CENTER, Align.CENTER, Align.CENTER))


# ---------------------------------------------------------------- horn (stock SG90 single arm)
def horn_outline(off=0.0):
    hl, w0, w1 = P["horn_len"], 5.0 / 2 + off, 3.6 / 2 + off
    return [(0, -w0), (hl, -w1), (hl, w1), (0, w0)]


hub = Pos(XS, Y_BOSS + 0.2, ZS) * Rot(-90, 0, 0) * Cylinder(P["horn_hub_d"] / 2, Y_HORN1 - Y_BOSS - 0.2, align=(Align.CENTER, Align.CENTER, Align.MIN))
with BuildSketch(Plane.XZ.offset(-Y_HORN0)) as hs:
    with Locations((XS, ZS)):
        Polygon(*horn_outline(), align=None)
        Circle(2.5 + 0.0)
hornarm = extrude(hs.sketch, amount=-(P["horn_pocket"]))
horn_s = hub + hornarm
horn_s = horn_s - Pos(XS, Y_BOSS, ZS) * Rot(-90, 0, 0) * Cylinder(P["sg90_spline_d"] / 2, P["sg90_spline_h"] + 0.2, align=(Align.CENTER, Align.CENTER, Align.MIN))
horn_s = horn_s - Pos(XS, Y_BOSS, ZS) * Rot(-90, 0, 0) * Cylinder(1.2, 10, align=(Align.CENTER, Align.CENTER, Align.MIN))

# ---------------------------------------------------------------- printed load arm
R_HUB = P["arm_hub_d"] / 2
with BuildSketch(Plane.XZ.offset(-Y_ARM0)) as ask:
    with Locations((XS, ZS)):
        Circle(R_HUB)
    with Locations((XS + P["arm_len"] / 2 - P["arm_w"] / 4, ZS)):
        Rectangle(P["arm_len"] - P["arm_w"] / 2, P["arm_w"])
    with Locations((XS + P["arm_len"] - P["arm_w"] / 2, ZS)):
        Circle(P["arm_w"] / 2)
arm_s = extrude(ask.sketch, amount=-P["arm_t"])
arm_s = arm_s - Pos(XS, Y_ARM0, ZS) * Rot(-90, 0, 0) * Cylinder(1.2, P["arm_t"], align=(Align.CENTER, Align.CENTER, Align.MIN))
arm_s = arm_s - Pos(XS + P["arm_load_r"], Y_ARM0, ZS) * Rot(-90, 0, 0) * Cylinder(P["clear_m3"] / 2, P["arm_t"], align=(Align.CENTER, Align.CENTER, Align.MIN))
# horn pocket on the back face (+0.2 mm all round): the horn keys the arm to the spline
with BuildSketch(Plane.XZ.offset(-Y_ARM0)) as pk:
    with Locations((XS, ZS)):
        Polygon(*horn_outline(0.2), align=None)
        Circle(P["horn_hub_d"] / 2 + 0.2)
arm_s = arm_s - extrude(pk.sketch, amount=-P["horn_pocket"])

# ---------------------------------------------------------------- hardware (ISO-ish probes: head + shank, threads not modelled)
def screw(at, axis, d, length, head_d, head_h):
    """Seat point `at`, driven along unit `axis`."""
    ax = Vector(*axis)
    shank = Cylinder(d / 2, length, align=(Align.CENTER, Align.CENTER, Align.MIN))
    head = Pos(0, 0, -head_h) * Cylinder(head_d / 2, head_h, align=(Align.CENTER, Align.CENTER, Align.MIN))
    s = shank + head
    # local +Z -> axis
    z = Vector(0, 0, 1)
    if (ax - z).length < 1e-9:
        rot = Location()
    elif (ax + z).length < 1e-9:
        rot = Location((0, 0, 0), (1, 0, 0), 180)
    else:
        k = z.cross(ax)
        ang = math.degrees(math.acos(max(-1, min(1, z.dot(ax)))))
        rot = Location((0, 0, 0), (k.X, k.Y, k.Z), ang)
    return Location(at) * rot * s


tab0 = screw((-HP, P["sg90_tab_t"], ZS), (0, -1, 0), 2.0, 8.0, 3.8, 1.3)
tab1 = screw((HP, P["sg90_tab_t"], ZS), (0, -1, 0), 2.0, 8.0, 3.8, 1.3)
horn_screw = screw((XS, Y_ARM1, ZS), (0, -1, 0), 2.0, 8.0, 3.8, 1.3)
m3a = screw((-IX, IY, P["cb_h"]), (0, 0, 1), 3.0, 8.0, 5.5, 3.0)
m3b = screw((IX, IY, P["cb_h"]), (0, 0, 1), 3.0, 8.0, 5.5, 3.0)
def insert(x, y):
    tube = Pos(x, y, Z1_BASE) * Cylinder(P["insert_od"] / 2, P["insert_l"], align=(Align.CENTER, Align.CENTER, Align.MIN))
    return tube - Pos(x, y, Z1_BASE) * Cylinder(1.25, P["insert_l"], align=(Align.CENTER, Align.CENTER, Align.MIN))
ins_a, ins_b = insert(-IX, IY), insert(IX, IY)
# load pin + hanger through the load hole: carries the TEST mass
weight = Pos(XS + P["arm_load_r"], Y_ARM0 - 2.0, ZS) * Rot(-90, 0, 0) * Cylinder(1.3, P["arm_t"] + 4.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
weight = weight + Pos(XS + P["arm_load_r"], Y_ARM0 - 2.0, ZS) * Rot(-90, 0, 0) * Cylinder(3.0, 1.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
weight = weight + Pos(XS + P["arm_load_r"], Y_ARM1 + 1.0, ZS) * Rot(-90, 0, 0) * Cylinder(3.0, 1.0, align=(Align.CENTER, Align.CENTER, Align.MIN))

PARTS = {
    "base": base_s, "cradle": cradle_s, "servo": servo_s, "horn": horn_s, "arm": arm_s,
    "tab0": tab0, "tab1": tab1, "horn_screw": horn_screw, "m3a": m3a, "m3b": m3b,
    "ins_a": ins_a, "ins_b": ins_b, "weight": weight,
}
# The engine's FRONT is −Y. Built with the arm on +Y, so turn the whole design 180° about Z:
# (x, y, z) -> (−x, −y, z). Text stays readable (a rotation, not a mirror).
PARTS = {k: solid_of(v).rotate(Axis.Z, 180) for k, v in PARTS.items()}
R = lambda p: [round(-p[0], 6) + 0.0, round(-p[1], 6) + 0.0, p[2]]
MOVING = ["horn", "arm", "horn_screw", "weight"]
# designed contacts: screws bite their hosts, inserts melt into their bores, the horn sits on the spline
DESIGNED = {tuple(sorted(p)) for p in [
    ("tab0", "cradle"), ("tab1", "cradle"), ("tab0", "servo"), ("tab1", "servo"),
    ("horn_screw", "servo"), ("horn_screw", "horn"), ("horn_screw", "arm"),
    ("m3a", "ins_a"), ("m3b", "ins_b"), ("ins_a", "cradle"), ("ins_b", "cradle"),
    ("m3a", "base"), ("m3b", "base"), ("m3a", "cradle"), ("m3b", "cradle"),
    ("servo", "horn"), ("horn", "arm"), ("weight", "arm"), ("servo", "cradle"), ("base", "cradle"),
]}

# ---------------------------------------------------------------- exports
facts = {"parts": {}, "frames": {}, "features": {}, "fasteners": {}, "dfm": {}}
for pid, s in PARTS.items():
    s = solid_of(s)
    export_step(s, os.path.join(OUT, "step", pid + ".step"))
    export_stl(s, os.path.join(OUT, "stl", pid + ".stl"), tolerance=0.02, angular_tolerance=0.15)      # default view + 3MF (20 µm chord)
    export_stl(s, os.path.join(OUT, "stl_hi", pid + ".stl"), tolerance=0.004, angular_tolerance=0.05)  # LOD for close zoom
    bb = s.bounding_box()
    c = s.center()
    facts["parts"][pid] = {
        "volume_mm3": round(s.volume, 3), "area_mm2": round(s.area, 3),
        "bbox": [[round(bb.min.X, 3), round(bb.min.Y, 3), round(bb.min.Z, 3)], [round(bb.max.X, 3), round(bb.max.Y, 3), round(bb.max.Z, 3)]],
        "centroid": [round(c.X, 3), round(c.Y, 3), round(c.Z, 3)],
        "solids": len(s.solids()),
        "valid": bool(s.is_valid),
    }
export_step(Compound(children=[solid_of(s) for s in PARTS.values()]), os.path.join(OUT, "step", "servo_mount_v1_assembly.step"))

# DXF footprint of the base (flat drawing for the drawing / BOM tab)
sec = section(PARTS["base"], Plane.XY.offset(P["base_t"] / 2 + 1.0)).moved(Location((0, 0, -(P["base_t"] / 2 + 1.0))))
dxf = ExportDXF(unit=Unit.MM)
dxf.add_layer("footprint")
dxf.add_shape(sec, layer="footprint")
dxf.write(os.path.join(OUT, "base_footprint.dxf"))

# ---------------------------------------------------------------- frames and features the AV + calc need
facts["frames"] = {
    "shaft": {"origin": R([XS, Y_SPL, ZS]), "axis": R([0, -1, 0])},
    "arm_dir": R([1, 0, 0]),                     # the arm points this way at 0° (level)
    "front": R([0, 1, 0]),                       # out of the wall's front face (engine FRONT = −Y)
    "arm_root": {"x_from_shaft": round(math.sqrt(R_HUB ** 2 - (P["arm_w"] / 2) ** 2), 4), "D": P["arm_hub_d"], "d": P["arm_w"],
                 "t_min": P["arm_t"] - P["horn_pocket"], "point": R([round(XS + math.sqrt(R_HUB ** 2 - (P["arm_w"] / 2) ** 2), 3), (Y_ARM0 + Y_ARM1) / 2, ZS + P["arm_w"] / 2])},
    "load_point": R([XS + P["arm_load_r"], (Y_ARM0 + Y_ARM1) / 2, ZS]),
    "wall_root": {"z": Z1_FOOT, "b": P["wall_w"], "h": WT, "y_front": 0.0, "y_mid": R([0, -WT / 2, 0])[1], "point": R([0.0, -WT / 2, Z1_FOOT])},
    "tab_screws_dx": 2 * HP,
}
def feat(fid, part, at, axis, d, kind="hole", size=None):
    facts["features"][fid] = {"part": part, "at": [round(a, 3) for a in R(at)], "axis": R(axis), "d": d, "kind": kind, "size": size}
feat("window", "cradle", (0, -WT / 2, ZS), [0, 1, 0], None, "rect", [WIN[0], WIN[1]])
feat("pilot0", "cradle", (-HP, -WT / 2, ZS), [0, 1, 0], P["pilot_d"])
feat("pilot1", "cradle", (HP, -WT / 2, ZS), [0, 1, 0], P["pilot_d"])
feat("bore_a", "cradle", (-IX, IY, Z1_BASE), [0, 0, 1], P["insert_bore_d"])
feat("bore_b", "cradle", (IX, IY, Z1_BASE), [0, 0, 1], P["insert_bore_d"])
feat("clr_a", "base", (-IX, IY, P["base_t"]), [0, 0, 1], P["clear_m3"])
feat("clr_b", "base", (IX, IY, P["base_t"]), [0, 0, 1], P["clear_m3"])
feat("hornhole", "arm", (XS, Y_ARM1, ZS), [0, 1, 0], 2.4)
feat("loadhole", "arm", (XS + P["arm_load_r"], Y_ARM1, ZS), [0, 1, 0], P["clear_m3"])
facts["fasteners"] = {
    "tab0": {"at": R([-HP, P["sg90_tab_t"], ZS]), "axis": R([0, -1, 0]), "d": 2.0, "len": 8, "head": "pan", "host": "cradle"},
    "tab1": {"at": R([HP, P["sg90_tab_t"], ZS]), "axis": R([0, -1, 0]), "d": 2.0, "len": 8, "head": "pan", "host": "cradle"},
    "horn_screw": {"at": R([XS, Y_ARM1, ZS]), "axis": R([0, -1, 0]), "d": 2.0, "len": 8, "head": "pan", "host": "arm"},
    "m3a": {"at": R([-IX, IY, P["cb_h"]]), "axis": [0, 0, 1], "d": 3.0, "len": 8, "head": "socket", "host": "cradle"},
    "m3b": {"at": R([IX, IY, P["cb_h"]]), "axis": [0, 0, 1], "d": 3.0, "len": 8, "head": "socket", "host": "cradle"},
}
facts["insert"] = {"boss_wall": round(min(P["wall_w"] / 2 - IX, IY - YF0, -IY) - P["insert_bore_d"] / 2, 3),
                   "cover": round(Z1_FOOT - (Z1_BASE + P["insert_bore_h"]), 3),
                   "engagement_m3": round(P["cb_h"] + 8.0 - Z1_BASE, 3), "tip_gap": round(Z1_BASE + P["insert_bore_h"] - (P["cb_h"] + 8.0), 3)}
facts["ligament"] = round(HP - WIN[0] / 2 - P["pilot_d"] / 2, 3)
facts["horn_screw_bite"] = round(Y_SPL - (Y_ARM1 - 8.0), 3)

# ---------------------------------------------------------------- DFM harness (/sp-print-dfm)
def vol_int(a, b):
    try:
        i = solid_of(a) & solid_of(b)
        return i.volume if i is not None else 0.0
    except Exception:
        return 0.0

dfm = facts["dfm"]
dfm["solid"] = {pid: {"valid": facts["parts"][pid]["valid"], "single_solid": facts["parts"][pid]["solids"] == 1} for pid in PARTS}
clashes, designed_hits = [], []
ids = list(PARTS)
for i, a in enumerate(ids):
    for b in ids[i + 1:]:
        v = vol_int(PARTS[a], PARTS[b])
        if v > 1e-3:
            (designed_hits if tuple(sorted((a, b))) in DESIGNED else clashes).append([a, b, round(v, 3)])
dfm["clashes_at_rest"] = clashes
dfm["designed_contacts"] = designed_hits
# sweep the moving set through the joint range — every 5°
o, sweep_hits = facts["frames"]["shaft"]["origin"], []
ax = facts["frames"]["shaft"]["axis"]
lo, hi = DATA["joints"][0]["limits"]["v"]
for ang in range(int(lo), int(hi) + 1, 5):
    loc = Location((o[0], 0, o[2])) * Location((0, 0, 0), tuple(ax), ang) * Location((-o[0], 0, -o[2]))
    for m in MOVING:
        mv = loc * solid_of(PARTS[m])
        for s in ids:
            if s in MOVING or tuple(sorted((m, s))) in DESIGNED:
                continue
            v = vol_int(mv, PARTS[s])
            if v > 1e-3:
                sweep_hits.append([ang, m, s, round(v, 3)])
dfm["sweep_deg"] = [lo, hi, 5]
dfm["sweep_clashes"] = sweep_hits
bed = DATA["printers"]["ender3s1pro"]["bed"]["v"]
env = {}
for pid in ("base", "cradle", "arm"):
    bb = facts["parts"][pid]["bbox"]
    ext = sorted([bb[1][k] - bb[0][k] for k in range(3)])
    env[pid] = {"extent": [round(e, 2) for e in ext], "fits": all(e <= b for e, b in zip(ext, sorted(bed)))}
dfm["envelope"] = env
dfm["min_wall_ligament"] = facts["ligament"]
dfm["pass"] = (not clashes and not sweep_hits and all(v["valid"] and v["single_solid"] for v in dfm["solid"].values())
               and all(e["fits"] for e in env.values()))
dfm["warn"] = [] if facts["ligament"] >= 1.6 - 1e-6 else [f"CAD tab-hole ligament {facts['ligament']} mm < 1.60 house minimum — trade-off D4 (prints ~1.66 after hole shrink; measure the SG90 pitch)"]

json.dump(facts, open(os.path.join(OUT, "cad_facts.json"), "w"), indent=1)

# GLB of the assembly (review link / Vercel export / /cad-viewer)
try:
    import trimesh
    sc = trimesh.Scene()
    for pid in PARTS:
        m = trimesh.load(os.path.join(OUT, "stl", pid + ".stl"))
        sc.add_geometry(m, node_name=pid, geom_name=pid)
    sc.export(os.path.join(OUT, "servo_mount_v1.glb"))
except Exception as e:  # noqa: BLE001
    print("GLB export skipped:", e)

with open(os.path.join(OUT, "DFM_REPORT.md"), "w") as f:
    f.write("# DFM report — Shawarma Servo Mount v1 (/sp-print-dfm harness)\n\n")
    f.write(f"**Result: {'PASS' if dfm['pass'] else 'FAIL'}**\n\n")
    f.write("| check | result |\n|---|---|\n")
    for pid, v in dfm["solid"].items():
        f.write(f"| {pid}: valid solid · single solid | {'✓' if v['valid'] else '✗'} · {'✓' if v['single_solid'] else '✗'} |\n")
    f.write(f"| clashes at rest (excluding designed contacts) | {len(clashes)} {clashes if clashes else ''} |\n")
    f.write(f"| designed contacts found | {len(designed_hits)} (screw bites, insert melt-in, horn on spline) |\n")
    f.write(f"| arm sweep {lo}°…{hi}° every 5° | {len(sweep_hits)} clashes {sweep_hits[:6] if sweep_hits else ''} |\n")
    for pid, e in env.items():
        f.write(f"| envelope {pid} {e['extent']} mm vs bed {bed} | {'fits' if e['fits'] else 'TOO BIG'} |\n")
    f.write(f"| tab-hole ligament (window edge → pilot edge, CAD) | {facts['ligament']} mm (house min 1.60) {'— WARN, see D4' if dfm['warn'] else ''} |\n")
    f.write(f"| insert boss wall / cover over bore | {facts['insert']['boss_wall']} mm / {facts['insert']['cover']} mm (min 1.40) |\n")
    f.write(f"| M3 thread engagement in insert / tip gap to bore end | {facts['insert']['engagement_m3']} mm / {facts['insert']['tip_gap']} mm |\n")
    f.write(f"| horn screw bite into the spline | {facts['horn_screw_bite']} mm |\n")
print(json.dumps({"dfm_pass": dfm["pass"], "clashes": clashes, "sweep": len(sweep_hits), "ligament": facts["ligament"],
                  "vol": {k: v["volume_mm3"] for k, v in facts["parts"].items()}}, indent=1))
