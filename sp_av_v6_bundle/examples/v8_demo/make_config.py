#!/usr/bin/env python3
"""Config generator for the Shawarma Servo Mount v1 AV — every position from the CAD facts, every
mass from the slicer / datasheet, never typed twice.

    python3 make_config.py        -> av_config_v8.json (+ coupon/av_config_coupon.json)
    python3 ../../engine/build_av_v8.py av_config_v8.json servo_mount_v8.html
"""
import json
import os
import re
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "engine"))
import calc_v8  # noqa: E402

DATA = yaml.safe_load(open(os.path.join(HERE, "engineering_data_servo_mount_v1.yaml"), encoding="utf-8"))
CAD = json.load(open(os.path.join(HERE, "out", "cad_facts.json")))
SL = json.load(open(os.path.join(HERE, "out", "slicer_facts.json")))
ENG, M = calc_v8.compute(os.path.join(HERE, "engineering_data_servo_mount_v1.yaml"))
P = {k: v["v"] for k, v in DATA["params"].items()}
YD = {p["id"]: p for p in DATA["parts"]}
FD = {f["id"]: f for f in DATA["fasteners"]}

SCREW_LINK = "https://www.amazon.ca/s?k=m3+socket+head+screw+assortment+kit"
M2_LINK = "https://www.amazon.ca/s?k=m2+self+tapping+screw+assortment"
INS_LINK = "https://www.amazon.ca/s?k=ruthex+m3+heat+set+inserts"


def mass(pid):
    mp = M.parts[pid]
    return {"g": round(mp["g"], 3), "com": [round(c, 3) for c in M.com_of(pid, ENG["model"]["lever"]["v"])], "how": f"{mp['src']} · {mp['how']}"}


def printed(pid, color, step, explode, insert, rot, note):
    y = YD[pid]
    pr, sp = y["print"], SL["parts"][pid]
    return {"id": pid, "label": y["name"], "color": color, "group": "printed", "step": step, "kind": "printed",
            "material": "PETG", "explode": explode, "insert": insert, "stl": f"out/stl/{pid}.stl", "stl_hi": f"out/stl_hi/{pid}.stl",
            "mass": mass(pid), "note": note,
            "print": {"rot": rot, "layer": pr["layer"]["v"], "walls": pr["walls"]["v"], "infill": pr["infill"]["v"],
                      "support": pr["supports"]["v"], "orientation": f"{pr['orientation']['v'].capitalize()}: {pr['orientation']['why']}",
                      "grams": sp["grams"], "time_min": round(sp["time_s"] / 60), "slicer": SL["slicer"] + " · Ender-3 S1 Pro profile"}}


def screw_part(pid, label, step, d, length, head, host, color="#9aa0a6", cost=None, finish="steel"):
    f = CAD["fasteners"][pid]
    side = FD[pid]["side"]
    return {"id": pid, "label": label, "color": color, "group": "hw", "step": step, "kind": "screw", "finish": finish,
            "explode": [0, 0, 0], "stl": f"out/stl/{pid}.stl", "stl_hi": f"out/stl_hi/{pid}.stl", "mass": mass(pid),
            "screw": {"fid": pid, "role": "screw", "axis": f["axis"], "at": f["at"], "d": d, "len": length, "head": head,
                      "side": side, "host": host, "gid": FD[pid]["spec"], "spec": FD[pid]["spec"], "into": [FD[pid]["into"]]},
            "cost": cost}


def main():
    sh = CAD["frames"]["shaft"]
    pk = lambda c, n, url, sup, bulk, est=True, formula="": {"each": c, "url": url, "supplier": sup, "bulk": bulk, "est": est,
                                                             "checked": "2026-10-03", "have": True, "have_note": n, "formula": formula}
    parts = [
        printed("cradle", "#3a3d42", 1, [0, 0, 0], None, [0, 0, 0], "Foot down on the bed. The wall root is the part's weak axis (Z) — checked."),
        {"id": "ins_a", "label": "M3×5.7 heat-set insert", "color": "#c9a227", "group": "hw", "step": 2, "kind": "bought", "finish": "brass",
         "explode": [0, 0, -0.5], "insert": {"dir": [0, 0, -1], "dist": 22}, "stl": "out/stl/ins_a.stl", "stl_hi": "out/stl_hi/ins_a.stl",
         "mass": mass("ins_a"), "cost": pk(0.12, "SP insert stock (M2–M5)", INS_LINK, "Amazon.ca (ruthex RX-M3×5.7)", {"10": 0.12, "50": 0.10, "100": 0.09},
                                           formula="ruthex 100-pack ÷ 100")},
        {"id": "ins_b", "label": "M3×5.7 heat-set insert", "color": "#c9a227", "group": "hw", "step": 2, "kind": "bought", "finish": "brass",
         "explode": [0, 0, -0.5], "insert": {"dir": [0, 0, -1], "dist": 22}, "stl": "out/stl/ins_b.stl", "stl_hi": "out/stl_hi/ins_b.stl",
         "mass": mass("ins_b"), "cost": pk(0.12, "SP insert stock (M2–M5)", INS_LINK, "Amazon.ca (ruthex RX-M3×5.7)", {"10": 0.12, "50": 0.10, "100": 0.09},
                                           formula="ruthex 100-pack ÷ 100")},
        printed("base", "#1d1f22", 3, [0, 0, -0.6], {"dir": [0, 0, -1], "dist": 30}, [0, 0, 0], "Bottom down. 0.6 mm SP emboss = 3 layers at 0.2."),
        screw_part("m3a", "M3×8 socket head", 4, 3.0, 8, "socket", "cradle",
                   cost=pk(0.05, "SP screw box", SCREW_LINK, "Amazon.ca (M3 kit)", {"10": 0.05, "50": 0.04, "100": 0.03}, formula="kit ÷ count")),
        screw_part("m3b", "M3×8 socket head", 4, 3.0, 8, "socket", "cradle",
                   cost=pk(0.05, "SP screw box", SCREW_LINK, "Amazon.ca (M3 kit)", {"10": 0.05, "50": 0.04, "100": 0.03}, formula="kit ÷ count")),
        {"id": "servo", "label": "SG90 micro servo", "color": "#2b4c7e", "group": "drive", "step": 5, "kind": "bought", "finish": "plastic",
         "explode": [0, -0.5, 0], "insert": {"dir": [0, -1, 0], "dist": 36}, "stl": "out/stl/servo.stl", "stl_hi": "out/stl_hi/servo.stl",
         "mass": mass("servo"), "note": "Probe body from ASSUMED dims — caliper yours (MEASURE_ME #4).",
         "cost": pk(4.49, "one of your 6 SG90s", "https://www.canadarobotix.com/products/1713", "Canada Robotix", {"10": 2.4, "50": 2.1, "100": 1.9},
                    est=False, formula="$4.49 single (listed). Bulk = 10-packs, estimated.")},
        screw_part("tab0", "M2×8 self-tapper", 6, 2.0, 8, "pan", "cradle",
                   cost=pk(0.0, "servo bag", None, "in the servo bag", {"10": 0.04, "50": 0.03, "100": 0.02}, formula="ships with each SG90")),
        screw_part("tab1", "M2×8 self-tapper", 6, 2.0, 8, "pan", "cradle",
                   cost=pk(0.0, "servo bag", None, "in the servo bag", {"10": 0.04, "50": 0.03, "100": 0.02}, formula="ships with each SG90")),
        {"id": "horn", "label": "SG90 single horn", "color": "#e8e6e0", "group": "drive", "step": 7, "kind": "bought", "finish": "plastic",
         "explode": [0, -0.8, 0], "insert": {"dir": [0, -1, 0], "dist": 16}, "stl": "out/stl/horn.stl", "stl_hi": "out/stl_hi/horn.stl",
         "mass": mass("horn"), "cost": pk(0.0, "servo bag", None, "in the servo bag", {"10": 0, "50": 0, "100": 0}, est=False, formula="ships with each SG90")},
        printed("arm", "#26292d", 8, [0, -1.1, 0], {"dir": [0, -1, 0], "dist": 26}, [-90, 0, 0],
                "Flat, horn pocket up: bending runs in the layer plane (XY). Root step = the weak spot (what-breaks-first #1 after the servo)."),
        screw_part("horn_screw", "M2×8 horn screw", 9, 2.0, 8, "pan", "arm",
                   cost=pk(0.04, "SP screw box", M2_LINK, "Amazon.ca (M2 kit)", {"10": 0.04, "50": 0.03, "100": 0.02}, formula="kit ÷ count")),
        {"id": "weight", "label": "Load pin + test weight", "color": "#8a8f98", "group": "test", "step": 10, "kind": "bought", "finish": "steel",
         "explode": [0, -1.4, 0], "insert": {"dir": [0, -1, 0], "dist": 20}, "stl": "out/stl/weight.stl", "stl_hi": "out/stl_hi/weight.stl",
         "mass": mass("weight"), "bom": False, "note": "Mass follows the TEST slider (SPEC)."},
    ]
    for p in parts:
        if p.get("cost") is None:
            p.pop("cost", None)
    for p in parts:   # owned -> HAVE in the BOM, OWNED $0 for unit #1
        if p.get("cost"):
            p["cost"]["have"] = True
    fasteners = []
    for pid, step, tool, note in [("m3a", 4, "2.5 mm hex", "Up through the base into the insert — 0.6 N·m guide (ASSUMED)."),
                                  ("m3b", 4, "2.5 mm hex", "Up through the base into the insert — 0.6 N·m guide (ASSUMED)."),
                                  ("tab0", 6, "PH0", "Through the servo tab into the wall pilot — snug, do not strip (0.15 N·m guide, ASSUMED)."),
                                  ("tab1", 6, "PH0", "Through the servo tab into the wall pilot — snug, do not strip (0.15 N·m guide, ASSUMED)."),
                                  ("horn_screw", 9, "PH0", "Through the arm hub into the spline.")]:
        f = CAD["fasteners"][pid]
        fasteners.append({"id": pid, "label": FD[pid]["spec"].split()[0], "spec": FD[pid]["spec"], "qty": 1, "at": f["at"], "axis": f["axis"],
                          "part": f["host"], "screw": pid, "step": step, "gid": FD[pid]["spec"], "side": FD[pid]["side"], "tool": tool,
                          "head": f["head"], "note": note, "holds": FD[pid]["holds"]})
    steps = [
        {"n": 1, "title": "Cradle on the bench", "caption": "Foot up for the inserts.", "tool": "—", "time": "1 min"},
        {"n": 2, "title": "Heat-set inserts into the foot", "caption": "Iron 240 °C, straight in, let it cool.", "tool": "soldering iron + insert tip",
         "spec": "2× M3×5.7", "time": "4 min"},
        {"n": 3, "title": "Base plate under the cradle", "caption": "Counterbores face down.", "tool": "—", "time": "1 min"},
        {"n": 4, "title": "M3×8 up from the bottom", "caption": "Into the inserts. Snug.", "tool": "2.5 mm hex", "spec": "0.6 N·m guide · ASSUMED", "time": "2 min"},
        {"n": 5, "title": "SG90 into the window", "caption": "From the front, cable out the back.", "tool": "—", "time": "1 min"},
        {"n": 6, "title": "Tab screws", "caption": "From the front into the pilots.", "tool": "PH0", "spec": "2× M2×8 self-tapper", "time": "2 min"},
        {"n": 7, "title": "Horn onto the spline", "caption": "Centre the servo first (90°).", "tool": "—", "time": "1 min"},
        {"n": 8, "title": "Arm over the horn", "caption": "Horn sits in the pocket.", "tool": "—", "time": "1 min"},
        {"n": 9, "title": "Horn screw", "caption": "Through the arm into the spline.", "tool": "PH0", "spec": "M2×8", "time": "1 min"},
        {"n": 10, "title": "Load pin + test weight", "caption": "Hang it, run the TEST sweep.", "tool": "—", "time": "1 min"},
    ]
    lc = ENG["at_default"]
    motion = {
        "joints": [{"id": "shaft", "label": "SG90 → arm (servo)", "type": "revolute", "parent": None,
                    "parts": ["horn", "arm", "horn_screw", "weight"], "origin": sh["origin"], "axis": sh["axis"], "cad": 0.0, "home": 0.0,
                    "limits": [-90.0, 90.0], "eff": [-90.0, 90.0], "units": "deg",
                    "servo": {"model": "SG90", "channel": "D9", "center": 90.0, "direction": 1, "offset": 0, "range": [0, 180],
                              "stall_kgcm": DATA["actuators"]["sg90"]["stall_kgcm"]["v"], "kind": "servo",
                              "note": "SG90 1.8 kgf·cm @ 4.8 V (DATASHEET). 0° = arm level."},
                    "band": None, "couple": None, "drive": "servo", "touch": DATA["joints"][0]["touch"],
                    "note": "Drag the arm: it turns about the SG90 output. The TEST slider sets the hanging mass."}],
        "loops": [], "payloads": [], "grip": None, "springs": [], "gravity": [0, 0, -1],
        "paths": [{"id": "sweep", "label": DATA["path"]["label"], "speed_dps": DATA["path"]["speed_dps"], "settle_s": 0.2, "fps": 30,
                   "start": {"shaft": 0.0},
                   "keys": [{"label": "level", "q": {"shaft": 0.0}}, {"wait": 0.3}, {"label": "up +90°", "q": {"shaft": 90.0}}, {"wait": 0.3},
                            {"label": "down −90°", "q": {"shaft": -90.0}}, {"wait": 0.3}, {"label": "level", "q": {"shaft": 0.0}}],
                   "note": "Minimum-jerk between keys. Watch the Load bar peak where the arm is level."}],
        "rules": {"warn": DATA["targets"]["hold_frac"]["v"], "max": DATA["targets"]["dyn_frac"]["v"]},
        "ghost": [], "note": "One revolute joint at the SG90 output. Load = Σ r × F over the arm (engine) = calc_v8 = PyBullet.",
        "load_payloads": [], "load_checks": [
            {"label": f"arm level · {lc['kg']} kg at {lc['lever']} mm", "q": {"shaft": 0.0}, "payload_g": None,
             "expect": {"shaft": round(M.tau(lc["kg"], lc["lever"], 0) / calc_v8.KGCM, 4)}, "source": "calc_v8: τ = g·Σ m·x (PyBullet agrees 0.1 %)"},
            {"label": f"arm +60° · {lc['kg']} kg", "q": {"shaft": 60.0}, "payload_g": None,
             "expect": {"shaft": round(M.tau(lc["kg"], lc["lever"], 60) / calc_v8.KGCM, 4)}, "source": "calc_v8: τ(θ) = g·Σ m·(x cosθ − z sinθ)"}],
    }
    cfg = {"title": "Shawarma Servo Mount v1", "subtitle": "SG90 bracket · LOAD → FIT → SECURE → TEST", "slug": "servo_mount_v8",
           "project_dir": "~/Claude/AV/examples/v8_demo", "currency": "CAD $", "explode_scale": 50, "home": {"yaw": -0.86, "pitch": 0.40},
           "printer": {"name": "Creality Ender 3 S1 Pro", "x": 220, "y": 220, "z": 270, "nozzle": 0.4, "gap": 8, "margin": 5, "sequential": False},
           "materials": {"PETG": {"density": 1.27, "price": 25.0, "spool_g": 1000}},
           "machine_rate_per_h": 0.35,
           "groups": {"printed": "Printed (PETG)", "drive": "Servo + horn", "hw": "Hardware", "test": "Test load"},
           "steps": steps, "parts": parts, "fasteners": fasteners, "motion": motion, "eng": "engineering_data_servo_mount_v1.yaml"}
    json.dump(cfg, open(os.path.join(HERE, "av_config_v8.json"), "w"), indent=1)
    coupon()
    print("av_config_v8.json:", len(parts), "parts,", len(steps), "steps")


def coupon_gcode():
    """grams + minutes straight from the coupon's G-code (SLICER) — no number typed in; a missing file fails the build"""
    p = os.path.join(HERE, "out", "coupon", "hole_coupon.gcode")
    if not os.path.exists(p):
        sys.exit("make_config: out/coupon/hole_coupon.gcode missing — run cad/hole_coupon.py (slices the coupon) first")
    g = open(p, encoding="utf-8", errors="ignore").read()
    mg = re.search(r"; (?:total )?filament used \[g\] = ([\d.]+)", g)
    mt = re.search(r"; estimated printing time \(normal mode\) = (.+)", g)
    if not (mg and mt):
        sys.exit("make_config: hole_coupon.gcode has no PrusaSlicer grams/time footer")
    sec = sum(int(v) * {"d": 86400, "h": 3600, "m": 60, "s": 1}[u] for v, u in re.findall(r"(\d+)([dhms])", mt.group(1)))
    return {"grams": float(mg.group(1)), "time_min": round(sec / 60, 1)}


def coupon():
    """the hole-coupon test-print AV: its own config + a reduced eng block (FIT only)"""
    cf = json.load(open(os.path.join(HERE, "out", "coupon", "coupon_facts.json")))
    prof = json.load(open(os.path.join(HERE, "..", "..", "engine", "tolerance_profile_ender3s1pro.json")))
    fits = []
    for k, h in enumerate(cf["holes"]):
        printed, src = calc_v8.printed_size(prof, h["cad"])
        clr = printed - 3.0
        fits.append({"id": h["id"], "part": "coupon", "label": "hole " + "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[k], "kind": "hole", "at": h["at"], "axis": h["axis"],
                     "cad": {"v": h["cad"], "u": "mm", "src": "CAD"}, "printed": {"v": round(printed, 3), "u": "mm", "src": "CALC", "formula": f"cad + a + b/cad — profile {src}"},
                     "comp_src": src, "measured": {"v": None, "u": "mm", "src": "MEASURED"}, "mate": "M3 screw shank", "mate_size": {"v": 3.0, "u": "mm", "src": "DATASHEET"},
                     "clearance": {"v": round(clr, 3), "u": "mm", "src": "CALC"}, "purpose": "clearance", "band": calc_v8.band_of(prof, "clearance", clr), "d": h["cad"]})
    gc = coupon_gcode()
    eng = {"schema": "sp-eng-v8", "kind": "coupon", "assembly": {"id": "hole_coupon", "name": "Hole coupon Ø2.8–3.6", "version": 1, "printer": "ender3s1pro"},
           "sources": calc_v8.SRC_INFO, "missing": [], "phases": ["load", "fit"],
           "parts": {"coupon": {"name": "Hole coupon", "kind": "printed", "material": "PETG",
                                "mass": {"v": gc["grams"], "u": "g", "src": "SLICER", "note": "G-code filament used (PrusaSlicer 2.7.2 CLI)"},
                                "volume": {"v": cf["volume_mm3"], "u": "mm³", "src": "CAD"},
                                "slicer": {"grams": {"v": gc["grams"], "u": "g", "src": "SLICER"}, "time_min": {"v": gc["time_min"], "u": "min", "src": "SLICER"}}}},
           "fits": fits, "stackups": [], "checks": [], "ranking": [],
           "measure": [{"key": "coupon", "what": "caliper all 9 holes (two readings 90° apart, keep the smaller)", "tool": "calipers",
                        "unlocks": ["every FIT colour in every SP AV"], "n": 9}],
           "tolerance": {"profile": prof["printer"] + " · " + prof["material"], "src": prof["src"], "status": prof["status"], "bands": prof["bands"],
                         "colors": prof["colors"], "model": prof["model"], "rect": prof["rect"], "coupon": prof["coupon"], "why": prof["why"]}}
    os.makedirs(os.path.join(HERE, "coupon"), exist_ok=True)
    cfg = {"title": "Hole coupon · Ender 3 S1 Pro", "subtitle": "test print → tolerance_profile_ender3s1pro.json", "slug": "hole_coupon_v8",
           "currency": "CAD $", "explode_scale": 10, "home": {"yaw": -1.2, "pitch": 0.75}, "base_dir": "..",
           "printer": {"name": "Creality Ender 3 S1 Pro", "x": 220, "y": 220, "z": 270, "nozzle": 0.4, "gap": 8, "margin": 5, "sequential": False},
           "materials": {"PETG": {"density": 1.27, "price": 25.0, "spool_g": 1000}}, "machine_rate_per_h": 0.35, "groups": {"printed": "Printed"},
           "steps": [{"n": 1, "title": "Print flat, measure every hole", "caption": "Two readings 90° apart — keep the smaller.", "tool": "calipers", "time": f"{round(gc['time_min'])} min print"}],
           "parts": [{"id": "coupon", "label": "Hole coupon Ø2.8–3.6", "color": "#26292d", "group": "printed", "step": 1, "kind": "printed", "material": "PETG",
                      "explode": [0, 0, 0], "stl": "out/coupon/hole_coupon.stl",
                      "print": {"rot": [0, 0, 0], "layer": 0.2, "walls": 3, "infill": 100, "support": "none", "orientation": "Flat: hole axes vertical, like the part's holes.",
                                "grams": gc["grams"], "time_min": round(gc["time_min"])}}],
           "fasteners": [], "eng_json": eng}
    json.dump(cfg, open(os.path.join(HERE, "coupon", "av_config_coupon.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
