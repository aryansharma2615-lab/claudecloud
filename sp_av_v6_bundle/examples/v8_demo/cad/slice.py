#!/usr/bin/env python3
"""Slice every printed part for REAL grams + minutes (source label SLICER).

    python3 cad/slice.py   -> out/gcode/<part>.gcode, out/slicer_facts.json, out/ender3s1pro_petg.ini,
                              out/coupon/hole_coupon.gcode (run cad/hole_coupon.py first)

PrusaSlicer 2.7 CLI with the stock Creality bundle flattened: printer "Creality Ender-3 S1 Pro
(0.4 mm nozzle)", print "0.20 mm NORMAL (0.4 mm nozzle) @CREALITY", filament "Generic PETG @CREALITY",
then the per-part walls / top-bottom / infill from the engineering data. Creality Print on the
Mac will read a few % different — the AV labels these numbers "SLICER · PrusaSlicer 2.7".
"""
import configparser
import json
import os
import re
import subprocess
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "out")
BUNDLE = "/usr/share/PrusaSlicer/profiles/Creality.ini"
PRINTER = "Creality Ender-3 S1 Pro (0.4 mm nozzle)"
PRINT = "0.20 mm NORMAL (0.4 mm nozzle) @CREALITY"
FILAMENT = "Generic PETG @CREALITY"
ROT = {"base": None, "cradle": None, "arm": ("--rotate-x", "-90")}   # matches print.rot in the AV config


def flatten(cp, kind, name, seen=None):
    sec = f"{kind}:{name}"
    if sec not in cp:
        raise KeyError(sec)
    out = {}
    inh = cp[sec].get("inherits", "")
    for parent in [p.strip() for p in inh.split(";") if p.strip()]:
        out.update(flatten(cp, kind, parent))
    for k, v in cp[sec].items():
        if k != "inherits":
            out[k] = v
    return out


def main():
    data = yaml.safe_load(open(os.path.join(ROOT, "engineering_data_servo_mount_v1.yaml"), encoding="utf-8"))
    cp = configparser.ConfigParser(interpolation=None, strict=False)
    cp.optionxform = str
    cp.read(BUNDLE, encoding="utf-8")
    cfg = {}
    for kind, name in (("printer", PRINTER), ("print", PRINT), ("filament", FILAMENT)):
        cfg.update(flatten(cp, kind, name))
    for k in [k for k in cfg if k.startswith("compatible_") or k in ("renamed_from", "printer_model", "printer_variant")]:
        cfg.pop(k)
    os.makedirs(os.path.join(OUT, "gcode"), exist_ok=True)
    facts = {"slicer": "PrusaSlicer 2.7.2 CLI", "printer": PRINTER, "print": PRINT, "filament": FILAMENT, "parts": {}}
    for p in data["parts"]:
        if p["kind"] != "printed":
            continue
        pr = p["print"]
        c = dict(cfg)
        c["layer_height"] = str(pr["layer"]["v"])
        c["perimeters"] = str(pr["walls"]["v"])
        c["top_solid_layers"] = c["bottom_solid_layers"] = str(pr["top_bottom"]["v"])
        c["fill_density"] = f'{pr["infill"]["v"]}%'
        c["fill_pattern"] = pr["pattern"]["v"]
        c["support_material"] = "0"
        c["skirts"] = "0"                         # per-part numbers, no skirt in them
        ini = os.path.join(OUT, "gcode", p["id"] + ".ini")
        with open(ini, "w") as f:
            for k, v in c.items():
                f.write(f"{k} = {v}\n")
        if p["id"] == "cradle":
            import shutil
            shutil.copy(ini, os.path.join(OUT, "ender3s1pro_petg.ini"))
        gco = os.path.join(OUT, "gcode", p["id"] + ".gcode")
        cmd = ["prusa-slicer", "--export-gcode", "--load", ini, "--center", "110,110"]
        if ROT.get(p["id"]):
            cmd += list(ROT[p["id"]])
        cmd += [os.path.join(OUT, "stl", p["id"] + ".stl"), "-o", gco]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stdout[-2000:], r.stderr[-2000:])
            sys.exit(1)
        g = open(gco, encoding="utf-8", errors="ignore").read()
        grams = float(re.search(r"; (?:total )?filament used \[g\] = ([\d.]+)", g).group(1))
        mm = float(re.search(r"; filament used \[mm\] = ([\d.]+)", g).group(1))
        t = re.search(r"; estimated printing time \(normal mode\) = (.+)", g).group(1).strip()
        sec = 0
        for val, unit in re.findall(r"(\d+)([dhms])", t):
            sec += int(val) * {"d": 86400, "h": 3600, "m": 60, "s": 1}[unit]
        layers = len(re.findall(r"^;LAYER_CHANGE", g, re.M))
        facts["parts"][p["id"]] = {"grams": grams, "filament_mm": mm, "time_s": sec, "time_txt": t, "layers": layers,
                                   "settings": {"layer": pr["layer"]["v"], "walls": pr["walls"]["v"], "top_bottom": pr["top_bottom"]["v"],
                                                "infill": pr["infill"]["v"], "pattern": pr["pattern"]["v"]},
                                   "gcode": os.path.relpath(gco, ROOT)}
        print(f"{p['id']:8s} {grams:6.2f} g  {t:>10s}  {layers} layers")
    json.dump(facts, open(os.path.join(OUT, "slicer_facts.json"), "w"), indent=1)
    # the hole coupon (test print AV): flat, 3 walls, 100 % — every hole is solid wall, like the part's holes
    cst = os.path.join(OUT, "coupon", "hole_coupon.stl")
    if os.path.exists(cst):
        c = dict(cfg)
        c.update({"layer_height": "0.2", "perimeters": "3", "top_solid_layers": "5", "bottom_solid_layers": "5",
                  "fill_density": "100%", "fill_pattern": "rectilinear", "support_material": "0", "skirts": "0"})
        ini = os.path.join(OUT, "coupon", "hole_coupon.ini")
        with open(ini, "w") as f:
            for k, v in c.items():
                f.write(f"{k} = {v}\n")
        gco = os.path.join(OUT, "coupon", "hole_coupon.gcode")
        r = subprocess.run(["prusa-slicer", "--export-gcode", "--load", ini, "--center", "110,110", cst, "-o", gco],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stdout[-2000:], r.stderr[-2000:])
            sys.exit(1)
        print("coupon   sliced ->", os.path.relpath(gco, ROOT))


if __name__ == "__main__":
    main()
