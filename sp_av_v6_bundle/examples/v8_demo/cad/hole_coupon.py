#!/usr/bin/env python3
"""Hole coupon — Ø2.8 … Ø3.6 in 0.1 mm steps, vertical holes, PETG on the Ender 3 S1 Pro.

    python3 cad/hole_coupon.py   -> out/coupon/hole_coupon.step/.stl, out/coupon/coupon_facts.json

Print it flat, 0.2 mm layers, same spool as the part. Caliper each hole twice (90° apart), keep the
smaller, write it into tolerance_profile_ender3s1pro.json -> coupon[].measured. Every FIT colour in
every SP AV then comes from that file. The labels are engraved 0.4 mm (2 layers) under each hole.
"""
import json
import os

from build123d import Align, Box, BuildSketch, Cylinder, Locations, Plane, Pos, Text, export_step, export_stl, extrude

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out", "coupon")
os.makedirs(OUT, exist_ok=True)
SIZES = [round(2.8 + 0.1 * i, 1) for i in range(9)]
PITCH, T, W = 8.0, 4.0, 18.0
L = PITCH * len(SIZES) + 4.0
plate = Box(L, W, T, align=(Align.CENTER, Align.CENTER, Align.MIN))
holes = []
for i, d in enumerate(SIZES):
    x = -L / 2 + 6.0 + i * PITCH
    plate = plate - Pos(x, 3.0, 0) * Cylinder(d / 2, T, align=(Align.CENTER, Align.CENTER, Align.MIN))
    holes.append({"id": f"h{int(round(d * 10))}", "cad": d, "at": [round(x, 3), 3.0, T], "axis": [0, 0, 1]})
with BuildSketch(Plane.XY.offset(T)) as sk:
    for h in holes:
        with Locations((h["at"][0], -4.5)):
            Text(str(int(round(h["cad"] * 10))), font_size=3.2)
plate = plate - extrude(sk.sketch, amount=-0.4)
export_step(plate, os.path.join(OUT, "hole_coupon.step"))
export_stl(plate, os.path.join(OUT, "hole_coupon.stl"), tolerance=0.01, angular_tolerance=0.1)
bb = plate.bounding_box()
json.dump({"holes": holes, "volume_mm3": round(plate.volume, 3), "bbox": [[bb.min.X, bb.min.Y, bb.min.Z], [bb.max.X, bb.max.Y, bb.max.Z]],
           "valid": bool(plate.is_valid), "solids": len(plate.solids())}, open(os.path.join(OUT, "coupon_facts.json"), "w"), indent=1)
print("coupon", round(plate.volume, 1), "mm3", len(holes), "holes", "valid", plate.is_valid)
