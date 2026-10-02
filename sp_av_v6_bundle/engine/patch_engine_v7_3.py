"""SP AV engine — v7.3 ratchet (applied to viewer_template_motion_v7_2.html).

R29 GAP     Gap tool (tool rail + Checks): tap two parts -> the minimum clearance by the Motion
            BVH distance query, the two closest points, a 3D dimension line, and the FDM verdict
            (0 = touching / clashing, < 0.2 mm prints fused or binds, else free).
R30 TIGHT   Tight-gaps report in Checks: every non-touching pair of non-screw parts closer than
            2 mm, smallest first; tap a row to isolate the pair with its dimension.
R31 BOM     ⤓ BOM (CSV) on the BOM tab — qty, status, each, line, ×10/×50/×100, supplier, link.
R32 SECTION a 44 px drag handle on the cut plane itself; drag along the axis, or arrow keys.

    python3 patch_engine_v7_3.py          -> viewer_template_motion_v7_3.html
    from patch_engine_v7_3 import patch   -> patch(v7.2 html) -> v7.3 html
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "viewer_template_motion_v7_2.html"
JS = HERE / "engine_v7_3.js"
CSS = HERE / "engine_v7_3.css"


def sub(s, old, new, count=1):
    n = s.count(old)
    assert n == count, f"anchor found {n}x (want {count}): {old[:80]!r}"
    return s.replace(old, new)


def patch(s):
    assert s.count("SP AV ENGINE v7.2 — module") == 1, "not a v7.2 page: run patch_engine_v7_2 first"
    s = sub(s, '<div id="app">', '<style>\n' + CSS.read_text(encoding="utf-8") + '</style>\n<div id="app">')
    s = sub(s, '<button class="tbtn" id="bDia" aria-pressed="false" title="Hole diameter: tap 3 rim points">Ø</button>',
            '<button class="tbtn" id="bDia" aria-pressed="false" title="Hole diameter: tap 3 rim points">Ø</button>\n'
            '      <button class="tbtn" id="bGap" aria-pressed="false" title="Clearance: tap two parts">Gap</button>')
    i = s.index("   BOOT\n   ====")
    j = s.rindex("/* ====", 0, i)
    s = s[:j] + JS.read_text(encoding="utf-8") + "\n" + s[j:]
    assert s.count("SP AV ENGINE v7.3 — module") == 1
    return s


if __name__ == "__main__":
    out = patch(SRC.read_text(encoding="utf-8"))
    (HERE / "viewer_template_motion_v7_3.html").write_text(out, encoding="utf-8")
    print("patched engine written:", len(out), "bytes")
