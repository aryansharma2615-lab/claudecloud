"""SP AV engine — v7 ratchet (applied to viewer_template_motion_v6.html).

R10 NAV     CAD-grade navigation: orbit about the picked point, pan (right/middle drag,
            shift+drag, two fingers), zoom to the cursor / pinch centre, a clickable view
            cube (6 faces + 12 edges + 8 corners), fit all, double-tap a part = fit it,
            orthographic <-> perspective, keys F / 1 3 7 (Ctrl = opposite) / 0 / 5 / 9.
R11 LOOK    key + fill + rim lights over a hemisphere ambient, per-material shading
            (PLA matte, PETG gloss, TPU satin, bought plastic, steel, brass), screen-space
            silhouette / crease / part-seam lines, a soft contact shadow, MSAA kept.
R12 BUILD   every Build step plays: parts fly in along `insert` (default: their explode
            vector), screws drive in along their axis while turning; play / pause / scrub
            per step, the old ▶ now plays the whole build; the build sheet stays static.
R13 WIRING  connector cards with pins in order and real lead colours, connector per end,
            gauge / current / drop chips, power budget + common-ground check, current-flow
            animation on the traced 3D tube and its schematic edge.
R14 3MF     honest label inside an artifact ("zipped by the viewer — tap to unzip"),
            direct .3mf locally, and the plate's real path on the Mac with copy buttons.
R15 UI      Fit / Persp-Ortho / Edges / Spin in the tool rail, 44 px tool targets on phones.

The module itself lives in engine_v7.js + engine_v7.css next to this file and is inlined
before BOOT. It reaches the v6 engine through the anchored patches below and by wrapping
v6 function declarations by name (see the module header). Every anchor is asserted.

    python3 patch_engine_v7.py            -> viewer_template_motion_v7.html
    from patch_engine_v7 import patch     -> patch(html) -> html   (refs, regression)
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "viewer_template_motion_v6.html"
JS = HERE / "engine_v7.js"
CSS = HERE / "engine_v7.css"


def sub(s, old, new, count=1):
    n = s.count(old)
    assert n == count, f"anchor found {n}x (want {count}): {old[:80]!r}"
    return s.replace(old, new)


NEW_FS = r"""const FS = `#version 300 es
precision highp float;
in vec3 vP; in vec3 vW;
uniform vec3 uCol, uCut, uUpV;
uniform vec4 uClip;            // xyz = plane normal, w = offset
uniform vec4 uMat;             // RATCHET v7 R11: specular, shininess, metal, sheen
uniform float uDim, uAlpha, uClipOn, uOrtho;
out vec4 o;
void main(){
  if (uClipOn > 0.5 && dot(vW, uClip.xyz) > uClip.w) discard;
  // Flat facet normal from screen-space derivatives: crisp CAD facets, and no
  // normal attribute in the buffer, which is a third of the bandwidth saved.
  vec3 n = normalize(cross(dFdx(vP), dFdy(vP)));
  if (!gl_FrontFacing) n = -n;   // section cuts expose back faces
  vec3 V = uOrtho > 0.5 ? vec3(0.0,0.0,1.0) : normalize(-vP);
  // three lights fixed to the camera like a CAD viewport: key upper right,
  // fill low left, rim from behind; a sky/ground hemisphere instead of a flat ambient
  vec3 Lk = normalize(vec3(0.45,0.60,0.66));
  vec3 Lf = normalize(vec3(-0.70,-0.15,0.45));
  vec3 Lr = normalize(vec3(-0.20,0.55,-0.80));
  float hemi = 0.5 + 0.5*dot(n, uUpV);
  vec3 amb = mix(vec3(0.20,0.19,0.18), vec3(0.40,0.42,0.45), hemi);
  float dk = max(dot(n,Lk),0.0), df = max(dot(n,Lf),0.0);
  vec3 c = uCol;
  float g = dot(c, vec3(0.299,0.587,0.114));
  c = mix(c, vec3(g*0.86+0.10), uDim);
  // a cut face reads as machined material, not as "the model is hollow"
  if (!gl_FrontFacing && uClipOn > 0.5) c = mix(c, uCut, 0.62);
  float metal = uMat.z, nv = max(dot(n,V),0.0);
  vec3 col = c * (amb + dk*0.72 + df*0.22) * (1.0 - 0.42*metal);
  vec3 H = normalize(Lk + V);
  float sp = pow(max(dot(n,H),0.0), uMat.y) * uMat.x * (1.0 - uDim*0.85);
  col += mix(vec3(1.0), c*1.35 + 0.08, metal) * sp;
  // metal mirrors the hemisphere: that gradient is what reads as "steel" at a glance
  float rz = dot(reflect(-V,n), uUpV);
  col += metal * c * mix(0.10, 0.42, 0.5 + 0.5*rz);
  col += uMat.w * pow(1.0 - nv, 2.0) * 0.30 * c;                       // TPU / jacket sheen
  col += pow(1.0 - nv, 3.0) * (0.08 + 0.22*max(dot(n,Lr),0.0)) * (1.0-uDim);   // rim
  o = vec4(col, uAlpha);
}`;"""


def patch(s):
    js = JS.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")

    # ---------------- page: styles, cube, tools, hint ----------------
    s = sub(s, '<div id="app">', '<style>\n' + css + '</style>\n<div id="app">')
    s = sub(s, '<div id="hint"><b>drag</b> spin · <b>wheel</b> zoom · <b>tap</b> identify · <b>shift-tap</b> multi</div>',
            '<div id="hint"><b>drag</b> orbit · <b>right-drag</b> pan · <b>wheel</b> zoom to cursor · '
            '<b>dbl-click</b> fit part · <b>F</b> fit</div>')
    s = sub(s, '<div id="fps">— fps</div>',
            '<div id="fps">— fps</div>\n    <div id="vcube" role="group" aria-label="View cube"><div id="vcIn"></div></div>')
    s = sub(s, '      <button class="tbtn" id="bMeas"',
            '      <button class="tbtn" id="bFit" title="Fit all (F) · double-tap a part to fit it">Fit</button>\n'
            '      <button class="tbtn" id="bOrtho" aria-pressed="false" title="Perspective / orthographic (5)">Persp</button>\n'
            '      <button class="tbtn" id="bMeas"')
    s = sub(s, '      <button class="tbtn" id="bLab"   aria-pressed="true">Labels</button>',
            '      <button class="tbtn" id="bLab"   aria-pressed="true">Labels</button>\n'
            '      <button class="tbtn" id="bEdge"  aria-pressed="true" title="CAD edge lines">Edges</button>\n'
            '      <button class="tbtn" id="bSpin"  aria-pressed="false" title="Turntable">Spin</button>')

    # ---------------- globals the module needs before draw() runs ----------------
    s = sub(s, 'const META = JSON.parse(document.getElementById("meta").textContent);',
            '/* RATCHET v7: module state, assigned by the v7 module before BOOT */\nvar V7 = null;\n'
            'const META = JSON.parse(document.getElementById("meta").textContent);')
    # R10: the orbit target carries a pan offset
    s = sub(s, 'function target(){ return plateMode ? PLATE_CTR : (focus ? focus.c : CTR); }',
            '/* RATCHET v7 R10: pan = an offset on the orbit target, so pan moves the camera, never the model */\n'
            'const PAN = [0,0,0];\n'
            'function target(){ const b = plateMode ? PLATE_CTR : (focus ? focus.c : CTR);\n'
            '  return [b[0]+PAN[0], b[1]+PAN[1], b[2]+PAN[2]]; }')
    # zoom-to-cursor gets close to a screw; the old floor stopped 14 % of the model away
    s = sub(s, 'const ZMIN = () => (plateMode?PLATE_R:_bb)*0.14;', 'const ZMIN = () => (plateMode?PLATE_R:_bb)*0.02;')
    # orthographic: every M.persp caller gets it, and the sheet skew becomes a translation
    s = sub(s, 'persp(f,a,n,fa){ const t=1/Math.tan(f/2);',
            'persp(f,a,n,fa){ if (V7 && V7.ortho) return orthoP(f,a,fa); const t=1/Math.tan(f/2);')
    s = sub(s, 'P[9] = -viewShiftY;', 'skewY(P);', count=3)
    s = sub(s, 'Pp[9]=-viewShiftY;', 'skewY(Pp);')
    # every eased move can carry the pan too
    s = sub(s, 'const from={yaw:cam.yaw, pitch:cam.pitch, dist:cam.dist, explode};',
            'const from={yaw:cam.yaw, pitch:cam.pitch, dist:cam.dist, explode, pan:PAN.slice()};\n'
            '  const toPan = to.pan || (V7 && V7.panNext) || null; if (V7) V7.panNext = null;')
    s = sub(s, '    if (to.explode!==undefined){\n      explode = from.explode',
            '    if (toPan) for (let i=0;i<3;i++) PAN[i] = from.pan[i] + (toPan[i]-from.pan[i])*k;\n'
            '    if (to.explode!==undefined){\n      explode = from.explode')
    s = sub(s, 'glide({yaw:HOME.yaw, pitch:HOME.pitch, dist:HOME.dist, explode:0}, 380);',
            'glide({yaw:HOME.yaw, pitch:HOME.pitch, dist:HOME.dist, explode:0, pan:[0,0,0]}, 380);')
    s = sub(s, 'glide({yaw:HOME.yaw, pitch:HOME.pitch, dist:focus.d}, 380);',
            'glide({yaw:HOME.yaw, pitch:HOME.pitch, dist:focus.d, pan:[0,0,0]}, 380);')

    # ---------------- R11: shading, edges, shadow ----------------
    i0 = s.index('const FS = `#version 300 es')
    i1 = s.index('}`;', i0) + 3
    old_fs = s[i0:i1]
    assert 'float rim = pow(1.0 - abs(normalize(-vP).z), 3.0) * 0.22 * (1.0-uDim);' in old_fs, "FS changed"
    s = sub(s, old_fs, NEW_FS)
    s = sub(s, 'const U  = ["uMVP","uMV","uModel","uLo","uSpan","uCol","uCut","uDim","uAlpha","uClip","uClipOn"];',
            'const U  = ["uMVP","uMV","uModel","uLo","uSpan","uCol","uCut","uDim","uAlpha","uClip","uClipOn","uMat","uUpV","uOrtho"];')
    s = sub(s, 'gl.uniform3fv(uni.uCol,new Float32Array(moTint.get(p.id) || p.rgb));',
            'gl.uniform3fv(uni.uCol,new Float32Array(moTint.get(p.id) || p.rgb));\n    gl.uniform4fv(uni.uMat, matOf(p));')
    s = sub(s, 'gl.uniformMatrix4fv(uni.uMV,false,new Float32Array(V));',
            'gl.uniformMatrix4fv(uni.uMV,false,new Float32Array(V));\n  v7Uniforms(V);')
    s = sub(s, '  drawLines(MVP);\n', '  drawLines(MVP);\n  v7Shadow(MVP);\n')
    s = sub(s, '  const gh = parts.filter(p => state(p)==="ghost");',
            '  v7Edges(MVP, V, w, h, clip);\n  const gh = parts.filter(p => state(p)==="ghost");')

    # ---------------- R12: step animation rides on the assembly matrix ----------------
    s = sub(s, '  return [M.trans(explodeVec(p))];', '  return [stepAnimM(p, M.trans(explodeVec(p)))];')

    # ---------------- R10: picking without the measure-tool corner snap ----------------
    s = sub(s, 'function raycast(cssX, cssY){', 'function raycast(cssX, cssY, noSnap){')
    s = sub(s, 'if (bd < diag*0.035){', 'if (!noSnap && bd < diag*0.035){')

    # ---------------- R10: pointer handling ----------------
    s = sub(s, '''cv.addEventListener("pointerdown", e=>{
  cv.setPointerCapture(e.pointerId); beginInteract();
  if (!drag){ drag={id:e.pointerId,x:e.clientX,y:e.clientY}; moved=0;
    // Motion: a press on a moving part grabs its JOINT, not the camera
    if (motionMode && !measOn && !(pathView && pathView.data)){
      const [cx,cy] = cssPt(e);
      if (beginJointDrag(cx, cy)) drag.joint = true;
    } }
  else { pinch={d:Math.hypot(e.clientX-drag.x,e.clientY-drag.y), dist:cam.dist};
         if (jdrag){ jdrag = null; drag.joint = false; } }
});
cv.addEventListener("pointermove", e=>{
  if (pinch && drag && e.pointerId!==drag.id){
    const d=Math.hypot(e.clientX-drag.x,e.clientY-drag.y);
    cam.dist=Math.min(ZMAX(),Math.max(ZMIN(), pinch.dist*pinch.d/Math.max(d,1)));
    draw(); return;
  }
  if (!drag || e.pointerId!==drag.id) return;
  const dx=e.clientX-drag.x, dy=e.clientY-drag.y;
  moved += Math.abs(dx)+Math.abs(dy);
  if (drag.joint && jdrag){
    if (moved > 3){ dragJoint(dx, dy); draw(); }
    drag.x=e.clientX; drag.y=e.clientY; return;
  }
  cam.yaw -= dx*0.0085;
  cam.pitch = Math.max(-1.45, Math.min(1.45, cam.pitch + dy*0.0085));
  drag.x=e.clientX; drag.y=e.clientY;
  clearPreset(); draw();
});''', '''/* RATCHET v7 R10: CAD navigation. Left drag orbits about the point under the
   finger, right / middle / shift drag pans, two fingers pan + pinch about their
   centre. Motion still grabs a joint first (left button, no modifier). */
cv.addEventListener("pointerdown", e=>{
  cv.setPointerCapture(e.pointerId); beginInteract();
  ptrs.set(e.pointerId, [e.clientX, e.clientY]);
  if (!drag){ drag={id:e.pointerId,x:e.clientX,y:e.clientY}; moved=0;
    // Motion: a press on a moving part grabs its JOINT, not the camera
    if (motionMode && !measOn && !(pathView && pathView.data) && e.button===0 && !e.shiftKey){
      const [cx,cy] = cssPt(e);
      if (beginJointDrag(cx, cy)) drag.joint = true;
    }
    navDown(e); }
  else if (ptrs.size >= 2){ pinch = navPinchStart();
         if (jdrag){ jdrag = null; drag.joint = false; } }
});
cv.addEventListener("pointermove", e=>{
  if (ptrs.has(e.pointerId)) ptrs.set(e.pointerId, [e.clientX, e.clientY]);
  if (pinch && ptrs.size >= 2){ moved += 99; navPinchMove(pinch); clearPreset(); draw(); return; }
  if (!drag || e.pointerId!==drag.id) return;
  const dx=e.clientX-drag.x, dy=e.clientY-drag.y;
  moved += Math.abs(dx)+Math.abs(dy);
  if (drag.joint && jdrag){
    if (moved > 3){ dragJoint(dx, dy); draw(); }
    drag.x=e.clientX; drag.y=e.clientY; return;
  }
  navDrag(dx, dy);
  drag.x=e.clientX; drag.y=e.clientY;
  clearPreset(); draw();
});''')
    s = sub(s, 'function up(e){\n', 'function up(e){\n  ptrs.delete(e.pointerId); if (ptrs.size < 2 && pinch && drag) { const me = ptrs.get(drag.id); if (me){ drag.x = me[0]; drag.y = me[1]; } }\n')
    s = sub(s, 'else { const [x,y]=glPt(e); pickPart(pickAt(x,y), e.shiftKey); }',
            'else { const [x,y]=glPt(e); const hp=pickAt(x,y); if (!navTap(cx,cy,hp)) pickPart(hp, e.shiftKey); }')
    s = sub(s, '''  cam.dist=Math.min(ZMAX(),Math.max(ZMIN(), cam.dist*(1+Math.sign(e.deltaY)*0.11)));
  draw(); endInteract();''', '''  navWheel(e); clearPreset();     // RATCHET v7 R10: zoom about the point under the cursor
  draw(); endInteract();''')
    # F is "fit" in every CAD package; the fps chip moves to ` (and p)
    s = sub(s, 'else if (k==="f"){', 'else if (k==="`" || k==="p"){')

    # ---------------- the module ----------------
    i = s.index("   BOOT\n   ====")
    j = s.rindex("/* ====", 0, i)
    s = s[:j] + js + "\n" + s[j:]
    assert s.count("SP AV ENGINE v7 — module") == 1
    return s


if __name__ == "__main__":
    out = patch(SRC.read_text(encoding="utf-8"))
    (HERE / "viewer_template_motion_v7.html").write_text(out, encoding="utf-8")
    print("patched engine written:", len(out), "bytes")
