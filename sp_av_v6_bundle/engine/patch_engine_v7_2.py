"""SP AV engine — v7.2 ratchet (applied to viewer_template_motion_v7_1.html).

R25 CHECKS  a 7th dock tab. Shows the project's own gates (META.checks — the v5.3 line's R9
            tiles, now in the v6 line) and the three live CAD tools below.
R26 CLASH   scan of the current pose: every box-overlapping pair walked with the Motion BVH,
            every intersecting facet pair kept and sorted into contact (coplanar / edge on face,
            nothing reaches > 0.05 mm behind the other) or clash (both cross in); pairs marked
            by design (declared touch / mesh, screw in host, heat-set insert, press-fit bearing).
            Tap a row: both parts isolated, a clash tinted red, the deepest point marked.
R27 COG     centre of gravity (part mass {g, com}, else print.grams at the mesh centroid), the
            footprint on the ground, the margin and the static tip angle atan(margin / height);
            a CoG symbol + drop line + footprint in 3D, live in Motion poses.
R28 DIA     Ø tool: three snapped taps on a rim -> the circle through them: diameter + centre.

    python3 patch_engine_v7_2.py          -> viewer_template_motion_v7_2.html
    from patch_engine_v7_2 import patch   -> patch(v7.1 html) -> v7.2 html
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "viewer_template_motion_v7_1.html"
JS = HERE / "engine_v7_2.js"
CSS = HERE / "engine_v7_2.css"


def sub(s, old, new, count=1):
    n = s.count(old)
    assert n == count, f"anchor found {n}x (want {count}): {old[:80]!r}"
    return s.replace(old, new)


def patch(s):
    assert s.count("SP AV ENGINE v7.1 — module") == 1, "not a v7.1 page: run patch_engine_v7_1 first"
    js = JS.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    s = sub(s, '<div id="app">', '<style>\n' + css + '</style>\n<div id="app">')
    s = sub(s, '<button id="dPlate" aria-pressed="false"><span class="ic">▤</span>Plate</button>',
            '<button id="dPlate" aria-pressed="false"><span class="ic">▤</span>Plate</button>\n'
            '    <button id="dCheck" aria-pressed="false"><span class="ic">✓</span>Checks</button>')
    s = sub(s, 'for (const id of ["dParts","dBuild","dMotion","dBom","dWire","dPlate"])',
            'for (const id of ["dParts","dBuild","dMotion","dBom","dWire","dPlate","dCheck"])', count=2)
    s = sub(s, 'wire:"dWire",plate:"dPlate",motion:"dMotion"}[tab])', 'wire:"dWire",plate:"dPlate",motion:"dMotion",check:"dCheck"}[tab])')
    s = sub(s, '["build","dBuild"],["bom","dBom"],["plate","dPlate"]]){', '["build","dBuild"],["bom","dBom"],["plate","dPlate"],["check","dCheck"]]){')
    s = sub(s, 'wire:showWire, plate:showPlate, motion:showMotion}[tab] || showParts)();',
            'wire:showWire, plate:showPlate, motion:showMotion, check:showChecks}[tab] || showParts)();')
    s = sub(s, '["dBom","bom"],["dWire","wire"],["dPlate","plate"]]){', '["dBom","bom"],["dWire","wire"],["dPlate","plate"],["dCheck","check"]]){')
    s = sub(s, '      <button class="tbtn" id="bMeas"', '      <button class="tbtn" id="bDia" aria-pressed="false" title="Hole diameter: tap 3 rim points">Ø</button>\n'
                                                    '      <button class="tbtn" id="bMeas"')
    i = s.index("   BOOT\n   ====")
    j = s.rindex("/* ====", 0, i)
    s = s[:j] + js + "\n" + s[j:]
    assert s.count("SP AV ENGINE v7.2 — module") == 1
    return s


if __name__ == "__main__":
    out = patch(SRC.read_text(encoding="utf-8"))
    (HERE / "viewer_template_motion_v7_2.html").write_text(out, encoding="utf-8")
    print("patched engine written:", len(out), "bytes")
