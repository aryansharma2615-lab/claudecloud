"""SP AV engine — v7.1 ratchet (applied to viewer_template_motion_v7.html).

R16 WIRES    lead colours that match how SP wires: config → factory lead (label / library) →
             carried along the run from a factory lead (servo SIG orange reaches UNO D5) →
             red/black convention for power and ground → "any colour · tag it". Pin ranges
             ("D8–11", "IN1–4") and "5-pin" plugs expand to one row per wire; a generic pin that
             mates a factory plug takes the plug's wires. Abbreviations read in full (brn → brown).
R17 TRACES   dashed explode trace lines from each part's home to where it is now.
R18 SEARCH   find a part by name / material / note; Enter selects, fits and opens it.
R19 BENCH    "Mark done" per Build step + "Next to build", progress on the timeline; kept on
             this device (localStorage, guarded), never shared.
R20 FILES    snapshot PNG and a wire cut-list CSV (routed length + 40 mm): both are on the
             artifact downloads allowlist, so they go out as-is, no zip.
R21 PEEK     long-press a part = select it and open its card (phones have no hover).
R22 SCALE    a mm scale bar at the orbit target (exact in ortho).
R23 LINK     the copied link (⧉) carries the camera: #…&cam=yaw,pitch,dist,px,py,pz[,o].
R24 FOCUS    hides header, presets and the explode row; haptic ticks on fits / snaps / ticks.

The module lives in engine_v7_1.js + engine_v7_1.css and is inlined before BOOT, after v7's.

    python3 patch_engine_v7_1.py          -> viewer_template_motion_v7_1.html
    from patch_engine_v7_1 import patch   -> patch(v7 html) -> v7.1 html
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "viewer_template_motion_v7.html"
JS = HERE / "engine_v7_1.js"
CSS = HERE / "engine_v7_1.css"


def sub(s, old, new, count=1):
    n = s.count(old)
    assert n == count, f"anchor found {n}x (want {count}): {old[:80]!r}"
    return s.replace(old, new)


def patch(s):
    assert s.count("SP AV ENGINE v7 — module") == 1, "not a v7 page: run patch_engine_v7 first"
    js = JS.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    s = sub(s, '<div id="app">', '<style>\n' + css + '</style>\n<div id="app">')
    s = sub(s, '      <button class="tbtn" id="bSpin"  aria-pressed="false" title="Turntable">Spin</button>',
            '      <button class="tbtn" id="bSpin"  aria-pressed="false" title="Turntable">Spin</button>\n'
            '      <button class="tbtn" id="bSnap" title="Save this view as a PNG">Snap</button>\n'
            '      <button class="tbtn" id="bFocus" aria-pressed="false" title="Hide the header and presets">Focus</button>')
    s = sub(s, '<div id="vcube" role="group" aria-label="View cube"><div id="vcIn"></div></div>',
            '<div id="vcube" role="group" aria-label="View cube"><div id="vcIn"></div></div>\n'
            '    <div id="scalebar" aria-hidden="true"><i></i><span></span></div>')
    i = s.index("   BOOT\n   ====")
    j = s.rindex("/* ====", 0, i)
    s = s[:j] + js + "\n" + s[j:]
    assert s.count("SP AV ENGINE v7.1 — module") == 1
    return s


if __name__ == "__main__":
    out = patch(SRC.read_text(encoding="utf-8"))
    (HERE / "viewer_template_motion_v7_1.html").write_text(out, encoding="utf-8")
    print("patched engine written:", len(out), "bytes")
