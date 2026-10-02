"""SP AV engine — v7.4 ratchet (applied to viewer_template_motion_v7_3.html).

R33 ANGLE   ∠ tool (tool rail, key A): three snapped taps -> the angle at the middle one, drawn.
R34 HISTORY ◀ / ▶ (keys [ ]) step back / forward through settled views (camera, pan, projection).
R35 SWIPE   swipe the Build step card left / right to change step.
R36 WIRE    "Wire to buy" on the Wiring tab: cut lengths × conductors, summed per gauge.
R37 KEYS    "?" opens the key map (desktop; hidden on touch-only screens).

    python3 patch_engine_v7_4.py          -> viewer_template_motion_v7_4.html
    from patch_engine_v7_4 import patch   -> patch(v7.3 html) -> v7.4 html
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "viewer_template_motion_v7_3.html"
JS = HERE / "engine_v7_4.js"
CSS = HERE / "engine_v7_4.css"


def sub(s, old, new, count=1):
    n = s.count(old)
    assert n == count, f"anchor found {n}x (want {count}): {old[:80]!r}"
    return s.replace(old, new)


def patch(s):
    assert s.count("SP AV ENGINE v7.3 — module") == 1, "not a v7.3 page: run patch_engine_v7_3 first"
    s = sub(s, '<div id="app">', '<style>\n' + CSS.read_text(encoding="utf-8") + '</style>\n<div id="app">')
    s = sub(s, '      <button class="tbtn" id="bFit" title="Fit all (F) · double-tap a part to fit it">Fit</button>',
            '      <button class="tbtn" id="bFit" title="Fit all (F) · double-tap a part to fit it">Fit</button>\n'
            '      <button class="tbtn" id="bBack" title="Previous view ([)" aria-label="Previous view" disabled>◀</button>\n'
            '      <button class="tbtn" id="bFwd" title="Next view (])" aria-label="Next view" disabled>▶</button>')
    s = sub(s, '      <button class="tbtn" id="bGap" aria-pressed="false" title="Clearance: tap two parts">Gap</button>',
            '      <button class="tbtn" id="bGap" aria-pressed="false" title="Clearance: tap two parts">Gap</button>\n'
            '      <button class="tbtn" id="bAng" aria-pressed="false" title="Angle: tap 3 points (A)">∠</button>')
    s = sub(s, '      <button class="tbtn" id="bFocus" aria-pressed="false" title="Hide the header and presets">Focus</button>',
            '      <button class="tbtn" id="bFocus" aria-pressed="false" title="Hide the header and presets">Focus</button>\n'
            '      <button class="tbtn" id="bKeys" title="Keyboard shortcuts (?)" aria-label="Keyboard shortcuts">?</button>')
    i = s.index("   BOOT\n   ====")
    j = s.rindex("/* ====", 0, i)
    s = s[:j] + JS.read_text(encoding="utf-8") + "\n" + s[j:]
    assert s.count("SP AV ENGINE v7.4 — module") == 1
    return s


if __name__ == "__main__":
    out = patch(SRC.read_text(encoding="utf-8"))
    (HERE / "viewer_template_motion_v7_4.html").write_text(out, encoding="utf-8")
    print("patched engine written:", len(out), "bytes")
