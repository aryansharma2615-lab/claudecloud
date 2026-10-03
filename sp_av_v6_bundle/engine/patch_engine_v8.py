"""SP AV engine — v8 ratchet (applied to viewer_template_motion_v7_4.html).

LOAD → FIT → SECURE → TEST on top of everything v7 … v7.4 does (R38–R54, see engine_v8.js header).
Shader: the base program stays the v7.4 one except the section CAP (flat hatched fill on the back
faces a cut exposes). Heat + wireframe live in a SECOND program (engine_v8.js builds it from the base
source at first use) so a frame that shows neither pays nothing for them — on SwiftShader a uniform
branch still costs both sides.

    python3 patch_engine_v8.py          -> viewer_template_motion_v8.html
    from patch_engine_v8 import patch   -> patch(v7.4 html) -> v8 html
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "viewer_template_motion_v7_4.html"
JS = HERE / "engine_v8.js"
CSS = HERE / "engine_v8.css"


def sub(s, old, new, count=1):
    n = s.count(old)
    assert n == count, f"anchor found {n}x (want {count}): {old[:80]!r}"
    return s.replace(old, new)


def patch(s):
    assert s.count("SP AV ENGINE v7.4 — module") == 1, "not a v7.4 page: run patch_engine_v7_4 first"
    s = sub(s, '<div id="app">', '<style>\n' + CSS.read_text(encoding="utf-8") + '</style>\n<div id="app">')
    # ---- DOM: phase bar, tools, share, footer, loader brand ----
    s = sub(s, '    <button class="icob" id="bTheme" title="Light / dark" aria-label="Toggle theme">◐</button>\n  </header>',
            '    <button class="icob" id="bShare" title="Share this exact view (phase, camera, explode, section, load)" aria-label="Share view"><span aria-hidden="true">↗</span><span class="t"> Share</span></button>\n'
            '    <button class="icob" id="bTheme" title="Light / dark" aria-label="Toggle theme">◐</button>\n  </header>\n'
            '  <nav id="v8phase" aria-label="Guided phases"></nav>')
    s = sub(s, '    <div id="load">decoding geometry…</div>',
            '    <div id="load">decoding geometry…<span class="v8brand">Shawarma Prints · Designed in Vaughan, ON</span></div>')
    s = sub(s, '      <button class="tbtn" id="bMeas"  aria-pressed="false" title="Tap two features for a distance">Measure</button>',
            '      <button class="tbtn" id="bMeas"  aria-pressed="false" title="Tap two features for a distance">Measure</button>\n'
            '      <button class="tbtn" id="bCal" aria-pressed="false" title="Caliper: tap two features (C)">Caliper</button>')
    s = sub(s, '      <button class="tbtn" id="bKeys" title="Keyboard shortcuts (?)" aria-label="Keyboard shortcuts">?</button>',
            '      <button class="tbtn" id="bKeys" title="Keyboard shortcuts (?)" aria-label="Keyboard shortcuts">?</button>\n'
            '      <button class="tbtn" id="bTree" aria-pressed="false" title="Parts tree (T)">Tree</button>\n'
            '      <button class="tbtn" id="bPerf" aria-pressed="false" title="fps · triangles · draw calls">Perf</button>')
    s = sub(s, '  <nav id="dock" role="group" aria-label="Panels">',
            '  <div id="v8foot">Prototyped on Ender 3 S1 Pro · Toronto, Canada</div>\n  <nav id="dock" role="group" aria-label="Panels">')
    # ---- shaders ----
    s = sub(s, "  if (!gl_FrontFacing && uClipOn > 0.5) c = mix(c, uCut, 0.62);",
            "  /* RATCHET v8 R47: the cut face is a CAP — flat, hatched, opaque — never a see-through shell */\n"
            "  if (!gl_FrontFacing && uClipOn > 0.5){ float hb = step(0.5, fract((gl_FragCoord.x + gl_FragCoord.y)/9.0));\n"
            "    o = vec4(mix(uCut*0.78, uCut, hb), 1.0); return; }")
    # ---- R56: CSS variables are read every frame (stage, cut, shadow, edges); right after the overlays
    #      moved, each read forced a style recalc. Cache them; any theme / class change on <html> clears it.
    s = sub(s, 'const cssVar = n => getComputedStyle(document.documentElement)\n                      .getPropertyValue(n).trim();',
            'const CSSV = new Map();   /* RATCHET v8 R56 */\n'
            'new MutationObserver(() => CSSV.clear()).observe(document.documentElement, {attributes: true, attributeFilter: ["data-theme", "class", "style"]});\n'
            'try { matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => CSSV.clear()); } catch(e){}\n'
            'const cssVar = n => { let v = CSSV.get(n); if (v === undefined){ v = getComputedStyle(document.documentElement).getPropertyValue(n).trim(); CSSV.set(n, v); } return v; };')
    # ---- draw: hover tint + per-part heat uniforms ----
    s = sub(s, "    gl.uniform3fv(uni.uCol,new Float32Array(moTint.get(p.id) || p.rgb));\n    gl.uniform4fv(uni.uMat, matOf(p));",
            "    gl.uniform3fv(uni.uCol,new Float32Array(v8Tint(p) || moTint.get(p.id) || p.rgb));\n    gl.uniform4fv(uni.uMat, matOf(p)); v8PartUniforms(p);")
    # ---- the module, before BOOT (same mechanism as v7 … v7.4) ----
    i = s.index("   BOOT\n   ====")
    j = s.rindex("/* ====", 0, i)
    s = s[:j] + JS.read_text(encoding="utf-8") + "\n" + s[j:]
    assert s.count("SP AV ENGINE v8 — module") == 1
    return s


if __name__ == "__main__":
    out = patch(SRC.read_text(encoding="utf-8"))
    (HERE / "viewer_template_motion_v8.html").write_text(out, encoding="utf-8")
    print("patched engine written:", len(out), "bytes")
