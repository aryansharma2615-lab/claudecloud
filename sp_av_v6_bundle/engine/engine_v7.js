/* ===========================================================================
   SP AV ENGINE v7 — module (inlined by patch_engine_v7.py, before BOOT)
   R10 CAD navigation · R11 viewport look · R12 animated build steps ·
   R13 detailed wiring · R14 honest 3MF hand-off · R15 v7 UI extras.
   Everything here hooks the v6 engine through a handful of anchored patches
   and by WRAPPING its function declarations (renderStep, showWire, …): a
   declaration is a mutable binding, and every v6 caller looks it up by name
   at call time, so a wrapper reaches all of them without touching their text.
   =========================================================================== */
V7 = {ortho:false, noAnim:false, edges:true, shadow:true, pivot:null,
      turntable:false, ver:"7.0"};
const V7RM = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
const clamp01 = x => x < 0 ? 0 : x > 1 ? 1 : x;
const ease3 = u => u < 0.5 ? 4*u*u*u : 1 - Math.pow(-2*u+2, 3)/2;   // in-out cubic
const easeOut = u => 1 - Math.pow(1-u, 3);

/* ---------- 4×4 helpers the v6 M object does not have ---------- */
function rotM(axis, ang){                      // rotation about a unit axis through 0
  const [x,y,z] = nrm(axis), c = Math.cos(ang), s = Math.sin(ang), t = 1-c;
  return [t*x*x+c,   t*x*y+s*z, t*x*z-s*y, 0,
          t*x*y-s*z, t*y*y+c,   t*y*z+s*x, 0,
          t*x*z+s*y, t*y*z-s*x, t*z*z+c,   0,  0,0,0,1];
}
function v7RotAbout(m, at, axis, ang){            // m · T(at) · R · T(−at)
  return M.mul(m, M.mul(M.trans(at), M.mul(rotM(axis, ang), M.trans(scl(at,-1)))));
}
function rodrigues(v, k, a){
  const c = Math.cos(a), s = Math.sin(a), kv = dot(k,v), kx = cross(k,v);
  return [v[0]*c + kx[0]*s + k[0]*kv*(1-c),
          v[1]*c + kx[1]*s + k[1]*kv*(1-c),
          v[2]*c + kx[2]*s + k[2]*kv*(1-c)];
}

/* ===========================================================================
   R10 — CAD-GRADE NAVIGATION
   One idea carries all of it: the camera is target + PAN, looked at from
   (yaw, pitch, dist). Orbit about a picked point, zoom to the cursor and pan
   all become "move PAN and one other number so the point under your finger
   stays put" — exact for both projections, which is what the 2 px gate checks.
   =========================================================================== */
function orthoP(f, a, fa){
  const hh = dist()*Math.tan(f/2), hw = hh*a;
  const far = Math.max(fa, dist()*2 + _bb*12);
  const n = -far;                 // an orthographic eye sees what is behind it: nothing clips at the eye
  return [1/hw,0,0,0, 0,1/hh,0,0, 0,0,-2/(far-n),0, 0,0,-(far+n)/(far-n),1];
}
/* The bottom sheet skews the frame up by viewShiftY. Perspective does it
   through P[9] (scaled by depth, then divided back out by w); an orthographic
   matrix has w = 1, so the same shift is a plain translation in P[13]. */
function skewY(P){ if (V7 && V7.ortho) P[13] = viewShiftY; else P[9] = -viewShiftY; }

rayFromPixel = (orig => function(cssX, cssY){
  if (!V7.ortho) return orig(cssX, cssY);
  const r = cv.getBoundingClientRect();
  const ndcx = (cssX/r.width)*2 - 1, ndcy = 1 - (cssY/r.height)*2;
  const E = eye(), T = target();
  const f = nrm(sub(T,E)), rt = nrm(cross(f,[0,0,1])), up = cross(rt,f);
  const hh = dist()*Math.tan(FOV/2), hw = hh*r.width/r.height;
  const o = add(T, add(scl(rt, ndcx*hw), scl(up, (ndcy - viewShiftY)*hh)));
  return {o: sub(o, scl(f, dist()*2 + _bb*6)), d: f};
})(rayFromPixel);

function camBasis(){
  const E = eye(), T = target();
  const f = nrm(sub(T,E)), rt = nrm(cross(f,[0,0,1])), up = cross(rt,f);
  return {E, T, f, rt, up};
}
/* the world point under a canvas pixel: the nearest real surface, else the
   point on the plane through the orbit target facing the camera */
function worldAt(cx, cy){
  const {o, d} = rayFromPixel(cx, cy);
  const h = raycast(cx, cy, true);
  if (h) return {p: add(o, scl(d, h.t)), part: h.part, hit: true};
  const {T, f} = camBasis();
  const t = dot(sub(T, o), f) / (dot(d, f) || 1e-9);
  return {p: add(o, scl(d, t)), part: null, hit: false};
}
function depthOf(P){ const {E, f} = camBasis(); return Math.max(1, dot(sub(P, E), f)); }

function orbitAbout(P, dyaw, dpitch){
  const p0 = cam.pitch, p1 = Math.max(-1.45, Math.min(1.45, p0 + dpitch));
  const T = target();
  let v = sub(T, P);
  v = rodrigues(v, [Math.sin(cam.yaw), -Math.cos(cam.yaw), 0], p1 - p0);   // pitch about the camera's right axis
  v = rodrigues(v, [0,0,1], dyaw);                                          // then yaw about world up
  const T2 = add(P, v);
  cam.yaw += dyaw; cam.pitch = p1;
  for (let i=0;i<3;i++) PAN[i] += T2[i] - T[i];
}
function panPx(dx, dy, depth){
  const r = cv.getBoundingClientRect();
  const k = 2*(V7.ortho ? dist() : (depth || dist()))*Math.tan(FOV/2) / Math.max(1, r.height);
  const {rt, up} = camBasis();
  for (let i=0;i<3;i++) PAN[i] += -rt[i]*dx*k + up[i]*dy*k;
}
function zoomAt(P, f){
  const d0 = cam.dist, d1 = Math.min(ZMAX(), Math.max(ZMIN(), d0*f)), k = d1/d0;
  const T = target();
  cam.dist = d1;
  for (let i=0;i<3;i++) PAN[i] += (P[i] - T[i])*(1 - k);   // T' = P + (T−P)·k keeps P on its pixel
}

/* ---- pointer plumbing called from the patched v6 listeners ---- */
const ptrs = new Map();
function navDown(e){
  drag.btn = e.button; drag.mode = (e.button === 1 || e.button === 2 || e.shiftKey) ? "pan" : "orbit";
  const [cx, cy] = cssPt(e); drag.sx = cx; drag.sy = cy; drag.pivot = undefined;
  if (V7.turntable) setTurntable(false);
}
function navDrag(dx, dy){
  if (drag.mode === "pan"){
    if (drag.pivot === undefined){ const w = worldAt(drag.sx, drag.sy); drag.pivot = w.p; drag.depth = depthOf(w.p); }
    panPx(dx, dy, drag.depth);
  } else {
    if (drag.pivot === undefined){ const w = worldAt(drag.sx, drag.sy); drag.pivot = w.hit ? w.p : null; }
    V7.pivot = drag.pivot;
    orbitAbout(drag.pivot || target(), -dx*0.0085, dy*0.0085);
  }
}
function navPinchGeom(){
  const a = [...ptrs.values()]; if (a.length < 2) return null;
  const r = cv.getBoundingClientRect(), [p, q] = a;
  return {c: [(p[0]+q[0])/2 - r.left, (p[1]+q[1])/2 - r.top], d: Math.max(1, Math.hypot(p[0]-q[0], p[1]-q[1]))};
}
function navPinchStart(){
  const g = navPinchGeom(); if (!g) return null;
  const w = worldAt(g.c[0], g.c[1]);
  return {c: g.c, d: g.d, P: w.p, depth: depthOf(w.p)};
}
function navPinchMove(pn){
  const g = navPinchGeom(); if (!g || !pn) return;
  panPx(g.c[0]-pn.c[0], g.c[1]-pn.c[1], pn.depth);      // two-finger drag = pan
  zoomAt(pn.P, pn.d / g.d);                            // spread = zoom about the pinch point
  pn.c = g.c; pn.d = g.d; pn.depth = depthOf(pn.P);
  const me = ptrs.get(drag && drag.id); if (me && drag){ drag.x = me[0]; drag.y = me[1]; }
}
function navWheel(e){
  const [cx, cy] = cssPt(e);
  const s = Math.max(-4, Math.min(4, (e.deltaMode === 1 ? e.deltaY*33 : e.deltaY) / 100));
  const f = Math.pow(e.ctrlKey ? 1.25 : 1.11, s);       // ctrl+wheel = a trackpad pinch
  zoomAt(worldAt(cx, cy).p, f);
}
cv.addEventListener("contextmenu", e => e.preventDefault());

/* ---- double-tap / double-click a part = fit that part ---- */
let lastTap = null;
function navTap(cx, cy, hp){
  const t = performance.now();
  if (hp && lastTap && lastTap.id === hp.id && t - lastTap.t < 380 && Math.hypot(cx-lastTap.x, cy-lastTap.y) < 30){
    lastTap = null; sel.clear(); sel.add(hp.id); syncUI();
    if (sheetTab === "inspect") renderInspector(hp);
    fitParts([hp]); return true;
  }
  lastTap = hp ? {t, id: hp.id, x: cx, y: cy} : null;
  return false;
}

/* ---- fit ---- */
function v7Box(list){
  const lo = [1e9,1e9,1e9], hi = [-1e9,-1e9,-1e9];
  for (const p of list) for (const m of instancesOf(p)) for (let i=0;i<8;i++){
    const c = M.xform(m, [p.lo[0]+((i&1)?p.span[0]:0), p.lo[1]+((i&2)?p.span[1]:0), p.lo[2]+((i&4)?p.span[2]:0)]);
    for (let k=0;k<3;k++){ lo[k] = Math.min(lo[k], c[k]); hi[k] = Math.max(hi[k], c[k]); }
  }
  return lo[0] > hi[0] ? null : {lo, hi};
}
function fitView(list, ms){
  const b = v7Box(list); if (!b) return;
  const c = [(b.lo[0]+b.hi[0])/2, (b.lo[1]+b.hi[1])/2, (b.lo[2]+b.hi[2])/2];
  const rad = Math.max(1.5, 0.5*Math.hypot(b.hi[0]-b.lo[0], b.hi[1]-b.lo[1], b.hi[2]-b.lo[2]));
  const r = cv.getBoundingClientRect(), asp = (r.width||1)/(r.height||1), tv = Math.tan(FOV/2);
  // the sheet skews the frame up, so the free band above and below the target is (1 − shift)
  const half = Math.min(Math.atan((1 - viewShiftY)*tv), Math.atan(tv*asp));
  const D = rad / Math.sin(Math.max(half, 0.05)) * 1.08;
  const mult = (plateMode ? 1 : (1 + explode*0.42)) * (1 + viewShiftY*0.85);
  const base = sub(target(), PAN);
  clearPreset();
  glide({dist: D/mult, pan: sub(c, base)}, ms === undefined ? 380 : ms);
}
function fitParts(list){ fitView(list); }
function fitAll(){
  let list = parts.filter(p => state(p) === "solid");
  if (!list.length) list = parts.filter(p => state(p) !== "off");
  if (!list.length) list = parts.filter(p => p.kind !== "wire");
  fitView(list);
}
function fitSelOrAll(){ const s = selParts(); s.length ? fitParts(s) : fitAll(); }

/* ---- view cube: Fusion-style, faces + 12 edges + 8 corners ----
   Six face buttons (each ≥ 44 px); WHERE on a face you tap picks the face,
   the edge or the corner (outer 28 % bands), so the cube stays big enough to
   hit with a thumb and still reaches all 26 directions. */
const VC_FACES = [
  ["FRONT",  [0,-1,0], [1,0,0],  [0,0,1]],
  ["BACK",   [0,1,0],  [-1,0,0], [0,0,1]],
  ["RIGHT",  [1,0,0],  [0,1,0],  [0,0,1]],
  ["LEFT",   [-1,0,0], [0,-1,0], [0,0,1]],
  ["TOP",    [0,0,1],  [1,0,0],  [0,1,0]],
  ["BOTTOM", [0,0,-1], [1,0,0],  [0,-1,0]],
];
const vcube = $("vcube"), vcIn = $("vcIn"), VC_EL = [];
let VC_L = 54;
let vcKey = "";
function vcSize(){ VC_L = Math.round((vcube.getBoundingClientRect().width || 96) * 0.56); vcKey = ""; return VC_L; }
addEventListener("resize", () => vcube && vcSize());
if (vcube){
  vcSize();
  for (const [nm, n, u, v] of VC_FACES){
    const b = document.createElement("div");
    b.className = "vcf"; b.dataset.face = nm; b.tabIndex = 0;
    b.addEventListener("keydown", ev => { if (ev.key === "Enter" || ev.key === " "){ ev.preventDefault(); cubeTo(n); } });
    b.setAttribute("aria-label", nm.toLowerCase() + " view");
    b.innerHTML = "<span>" + nm + "</span>";
    b.addEventListener("click", ev => {
      const L = b.offsetWidth || VC_L;
      const ox = ev.offsetX, oy = ev.offsetY;
      const i = ox < L*0.28 ? -1 : ox > L*0.72 ? 1 : 0;      // left / right band
      const j = oy < L*0.28 ? 1 : oy > L*0.72 ? -1 : 0;      // top / bottom band
      cubeTo(add(n, add(scl(u, i), scl(v, j))));
    });
    vcIn.appendChild(b); VC_EL.push({b, n, u, v});
  }
}
function viewOfNormal(N){
  N = nrm(N);
  const pitch = Math.max(-1.4499, Math.min(1.4499, Math.asin(Math.max(-1, Math.min(1, N[2])))));
  const yaw = Math.abs(N[2]) > 0.999 ? -Math.PI/2 : Math.atan2(N[1], N[0]);
  return {yaw, pitch};
}
function cubeTo(N){
  clearPreset();
  if (V7.turntable) setTurntable(false);
  animate(viewOfNormal(N), V7RM() ? 0 : 420);
}
function syncCube(){
  if (!vcube || !VC_EL.length || V7.cube === false) return;
  // a phone with the sheet up has a short band of model left: the cube steps back
  const mini = sheetOpen && !wide();
  if (vcube._mini !== mini){ vcube._mini = mini; vcube.classList.toggle("mini", mini); }
  const k = cam.yaw.toFixed(4) + "," + cam.pitch.toFixed(4);
  if (k === vcKey) return;                 // pan and zoom do not turn the cube
  if (!vcKey && !VC_L) vcSize();
  vcKey = k;
  const L = VC_L;
  const V = M.look(eye(), target(), [0,0,1]);
  // world -> CSS: camera axes with y flipped (CSS y runs down)
  const C = [V[0],-V[1],V[2],0, V[4],-V[5],V[6],0, V[8],-V[9],V[10],0, 0,0,0,1];
  vcIn.style.transform = "matrix3d(" + C.map(x => +x.toFixed(5)).join(",") + ")";
  const zc = [V[2], V[6], V[10]];             // world direction toward the eye
  for (const f of VC_EL){
    const F = [f.u[0],f.u[1],f.u[2],0, -f.v[0],-f.v[1],-f.v[2],0, f.n[0],f.n[1],f.n[2],0,
               f.n[0]*L/2, f.n[1]*L/2, f.n[2]*L/2, 1];
    const key = F.join(",");
    if (f._k !== key){ f.b.style.transform = "matrix3d(" + key + ")"; f._k = key;
      f.b.style.width = f.b.style.height = L + "px"; f.b.style.margin = (-L/2) + "px 0 0 " + (-L/2) + "px"; }
    const vis = dot(f.n, zc);
    f.b.style.visibility = vis > 0.04 ? "visible" : "hidden";
    f.b.classList.toggle("on", vis > 0.985);
    // a face seen edge-on is a sliver, not a target: it stays drawn but stops being a button
    const act = vis > (matchMedia("(pointer: coarse)").matches ? 0.45 : 0.12);   // a mouse can hit a thinner face than a thumb
    if (f._act !== act){ f._act = act;
      if (act){ f.b.setAttribute("role", "button"); f.b.tabIndex = 0; f.b.removeAttribute("aria-hidden"); f.b.style.pointerEvents = ""; }
      else { f.b.removeAttribute("role"); f.b.tabIndex = -1; f.b.setAttribute("aria-hidden", "true"); f.b.style.pointerEvents = "none"; } }
  }
}
/* where a face zone sits on screen (client px) — lets the verifier click a
   real corner of the real cube instead of trusting the maths above */
function cubePoint(face, i, j){
  const f = VC_EL.find(x => x.b.dataset.face === face); if (!f) return null;
  const L = VC_L, V = M.look(eye(), target(), [0,0,1]);
  const off = add(scl(f.n, L/2), add(scl(f.u, i*L*0.38), scl(f.v, j*L*0.38)));
  const cx = V[0]*off[0]+V[4]*off[1]+V[8]*off[2], cy = V[1]*off[0]+V[5]*off[1]+V[9]*off[2];
  const r = vcube.getBoundingClientRect(), k = r.width / (vcube.offsetWidth || r.width);   // .mini scales it
  return [r.left + r.width/2 + cx*k, r.top + r.height/2 - cy*k];
}

/* ---- projection + buttons ---- */
function setOrtho(on){
  V7.ortho = !!on;
  const b = $("bOrtho"); if (b){ b.setAttribute("aria-pressed", String(V7.ortho)); b.textContent = V7.ortho ? "Ortho" : "Persp"; }
  draw();
}
$("bOrtho") && $("bOrtho").addEventListener("click", () => setOrtho(!V7.ortho));
$("bFit") && $("bFit").addEventListener("click", fitSelOrAll);
/* Reset's own glide (patched) already carries pan:[0,0,0]; a second glide here would
   supersede v6's plate / motion exits and re-zero an explode set right after */
$("bReset").addEventListener("click", () => { V7.pivot = null; if (V7.turntable) setTurntable(false); });
for (const c of document.querySelectorAll("#views .chip"))
  c.addEventListener("click", () => { if (V7.turntable) setTurntable(false); });

/* ---- turntable (R15): slow spin about the target, stops on any touch ---- */
let ttRaf = 0, ttLast = 0;
function setTurntable(on){
  V7.turntable = !!on && !V7RM();
  const b = $("bSpin"); if (b) b.setAttribute("aria-pressed", String(V7.turntable));
  cancelAnimationFrame(ttRaf);
  if (V7.turntable){ ttLast = performance.now();
    (function spin(){ if (!V7.turntable) return;
      const t = performance.now(); cam.yaw += (t - ttLast)*0.00035; ttLast = t; draw();
      ttRaf = requestAnimationFrame(spin); })(); }
}
$("bSpin") && $("bSpin").addEventListener("click", () => setTurntable(!V7.turntable));

/* ---- keys: F fit · 1/3/7 front/right/top (Ctrl = opposite) · 0 iso · 5 ortho · 9 flip ---- */
addEventListener("keydown", e => {
  if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
  const k = e.key, opp = e.ctrlKey || e.altKey;
  const go = n => { e.preventDefault(); cubeTo(opp ? scl(n, -1) : n); };
  if (k === "f" || k === "F"){ e.preventDefault(); fitSelOrAll(); }
  else if (k === "1") go([0,-1,0]);
  else if (k === "3") go([1,0,0]);
  else if (k === "7") go([0,0,1]);
  else if (k === "0"){ e.preventDefault(); clearPreset(); animate({yaw:HOME.yaw, pitch:HOME.pitch}, V7RM() ? 0 : 420); }
  else if (k === "5"){ e.preventDefault(); setOrtho(!V7.ortho); }
  else if (k === "9"){ e.preventDefault(); const {f} = camBasis(); cubeTo(f); }
});

/* ===========================================================================
   R11 — VIEWPORT LOOK: materials, silhouette + crease edges, contact shadow
   =========================================================================== */
const FIN = {                   // [specular, shininess, metal, sheen]
  matte:   [0.07, 10, 0, 0],    // PLA: chalky, almost no highlight
  gloss:   [0.34, 46, 0, 0],    // PETG: a tight, wet-looking highlight
  satin:   [0.12,  7, 0, 0.55], // TPU / wire jackets: broad soft sheen at grazing angles
  plastic: [0.24, 30, 0, 0],    // bought moulded parts
  steel:   [0.80, 70, 1, 0],    // screws, bearings, shafts
  brass:   [0.85, 52, 1, 0],    // heat-set inserts
  metal:   [0.45, 24, 0.6, 0],  // painted / cast motor cans
};
const matCache = new Map();
function matOf(p){
  let m = matCache.get(p.id); if (m) return m;
  const fin = String(p.finish || "").toLowerCase();
  const mat = String(p.material || "").toUpperCase();
  const txt = (p.id + " " + (p.label || "")).toLowerCase();
  let k;
  if (fin && FIN[fin]) k = fin;
  else if (p.kind === "screw") k = "steel";
  else if (/insert|brass/.test(txt)) k = "brass";
  else if (p.kind === "wire") k = "satin";
  else if (p.kind === "printed") k = mat === "PETG" ? "gloss" : mat === "TPU" ? "satin" : "matte";
  else if (/bearing|608|6[0-9]{2}zz|shaft|rail|mgn|screw|nut|bolt|washer|spring|steel|rod\b/.test(txt)) k = "steel";
  else if (/motor|stepper|nema|28byj|gearmotor/.test(txt)) k = "metal";
  else k = "plastic";
  m = new Float32Array(FIN[k]); m.kind = k; matCache.set(p.id, m); return m;
}

const NFS = `#version 300 es
precision highp float;
in vec3 vP; in vec3 vW;
uniform vec4 uClip; uniform float uClipOn, uId;
out vec4 o;
void main(){
  if (uClipOn > 0.5 && dot(vW, uClip.xyz) > uClip.w) discard;
  vec3 n = normalize(cross(dFdx(vP), dFdy(vP)));
  if (!gl_FrontFacing) n = -n;
  o = vec4(n*0.5 + 0.5, uId);
}`;
const QVS = `#version 300 es
void main(){
  vec2 p = vec2(gl_VertexID == 1 ? 3.0 : -1.0, gl_VertexID == 2 ? 3.0 : -1.0);
  gl_Position = vec4(p, 0.0, 1.0);
}`;
/* CAD edge lines from the frame itself: silhouette = depth jump or the model
   meeting the background, crease = facet normals > ~40° apart, and a line
   wherever two different parts touch (coplanar faces of two parts still get
   a seam, which is how a CAD viewport shows an assembly). One line per edge:
   only the NEARER pixel of a pair draws it. */
const EFS = `#version 300 es
precision highp float;
uniform sampler2D uN; uniform highp sampler2D uD;
uniform float uNear, uFar, uOrtho; uniform int uK;
uniform vec4 uInk;
out vec4 o;
float lin(float d){ float z = d*2.0 - 1.0;
  return uOrtho > 0.5 ? 0.5*(z*(uFar-uNear) + (uFar+uNear))
                      : 2.0*uNear*uFar / (uFar + uNear - z*(uFar-uNear)); }
void main(){
  ivec2 p = ivec2(gl_FragCoord.xy);
  ivec2 sz = textureSize(uD, 0) - 1;
  float dc = texelFetch(uD, p, 0).r;
  if (dc >= 1.0) discard;                       // background never draws a line
  vec4 nc = texelFetch(uN, p, 0);
  vec3 n0 = nc.xyz*2.0 - 1.0;
  float lc = lin(dc), e = 0.0;
  ivec2 Q[4] = ivec2[4](ivec2(uK,0), ivec2(-uK,0), ivec2(0,uK), ivec2(0,-uK));
  for (int i = 0; i < 4; i++){
    ivec2 q = clamp(p + Q[i], ivec2(0), sz);
    float dn = texelFetch(uD, q, 0).r;
    if (dn >= 1.0){ e = 1.0; continue; }        // the outline against the stage
    vec4 nn = texelFetch(uN, q, 0);
    float ln = lin(dn);
    float tol = (0.012*lc + 0.35) / max(abs(n0.z), 0.18);   // grazing faces change depth fast: allow it
    if (ln - lc > tol) e = max(e, 1.0);         // I am in front of a jump: silhouette
    if (abs(nc.a - nn.a) > 0.002 && ln >= lc) e = max(e, 0.8);   // seam between two parts
    if (dot(n0, nn.xyz*2.0 - 1.0) < 0.76 && ln >= lc - tol) e = max(e, 0.62);   // crease
  }
  if (e <= 0.0) discard;
  o = vec4(uInk.rgb, uInk.a*e);
}`;
const SFS = `#version 300 es
precision highp float;
in vec3 vP; in vec3 vW;
uniform float uG, uH;
out vec4 o;
void main(){ o = vec4(vec3(clamp(1.0 - (vW.z - uG)/uH, 0.0, 1.0)), 1.0); }`;
const GVS = `#version 300 es
in vec3 aP; uniform mat4 uMVP; uniform vec4 uBox; out vec2 vUV;
void main(){ vUV = (aP.xy - uBox.xy)/uBox.zw*0.5 + 0.5; gl_Position = uMVP*vec4(aP,1.0); }`;
const GFS = `#version 300 es
precision highp float;
in vec2 vUV; uniform sampler2D uS; uniform float uA; uniform vec3 uC;
out vec4 o;
void main(){
  float s = texture(uS, vUV).r;              // already blurred, once, when the model last moved
  vec2 d = abs(vUV - 0.5)*2.0;
  float fade = 1.0 - smoothstep(0.62, 1.0, max(d.x, d.y));
  float a = s*uA*fade;
  if (a < 0.004) discard;
  o = vec4(uC, a);
}`;
/* separable 9-tap Gaussian, run twice (x then y) into the second shadow texture:
   a contact shadow is soft because the light is big, not because it is far */
const BFS = `#version 300 es
precision highp float;
uniform sampler2D uS; uniform vec2 uDir;
out vec4 o;
void main(){
  vec2 px = 1.0/vec2(textureSize(uS,0)), uv = gl_FragCoord.xy*px;
  float w[5] = float[5](0.227, 0.194, 0.121, 0.054, 0.016);
  float s = texture(uS, uv).r*w[0];
  for (int i = 1; i < 5; i++){
    s += texture(uS, uv + uDir*px*float(i)*3.2).r*w[i];
    s += texture(uS, uv - uDir*px*float(i)*3.2).r*w[i];
  }
  o = vec4(vec3(s), 1.0);
}`;
let GX = null;                    // v7 GL objects, created lazily
function v7GL(){
  if (GX || !gl) return GX;
  GX = {};
  GX.nprog = link(VS, NFS, "aQ"); GX.eprog = link(QVS, EFS, "aQ");
  GX.sprog = link(VS, SFS, "aQ"); GX.gprog = link(GVS, GFS, "aP");
  GX.nu = {}; for (const k of ["uMVP","uMV","uModel","uLo","uSpan","uClip","uClipOn","uId"]) GX.nu[k] = gl.getUniformLocation(GX.nprog, k);
  GX.eu = {}; for (const k of ["uN","uD","uNear","uFar","uOrtho","uK","uInk"]) GX.eu[k] = gl.getUniformLocation(GX.eprog, k);
  GX.su = {}; for (const k of ["uMVP","uMV","uModel","uLo","uSpan","uG","uH"]) GX.su[k] = gl.getUniformLocation(GX.sprog, k);
  GX.gu = {}; for (const k of ["uMVP","uBox","uS","uA","uC"]) GX.gu[k] = gl.getUniformLocation(GX.gprog, k);
  GX.bprog = link(QVS, BFS, "aQ");
  GX.bu = {uS: gl.getUniformLocation(GX.bprog, "uS"), uDir: gl.getUniformLocation(GX.bprog, "uDir")};
  GX.evao = gl.createVertexArray();
  GX.gvbo = gl.createBuffer(); GX.gvao = gl.createVertexArray();
  gl.bindVertexArray(GX.gvao); gl.bindBuffer(gl.ARRAY_BUFFER, GX.gvbo);
  gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0,3,gl.FLOAT,false,12,0);
  gl.bindVertexArray(vao);
  // edge target: facet normal + part id, and a sampleable depth texture
  GX.efb = gl.createFramebuffer(); GX.ntex = gl.createTexture(); GX.dtex = gl.createTexture(); GX.ew = 0; GX.eh = 0;
  // shadow target: a 256² height map seen from under the ground plane
  GX.sfb = gl.createFramebuffer(); GX.stex = gl.createTexture(); GX.srb = gl.createRenderbuffer();
  gl.bindTexture(gl.TEXTURE_2D, GX.stex);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 256, 256, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
  for (const [k,v] of [[gl.TEXTURE_MIN_FILTER,gl.LINEAR],[gl.TEXTURE_MAG_FILTER,gl.LINEAR],
                       [gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE],[gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE]]) gl.texParameteri(gl.TEXTURE_2D,k,v);
  gl.bindRenderbuffer(gl.RENDERBUFFER, GX.srb);
  gl.renderbufferStorage(gl.RENDERBUFFER, gl.DEPTH_COMPONENT16, 256, 256);
  gl.bindFramebuffer(gl.FRAMEBUFFER, GX.sfb);
  gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, GX.stex, 0);
  gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.RENDERBUFFER, GX.srb);
  // ping-pong target for the blur
  GX.bfb = gl.createFramebuffer(); GX.btex = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, GX.btex);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 256, 256, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
  for (const [k,v] of [[gl.TEXTURE_MIN_FILTER,gl.LINEAR],[gl.TEXTURE_MAG_FILTER,gl.LINEAR],
                       [gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE],[gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE]]) gl.texParameteri(gl.TEXTURE_2D,k,v);
  gl.bindFramebuffer(gl.FRAMEBUFFER, GX.bfb);
  gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, GX.btex, 0);
  gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  GX.skey = ""; GX.sbox = null;
  return GX;
}
function edgeTargets(w, h){
  if (GX.ew === w && GX.eh === h) return;
  GX.ew = w; GX.eh = h;
  gl.bindTexture(gl.TEXTURE_2D, GX.ntex);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
  gl.bindTexture(gl.TEXTURE_2D, GX.dtex);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.DEPTH_COMPONENT24, w, h, 0, gl.DEPTH_COMPONENT, gl.UNSIGNED_INT, null);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
  gl.bindFramebuffer(gl.FRAMEBUFFER, GX.efb);
  gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, GX.ntex, 0);
  gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.TEXTURE_2D, GX.dtex, 0);
  gl.bindFramebuffer(gl.FRAMEBUFFER, null);
}
/* Called from draw() between the solid pass and the ghost pass. Skipped while
   a hand is on the model (drag, pinch, wheel, the fps bench): the same rule
   as the resolution tuner — spend fill rate on the still frame you study, not
   on the frames you barely see. endInteract() redraws one crisp frame with
   the lines 90 ms after you let go. */
function v7Edges(MVP, V, w, h, clip){
  if (!V7.edges || wireMode || !v7GL()) return;
  if (interacting) { V7.edgeSkipped = (V7.edgeSkipped||0) + 1; return; }
  edgeTargets(w, h);
  gl.bindFramebuffer(gl.FRAMEBUFFER, GX.efb);
  gl.viewport(0, 0, w, h);
  gl.clearColor(0.5, 0.5, 1.0, 0); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
  gl.useProgram(GX.nprog); gl.bindVertexArray(vao);
  gl.uniformMatrix4fv(GX.nu.uMVP, false, new Float32Array(MVP));
  gl.uniformMatrix4fv(GX.nu.uMV, false, new Float32Array(V));
  gl.uniform4fv(GX.nu.uClip, new Float32Array(clip.v)); gl.uniform1f(GX.nu.uClipOn, clip.on);
  for (const p of parts){
    if (state(p) !== "solid" || p.kind === "wire") continue;
    gl.uniform3fv(GX.nu.uLo, new Float32Array(p.lo)); gl.uniform3fv(GX.nu.uSpan, new Float32Array(p.span));
    gl.uniform1f(GX.nu.uId, ((p.idx*37) % 251 + 2)/255);
    for (const m of instancesOf(p)){ gl.uniformMatrix4fv(GX.nu.uModel, false, new Float32Array(m)); gl.drawArrays(gl.TRIANGLES, p.off/6, p.n); }
  }
  gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  gl.viewport(0, 0, w, h);
  gl.useProgram(GX.eprog); gl.bindVertexArray(GX.evao);
  gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, GX.ntex);
  gl.activeTexture(gl.TEXTURE2); gl.bindTexture(gl.TEXTURE_2D, GX.dtex);
  gl.activeTexture(gl.TEXTURE0);
  gl.uniform1i(GX.eu.uN, 1); gl.uniform1i(GX.eu.uD, 2);
  gl.uniform1f(GX.eu.uNear, V7.ortho ? -(Math.max(plateMode ? 4000 : 2000, dist()*2 + _bb*12)) : 1);
  gl.uniform1f(GX.eu.uFar, V7.ortho ? Math.max(plateMode ? 4000 : 2000, dist()*2 + _bb*12) : (plateMode ? 4000 : 2000));
  gl.uniform1f(GX.eu.uOrtho, V7.ortho ? 1 : 0);
  gl.uniform1i(GX.eu.uK, Math.max(1, Math.round(curDpr*0.75)));
  const ink = hex(cssVar("--edge") || "#06090a");
  gl.uniform4fv(GX.eu.uInk, new Float32Array([ink[0], ink[1], ink[2], +(cssVar("--edge-a") || 0.7)]));
  gl.disable(gl.DEPTH_TEST); gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
  gl.drawArrays(gl.TRIANGLES, 0, 3);
  gl.disable(gl.BLEND); gl.enable(gl.DEPTH_TEST);
  gl.useProgram(prog); gl.bindVertexArray(vao);
}
/* Soft contact shadow: render every solid part from UNDER the ground plane
   into a 256² height map (nearest-to-ground wins the depth test, and lower =
   darker), blur it on a ground quad. Re-rendered only when something moved
   relative to the ground — orbiting reuses it, so it costs nothing to spin. */
function v7Shadow(MVP){
  if (!V7.shadow || plateMode || wireMode || !v7GL()) return;
  const sol = parts.filter(p => state(p) === "solid" && p.kind !== "wire");
  if (!sol.length) return;
  let key = sol.length;                   // a cheap fingerprint of every solid part's pose
  for (const p of sol) for (const m of instancesOf(p))
    key = (key*31 + Math.round((m[12]+m[13]*3+m[14]*7+m[0]*11+m[5]*13+m[10]*17+m[4]*19)*100)) % 2147483647;
  if (key !== GX.skey){
    GX.skey = key;
    const b = v7Box(sol);
    const cx = (b.lo[0]+b.hi[0])/2, cy = (b.lo[1]+b.hi[1])/2;
    const R = Math.max(b.hi[0]-b.lo[0], b.hi[1]-b.lo[1])*0.5*1.45 + _bb*0.12;
    const g = b.lo[2], top = b.hi[2] + 1, H = Math.max(6, (b.hi[2]-b.lo[2])*0.35);
    GX.sbox = {cx, cy, R, g};
    // x,y -> ndc by the footprint; z -> depth, ground at the near plane
    const S = [1/R,0,0,0, 0,1/R,0,0, 0,0,2/(top-g+1),0, -cx/R,-cy/R,-2*(g-0.5)/(top-g+1)-1,1];
    gl.bindFramebuffer(gl.FRAMEBUFFER, GX.sfb); gl.viewport(0, 0, 256, 256);
    gl.clearColor(0,0,0,0); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.disable(gl.CULL_FACE);
    gl.useProgram(GX.sprog); gl.bindVertexArray(vao);
    gl.uniformMatrix4fv(GX.su.uMVP, false, new Float32Array(S)); gl.uniformMatrix4fv(GX.su.uMV, false, new Float32Array(IDENT));
    gl.uniform1f(GX.su.uG, g); gl.uniform1f(GX.su.uH, H);
    for (const p of sol){
      gl.uniform3fv(GX.su.uLo, new Float32Array(p.lo)); gl.uniform3fv(GX.su.uSpan, new Float32Array(p.span));
      for (const m of instancesOf(p)){ gl.uniformMatrix4fv(GX.su.uModel, false, new Float32Array(m)); gl.drawArrays(gl.TRIANGLES, p.off/6, p.n); }
    }
    // blur: stex -> btex (x), btex -> stex (y)
    gl.disable(gl.DEPTH_TEST);
    gl.useProgram(GX.bprog); gl.bindVertexArray(GX.evao); gl.uniform1i(GX.bu.uS, 3);
    gl.activeTexture(gl.TEXTURE3);
    gl.bindFramebuffer(gl.FRAMEBUFFER, GX.bfb); gl.bindTexture(gl.TEXTURE_2D, GX.stex);
    gl.uniform2f(GX.bu.uDir, 1, 0); gl.drawArrays(gl.TRIANGLES, 0, 3);
    gl.bindFramebuffer(gl.FRAMEBUFFER, GX.sfb); gl.bindTexture(gl.TEXTURE_2D, GX.btex);
    gl.uniform2f(GX.bu.uDir, 0, 1); gl.drawArrays(gl.TRIANGLES, 0, 3);
    gl.activeTexture(gl.TEXTURE0);
    gl.enable(gl.DEPTH_TEST);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.enable(gl.CULL_FACE);
    const [w, h] = [cv.width, cv.height]; gl.viewport(0, 0, w, h);
  }
  const {cx, cy, R, g} = GX.sbox, z = g - 0.15;
  gl.useProgram(GX.gprog); gl.bindVertexArray(GX.gvao);
  gl.bindBuffer(gl.ARRAY_BUFFER, GX.gvbo);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([cx-R,cy-R,z, cx+R,cy-R,z, cx+R,cy+R,z, cx-R,cy-R,z, cx+R,cy+R,z, cx-R,cy+R,z]), gl.DYNAMIC_DRAW);
  gl.uniformMatrix4fv(GX.gu.uMVP, false, new Float32Array(MVP));
  gl.uniform4fv(GX.gu.uBox, new Float32Array([cx, cy, R, R]));
  gl.activeTexture(gl.TEXTURE3); gl.bindTexture(gl.TEXTURE_2D, GX.stex); gl.uniform1i(GX.gu.uS, 3); gl.activeTexture(gl.TEXTURE0);
  gl.uniform1f(GX.gu.uA, +(cssVar("--shadow-a") || 0.5));
  gl.uniform3fv(GX.gu.uC, new Float32Array(hex(cssVar("--shadow-c") || "#000000")));
  gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
  gl.depthMask(false); gl.disable(gl.CULL_FACE);
  gl.drawArrays(gl.TRIANGLES, 0, 6);
  gl.depthMask(true); gl.disable(gl.BLEND); gl.enable(gl.CULL_FACE);
  gl.useProgram(prog); gl.bindVertexArray(vao);
}
function v7Uniforms(V){
  gl.uniform3fv(uni.uUpV, new Float32Array(nrm([V[8], V[9], V[10]])));
  gl.uniform1f(uni.uOrtho, V7.ortho ? 1 : 0);
}
$("bEdge") && $("bEdge").addEventListener("click", () => {
  V7.edges = !V7.edges; $("bEdge").setAttribute("aria-pressed", String(V7.edges)); draw(); });

/* ===========================================================================
   R12 — ANIMATED BUILD STEPS
   Entering parts fly in along part.insert {dir, dist} (default: their explode
   vector), screws drive in along their axis while turning, nuts thread on from
   the far side. u runs 0 → 1; at u = 1 every matrix is EXACTLY the assembled
   one (the animation returns the untouched base matrix), which the verifier
   checks bit-for-bit.
   =========================================================================== */
let SA = null;                  // {n, t0, dur, u, paused, keys, raf}
V7.onStepEnd = null;
function stepKeys(n){
  const ent = parts.filter(p => p.step === n && p.kind !== "wire");
  const scr = ent.filter(p => p.kind === "screw" && p.screw && p.screw.axis);
  const oth = ent.filter(p => !scr.includes(p));
  const keys = new Map();
  const hasS = scr.length > 0, hasO = oth.length > 0;
  oth.forEach((p, i) => {
    const span = hasS ? 0.55 : 1;
    const st = Math.min(0.25, 0.07*i) * span;
    let dir, d;
    if (p.insert && p.insert.dir){ dir = nrm(p.insert.dir); d = +p.insert.dist || 30; }
    else {
      const e = p.explode || [0,0,0], L = Math.hypot(e[0], e[1], e[2]);
      if (L > 1e-6){ dir = scl(e, 1/L); d = Math.max(18, L*EXK*1.25); }
      else { dir = [0,0,1]; d = Math.max(12, _bb*0.25); }
    }
    keys.set(p.id, {t0: st, t1: span, off: scl(dir, d), screw: false});
  });
  scr.forEach((p, i) => {
    const K = scr.length, w = Math.min(0.55, hasO ? 0.5 : 0.7);
    const a = hasO ? 0.42 : 0, b = 1 - w;
    const t0 = K > 1 ? a + (b - a)*i/(K - 1) : a + (b - a)/2;
    const sc = p.screw, nut = sc.role === "nut";
    const L = (sc.len || 8) + 6;
    keys.set(p.id, {t0, t1: t0 + w, screw: true, axis: nrm(sc.axis), at: sc.at || [0,0,0],
                    off: scl(nrm(sc.axis), (nut ? 1 : -1)*L),
                    turns: (nut ? -1 : 1) * Math.min(6, Math.max(2, (sc.len || 8)/3))});
  });
  return keys;
}
function stepAnimM(p, base){
  if (!SA || SA.u >= 1 || V7.noAnim || !stepMode || plateMode || wireMode || motionMode || p.step !== SA.n) return base;
  const k = SA.keys.get(p.id); if (!k) return base;
  const u = clamp01((SA.u - k.t0)/Math.max(1e-6, k.t1 - k.t0));
  if (u >= 1) return base;
  if (!k.screw){ const e = 1 - ease3(u); return M.mul(base, M.trans(scl(k.off, e))); }
  const e = 1 - easeOut(u);
  const m = M.mul(base, M.trans(scl(k.off, e)));
  return v7RotAbout(m, k.at, k.axis, -e*k.turns*2*Math.PI);
}
function stepDur(keys){
  let ns = 0, no = 0; for (const k of keys.values()) k.screw ? ns++ : no++;
  return Math.min(2000, 900 + 160*Math.min(ns, 6) + 120*Math.min(no, 4));
}
function startStepAnim(n){
  cancelAnimationFrame(SA && SA.raf);
  const keys = stepKeys(n);
  SA = {n, t0: performance.now(), dur: V7RM() ? 0 : stepDur(keys), u: 0, paused: false, keys, raf: 0};
  if (!keys.size || SA.dur === 0){ SA.u = 1; draw(); saSync(); endStep(); return; }
  tickStep();
}
function tickStep(){
  if (!SA || SA.paused) return;
  SA.u = clamp01((performance.now() - SA.t0)/SA.dur);
  draw(); saSync();
  if (SA.u < 1) SA.raf = requestAnimationFrame(tickStep);
  else endStep();
}
function endStep(){ const f = V7.onStepEnd; if (f) f(); }
function saPause(){ if (!SA || SA.u >= 1) return; SA.paused = true; cancelAnimationFrame(SA.raf); saSync(); }
function saResume(){ if (!SA) return;
  if (SA.u >= 1){ startStepAnim(SA.n); return; }
  SA.paused = false; SA.t0 = performance.now() - SA.u*SA.dur; tickStep(); }
function saScrub(u){ if (!SA) startStepAnim(step);
  SA.paused = true; cancelAnimationFrame(SA.raf); SA.u = clamp01(u); draw(); saSync(); }
function saSync(){
  const r = $("saScrub"), b = $("saPlay");
  if (r && SA) r.value = Math.round(SA.u*1000);
  if (b) b.textContent = (SA && !SA.paused && SA.u < 1) ? "❚❚" : "▷";
  if (b) b.setAttribute("aria-label", (SA && !SA.paused && SA.u < 1) ? "Pause this step" : "Play this step");
}
renderStep = (orig => function(){
  orig();
  if (stepMode){
    if (!V7.noAnim) startStepAnim(step);
    if (focus) glide({dist: focus.d, pan: [0,0,0]});
  }
})(renderStep);
showBuild = (orig => function(){
  orig();
  const w = $("tl"); if (!w) return;
  if (playBtn){ playBtn.setAttribute("aria-label", "Play whole build"); playBtn.title = "Play whole build"; }
  const bar = el("div", "sabar");
  const pb = el("button", "btn", "▷"); pb.id = "saPlay";
  pb.addEventListener("click", () => (SA && !SA.paused && SA.u < 1) ? saPause() : saResume());
  const rg = document.createElement("input"); rg.type = "range"; rg.id = "saScrub";
  rg.min = 0; rg.max = 1000; rg.value = SA ? Math.round(SA.u*1000) : 1000;
  rg.setAttribute("aria-label", "Scrub this step");
  rg.addEventListener("input", () => { stopPlay(); saScrub(+rg.value/1000); });
  const rp = el("button", "btn", "↺"); rp.setAttribute("aria-label", "Replay this step");
  rp.addEventListener("click", () => { stopPlay(); startStepAnim(step); });
  bar.append(pb, rg, rp);
  const tlbar = w.querySelector(".tlbar"); tlbar.after(bar);
  saSync();
})(showBuild);
startPlay = function(){
  playing = true; if (playBtn) playBtn.textContent = "❚❚";
  if (step >= NSTEP) step = 1;
  V7.onStepEnd = () => {
    if (!playing) return;
    clearTimeout(playTimer);
    playTimer = setTimeout(() => {
      if (!playing) return;
      if (step >= NSTEP){ stopPlay(); return; }
      gotoStep(step + 1);
    }, V7RM() ? 1800 : 480);
  };
  renderStep();
};
/* entering plates or the wiring view re-centres: the pan belongs to the view you left */
setPlateMode = (orig => function(on){ V7.panNext = [0,0,0]; orig(on); V7.panNext = null; })(setPlateMode);
setWireMode  = (orig => function(on){ V7.panNext = [0,0,0]; orig(on); V7.panNext = null; })(setWireMode);
stopPlay = (orig => function(){ orig(); V7.onStepEnd = null; })(stopPlay);
/* the printed build sheet keeps STATIC renders: no fly-in, no pan, no ortho */
buildSheet = (orig => async function(btn, noPrint){
  const keep = {pan: PAN.slice(), ortho: V7.ortho, noAnim: V7.noAnim, tt: V7.turntable};
  V7.noAnim = true; V7.ortho = false; PAN[0] = PAN[1] = PAN[2] = 0; if (V7.turntable) setTurntable(false);
  try { return await orig(btn, noPrint); }
  finally { V7.noAnim = keep.noAnim; V7.ortho = keep.ortho; for (let i=0;i<3;i++) PAN[i] = keep.pan[i]; draw(); }
})(buildSheet);

/* ===========================================================================
   R13 — DETAILED WIRING
   Pinouts in pin order with real lead colours; connector per end; gauge /
   current / drop chips per run; a power budget and a common-ground check;
   current-flow animation on the 3D tube and the schematic edge while tracing.
   Colour of every conductor comes from, in order: pin.color / pin.wires
   (config) → a colour word in the pin label → the part library below →
   wiring convention (power red, ground black) → "unset", shown as unset.
   =========================================================================== */
const WCOL = {brown:"#7a4a26", brn:"#7a4a26", red:"#d1302a", orange:"#f08a1c", org:"#f08a1c",
  yellow:"#f2cd1a", yel:"#f2cd1a", green:"#2e9b45", grn:"#2e9b45", blue:"#2f6fd8", blu:"#2f6fd8",
  purple:"#8a4fd1", violet:"#8a4fd1", grey:"#8b9096", gray:"#8b9096", white:"#f3f3f0", wht:"#f3f3f0",
  black:"#1b1b1b", blk:"#1b1b1b", pink:"#f08bb4"};
const WRE = new RegExp("\\b(" + Object.keys(WCOL).join("|") + ")\\b", "gi");
const LIB = [   // [node label regex, connector, [[conductor role regex, label, colour]…]]
  [/\b(sg90|mg90s?|mg996r?|ds3218|servo)\b/i, "JR servo 3-pin · 2.54 mm",
    [[/gnd|ground|−|-ve/i, "GND", "brown"], [/\+5|5v|vcc|\+v|v\+|pwr/i, "+5 V", "red"], [/sig|pwm|signal|ctl/i, "SIG", "orange"]]],
  [/28byj/i, "JST-XH 5-pin · 2.5 mm",
    [[/^a$|in1|coil a|blue/i, "A", "blue"], [/^b$|in2|pink/i, "B", "pink"], [/^c$|in3|yellow/i, "C", "yellow"], [/^d$|in4|orange/i, "D", "orange"], [/com|\+5|red/i, "COM +5 V", "red"]]],
  [/\bpot|potentiometer/i, "Solder joints ×3",
    [[/end ?a|outer ?1|^1$/i, "END 1", null], [/wiper|middle|^2$/i, "WIPER", null], [/end ?b|outer ?2|^3$/i, "END 2", null]]],
];
const CONN = [
  [/sg90|mg90|mg996|servo/i, "JR servo 3-pin · 2.54 mm"], [/28byj/i, "JST-XH 5-pin"],
  [/uln2003/i, "2.54 mm header + JST-XH socket"], [/\b(uno|arduino|nano|mega|esp32|esp8266|pico|teensy)\b/i, "Dupont 2.54 mm header"],
  [/breadboard|\brail\b/i, "Breadboard 2.54 mm"], [/charger|usb/i, "USB lead · cut + soldered"],
  [/psu|supply|adapter|brick|batter/i, "Screw terminal"], [/e-?stop|switch|relay|terminal/i, "Screw terminal"],
  [/button|door/i, "Dupont / solder tab"], [/pot|hall|sensor/i, "Solder joint"],
  [/gland/i, "Cable gland · pass-through"], [/driver|h-bridge|bridge/i, "Screw terminal + 2.54 mm header"],
  [/motor|gearmotor/i, "Solder tabs"],
];
const nodeConn = n => n.connector || (CONN.find(([re]) => re.test(n.label + " " + n.id)) || [0, null])[1];
function libOf(n){ return LIB.find(([re]) => re.test(n.label + " " + n.id)) || null; }
function colourOf(word){ return word ? (WCOL[String(word).toLowerCase()] || (String(word)[0] === "#" ? word : null)) : null; }
/* the conductors behind one pin, in order: [{label, color, colName, src}] */
function conductors(n, pn){
  const lib = libOf(n), out = [];
  const fromLib = lab => { if (!lib) return null; const hit = lib[2].find(([re]) => re.test(lab)); return hit ? hit : null; };
  if (Array.isArray(pn.wires)) return pn.wires.map(w => ({label: w.label || pn.label, colName: w.color || null,
    color: colourOf(w.color), src: w.color ? "config" : "unset"}));
  if (Array.isArray(pn.color)) return pn.color.map((c, i) => ({label: pn.label + " " + (i+1), colName: c, color: colourOf(c), src: "config"}));
  if (pn.color) return [{label: pn.label, colName: pn.color, color: colourOf(pn.color), src: "config"}];
  const lab = String(pn.label || pn.id);
  // "pot pads ×3", "3 pins": one conductor per pad, named by the library when it knows the part
  const mN = lab.match(/[×x]\s*(\d)|(\d)\s*pins?\b/i);
  const nN = mN ? +(mN[1] || mN[2]) : 0;
  if (nN > 1){
    const potLib = /pot/i.test(lab + " " + n.label) ? LIB[2] : lib;
    for (let i = 0; i < nN; i++){
      const r = potLib && potLib[2][i];
      out.push({label: r ? r[1] : "#" + (i+1), color: null, colName: null, src: "unset"});
    }
    return out;
  }
  // "+5V red/GND brn": one pin label carrying a pair
  const segs = /\//.test(lab) ? lab.split("/") : [lab];
  for (const sgm of segs){
    const words = sgm.match(WRE);
    const name = sgm.replace(WRE, "").trim() || sgm.trim();
    if (words){ out.push({label: name, colName: words[0].toLowerCase(), color: colourOf(words[0]), src: "label"}); continue; }
    const L = fromLib(name);
    if (L && L[2]){ out.push({label: L[1], colName: L[2], color: colourOf(L[2]), src: "library"}); continue; }
    if (/gnd|ground/i.test(name) || pn.kind === "ground"){ out.push({label: name, colName: "black", color: WCOL.black, src: "convention"}); continue; }
    if (pn.kind === "power" && segs.length === 1){ out.push({label: name, colName: "red", color: WCOL.red, src: "convention"}); continue; }
    if (/^\+|v\b|vcc|vin/i.test(name)){ out.push({label: name, colName: "red", color: WCOL.red, src: "convention"}); continue; }
    out.push({label: name, color: null, colName: null, src: "unset"});
  }
  return out;
}
function pinsInOrder(n){
  return (n.pins || []).map((p, i) => ({p, o: p.order != null ? +p.order : i + 1})).sort((a, b) => a.o - b.o);
}
/* where each end of a run goes, and on what connector */
function runEnd(r, which){
  const ref = which === "from" ? r.from : r.to;
  const [nid, pid] = endRef(ref), n = nodeById.get(nid) || {label: nid, id: nid};
  const e = (r.ends && r.ends[which]) || {};
  return {n, pid, connector: e.connector || nodeConn(n) || null, color: e.color || null};
}
/* supply, loads, headroom and the ground net */
function powerBudget(){
  const pw = RUNS.filter(r => r.kind === "power");
  const deg = new Map();
  for (const r of pw) for (const ref of [r.from, r.to]){ const id = endRef(ref)[0]; deg.set(id, (deg.get(id)||0) + 1); }
  const sup = NODES.find(n => n.supply) ||
              NODES.find(n => /psu|supply|charger|adapter|brick|batter|wall/i.test(n.id + " " + n.label));
  let rating = null, volts = WIRING ? WIRING.volts : null;
  if (sup){
    if (sup.supply && sup.supply.amps) rating = +sup.supply.amps;
    if (sup.supply && sup.supply.volts) volts = +sup.supply.volts;
    if (rating == null){ const m = (sup.label + " " + (sup.role || "")).match(/(\d+(?:\.\d+)?)\s*A\b/); if (m) rating = +m[1]; }
  }
  const loads = [];
  const seen = new Set();
  for (const n of NODES) if (n !== sup && n.stall_a != null){ loads.push({node: n, amps: +n.stall_a, src: "stall_a"}); seen.add(n.id); }
  for (const r of pw){
    for (const ref of [r.from, r.to]){
      const id = endRef(ref)[0], n = nodeById.get(id);
      if (!n || n === sup || seen.has(id) || deg.get(id) !== 1) continue;
      loads.push({node: n, amps: +r.amps || 0, src: "run " + r.id}); seen.add(id);
    }
  }
  const total = loads.reduce((a, l) => a + l.amps, 0);
  // ground: every node with a ground pin, and every load, must reach the supply's ground
  const par = new Map(NODES.map(n => [n.id, n.id]));
  const find = x => { while (par.get(x) !== x){ par.set(x, par.get(par.get(x))); x = par.get(x); } return x; };
  const join = (a, b) => { if (par.has(a) && par.has(b)) par.set(find(a), find(b)); };
  for (const r of RUNS){
    const gnd = r.kind === "ground" || /gnd|ground/i.test(r.net || "") || (r.kind === "power" && (r.conductors || 1) >= 2);
    if (gnd) join(endRef(r.from)[0], endRef(r.to)[0]);
  }
  const need = NODES.filter(n => (n.pins || []).some(p => p.kind === "ground") || loads.some(l => l.node === n));
  const root = sup ? find(sup.id) : (need[0] ? find(need[0].id) : null);
  const missing = root == null ? [] : need.filter(n => find(n.id) !== root);
  const pct = rating ? total/rating : null;
  return {sup, rating, volts, loads, total, pct,
          status: pct == null ? "warn" : pct <= 0.8 ? "pass" : pct <= 1 ? "warn" : "fail",
          ground: {ok: !missing.length && !!sup, n: need.length, missing}};
}
/* which way current (or the signal) flows along a run */
const CTRL = /\b(uno|arduino|nano|mega|esp32|esp8266|pico|teensy|mcu|controller|driver|uln2003|h-bridge)\b/i;
function flowDir(r){
  if (r.dir === "from" || r.dir === "to") return r.dir === "to" ? 1 : -1;    // config override: +1 = from → to
  const [a] = endRef(r.from), [b] = endRef(r.to);
  if (r.kind === "power" || r.kind === "ground"){
    const pb = powerBudget(); if (!pb.sup) return 1;
    // breadth-first distance from the supply over every run
    const dd = new Map([[pb.sup.id, 0]]), q = [pb.sup.id];
    while (q.length){ const x = q.shift();
      for (const s of RUNS){ const [u] = endRef(s.from), [v] = endRef(s.to);
        for (const [p1, p2] of [[u, v], [v, u]]) if (p1 === x && !dd.has(p2)){ dd.set(p2, dd.get(x) + 1); q.push(p2); } } }
    const da = dd.has(a) ? dd.get(a) : 99, db = dd.has(b) ? dd.get(b) : 99;
    const out = da <= db ? 1 : -1;                      // +V flows away from the supply
    return r.kind === "ground" ? -out : out;            // the return comes back to it
  }
  const na = nodeById.get(a), nb = nodeById.get(b);
  if (na && CTRL.test(na.label + " " + na.id) && !(nb && CTRL.test(nb.label + " " + nb.id))) return 1;
  if (nb && CTRL.test(nb.label + " " + nb.id) && !(na && CTRL.test(na.label + " " + na.id))) return -1;
  return 1;
}
showWire = (orig => function(){
  orig();
  if (!RUNS.length) return;
  const kp = shBody.querySelector(".kpis");
  /* power budget: one bar, load segments against the supply rating, an 80 % line */
  const pb = powerBudget();
  const card = el("div", "pbud " + pb.status); card.id = "pBudget";
  const head = el("div", "pbh");
  head.appendChild(el("span", "pbg", pb.status === "pass" ? "✓" : pb.status === "fail" ? "✗" : "!"));
  head.appendChild(el("span", "pbt", "Power budget"));
  head.appendChild(el("span", "pbv", pb.rating ? `${pb.total.toFixed(2)} / ${pb.rating} A · ${Math.round(pb.pct*100)} %`
                                                : `${pb.total.toFixed(2)} A · supply rating not set`));
  card.appendChild(head);
  const track = el("div", "pbtrack"), full = Math.max(pb.rating || 0, pb.total, 0.001);
  for (const l of pb.loads){
    const s = el("div", "pbseg"); s.style.width = (100*l.amps/full).toFixed(2) + "%";
    s.title = l.node.label + " " + l.amps + " A"; track.appendChild(s);
  }
  if (pb.rating){ const m = el("div", "pbmark"); m.style.left = (100*0.8*pb.rating/full).toFixed(2) + "%"; track.appendChild(m); }
  card.appendChild(track);
  const leg = el("div", "pbleg");
  for (const l of pb.loads) leg.appendChild(el("span", "pbl", `${l.node.label} ${l.amps} A`));
  card.appendChild(leg);
  const gnd = el("div", "pbgnd " + (pb.ground.ok ? "ok" : "bad"),
    pb.ground.ok ? `✓ Common ground · ${pb.ground.n} nodes` :
    (!pb.sup ? "! No supply node found — set node.supply" : "✗ Not on the common ground: " + pb.ground.missing.map(n => n.label).join(", ")));
  card.appendChild(gnd);
  if (kp) kp.after(card); else shBody.prepend(card);

  /* connectors: every node, pins in order, every conductor with its colour */
  const anchor = shBody.querySelector(".schem");
  const sec = el("div", "sect", "Connectors · pin order");
  const grid = el("div", "pinouts"); grid.id = "pinouts";
  for (const n of NODES){
    const c = el("div", "pcard"); c.dataset.node = n.id;
    const h = el("div", "pch");
    h.appendChild(el("span", "pcn", n.label));
    const cn = nodeConn(n);
    h.appendChild(el("span", "pcc" + (cn ? "" : " unset"), cn || "connector ?"));
    c.appendChild(h);
    let k = 0;
    for (const {p: pn} of pinsInOrder(n)){
      const runs = RUNS.filter(r => r.from === n.id + "." + pn.id || r.to === n.id + "." + pn.id);
      const cds = conductors(n, pn);
      /* a pair pin ("+5V red/GND brn") sends its GND lead to the far end's ground pin,
         even when the run names only the +5V pin */
      const destOf = cd => runs.map(r => { const other = r.from === n.id + "." + pn.id ? runEnd(r, "to") : runEnd(r, "from");
        const pins = other.n.pins || [];
        let q = pins.find(x => x.id === other.pid) || (other.pid ? {label: other.pid} : null);
        if (cds.length > 1){
          const want = /gnd|ground/i.test(cd.label) ? "ground" : /^\+|v\b|vcc|vin|5 ?v/i.test(cd.label) ? "power" : null;
          const alt = want && pins.find(x => x.kind === want);
          if (alt) q = alt;
        }
        return other.n.label + (q ? "·" + q.label : ""); });
      for (const cd of cds){
        const dest = destOf(cd);
        k++;
        const row = el("div", "pcr"); row.dataset.src = cd.src; row.dataset.kind = pn.kind || "data";
        row.appendChild(el("span", "pco", String(k)));
        const sw = el("span", "pcw" + (cd.color ? "" : " unset")); if (cd.color) sw.style.background = cd.color;
        sw.title = cd.colName || "colour not set"; row.appendChild(sw);
        row.appendChild(el("span", "pcl", cd.label));
        row.appendChild(el("span", "pcx", cd.colName || "—"));
        row.appendChild(el("span", "pcd", dest.length ? "→ " + dest.join(", ") : ""));
        c.appendChild(row);
      }
    }
    grid.appendChild(c);
  }
  if (anchor){ anchor.after(sec); sec.after(grid); } else { shBody.appendChild(sec); shBody.appendChild(grid); }

  /* chips on every run: gauge · current · drop, and the connector at each end */
  for (const row of shBody.querySelectorAll(".wrow")){
    const r = RUNS.find(x => x.id === row.dataset.run); if (!r) continue;
    const ch = el("div", "wchips");
    const chip = (t, cls) => ch.appendChild(el("span", "wchip" + (cls ? " " + cls : ""), t));
    chip(r.gauge || (r.awg + " AWG"));
    chip((+r.amps).toFixed(r.amps < 0.1 ? 3 : 2) + " A");
    chip("ΔV " + (+r.drop_v).toFixed(3) + " V · " + (+r.drop_pct).toFixed(2) + " %", r.drop_pct > 3 ? "bad" : r.drop_pct > 1 ? "warn" : "");
    const a = runEnd(r, "from"), b = runEnd(r, "to");
    if (a.connector || b.connector) chip((a.connector || "?") + " ⇄ " + (b.connector || "?"), "conn");
    row.appendChild(ch);
  }
  paintWire();
})(showWire);
/* flow on the schematic: a dashed twin of each traced edge, marching the way
   the current goes (or a static arrow when motion is reduced) */
paintWire = (orig => function(){
  for (const e of document.querySelectorAll("#shBody .eflow")) e.remove();
  for (const id of selWire){
    const r = RUNS.find(x => x.id === id), pth = document.querySelector(`#shBody .edge[data-run="${CSS.escape(id)}"]`);
    if (!r || !pth) continue;
    const [an] = endRef(r.from), [bn] = endRef(r.to);
    const A = nodeById.get(an), B = nodeById.get(bn);
    const sa = (A && A.schem) || [0,0], sb = (B && B.schem) || [0,0];
    const fromIsStart = sa[0] < sb[0] || (sa[0] === sb[0] && sa[1] <= sb[1]);
    const fwd = (flowDir(r) > 0) === fromIsStart;
    const f = mk("path", {class: "eflow" + (fwd ? "" : " rev"), d: pth.getAttribute("d")});
    f.dataset.run = id; pth.after(f);
  }
  orig();
})(paintWire);
/* flow on the 3D tube: dashes along the projected route */
const flowEls = new Map();
(() => { const d = leads.querySelector("defs"); if (!d) return;
  const m = document.createElementNS("http://www.w3.org/2000/svg", "marker");
  for (const [k, v] of [["id","arwf"],["viewBox","0 0 10 10"],["refX","7"],["refY","5"],["markerUnits","userSpaceOnUse"],
                        ["markerWidth","11"],["markerHeight","11"],["orient","auto-start-reverse"]]) m.setAttribute(k, v);
  m.innerHTML = '<path d="M0,0 L10,5 L0,10 z" fill="context-stroke"/>'; d.appendChild(m); })();
function drawFlow3D(MVP, W, H){
  for (const [id, e] of flowEls) if (!selWire.has(id) || !wireMode){ e.remove(); flowEls.delete(id); }
  if (!wireMode) return;
  for (const id of selWire){
    const r = RUNS.find(x => x.id === id); if (!r || !r.path || r.path.length < 2) continue;
    let pts = r.path.slice();
    const a = nodeById.get(endRef(r.from)[0]);
    if (a && a.at && Math.hypot(...sub(pts[0], a.at)) > Math.hypot(...sub(pts[pts.length-1], a.at))) pts.reverse();
    if (flowDir(r) < 0) pts.reverse();
    const sp = pts.map(p => project(MVP, p, W, H)).filter(Boolean);
    let e = flowEls.get(id);
    if (!e){ e = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
      e.setAttribute("class", "flow3"); e.setAttribute("marker-end", "url(#arwf)"); leads.appendChild(e); flowEls.set(id, e); }
    e.setAttribute("points", sp.map(s => s[0].toFixed(1) + "," + s[1].toFixed(1)).join(" "));
    e.style.stroke = "var(--wire-" + r.kind + ")";
  }
}

/* ===========================================================================
   R14 — 3MF HAND-OFF: honest in an artifact, one tap from the file on the Mac
   =========================================================================== */
const inArtifact = () => !!(window.claude && window.claude.use);
function projectRoot(){
  if (META.projectDir) return META.projectDir.replace(/\/$/, "");
  const sp = parts.map(p => p.stlPath).find(Boolean); if (!sp) return null;
  const i = sp.indexOf("/out/");
  if (i > 0) return sp.slice(0, i);
  return sp.replace(/\/[^/]*$/, "").replace(/\/stl$/, "");
}
function plateLocalPath(n){
  const all = META.plateFile || null;
  let dir, file;
  if (META.plateDir) dir = META.plateDir.replace(/\/$/, "");
  else if (all && all[0] === "/" || all && all[0] === "~") dir = all.replace(/\/[^/]*$/, "");
  else { const root = projectRoot(); if (!root) return null; dir = root + "/" + (all ? all.replace(/\/[^/]*$/, "") : "av/plates"); }
  const pl = PLATES[n - 1] || {};
  if (pl.file) file = pl.file;
  else if (all) file = all.replace(/^.*\//, "").replace(/\.3mf$/i, "_plate" + n + ".3mf");
  else file = (META.slug || "plates") + "_plate" + n + ".3mf";
  const allPath = all ? dir + "/" + all.replace(/^.*\//, "") : null;
  return {dir, plate: dir + "/" + file, all: allPath};
}
showPlateBody = (orig => function(){
  orig();
  const b = $("plBody"); if (!b) return;
  const btn = [...b.querySelectorAll("button")].find(x => /3MF/.test(x.textContent));
  if (btn && inArtifact()){
    btn.textContent = "⤓ 3MF · zipped by the viewer — tap to unzip";
    btn.setAttribute("aria-label", "Download plate " + plateIdx + " as 3MF inside a zip");
  }
  const lp = plateLocalPath(plateIdx);
  if (!lp) return;
  const card = el("div", "lpath"); card.id = "localPath";
  card.appendChild(el("div", "lph", "⌂ On the Mac"));
  const row = (lab, path) => {
    const r = el("div", "lpr");
    r.appendChild(el("span", "lpk", lab));
    const code = el("code", "lpv", path); r.appendChild(code);
    const cp = el("button", "btn", "⧉"); cp.setAttribute("aria-label", "Copy " + lab + " path");
    cp.addEventListener("click", () => copyText(path, cp, "Copied"));
    r.appendChild(cp);
    card.appendChild(r);
  };
  row("Plate " + plateIdx, lp.plate);
  if (lp.all) row("All plates", lp.all);
  const acts = el("div", "acts");
  const op = el("button", "btn", "⧉ Open in slicer");
  op.addEventListener("click", () => copyText(`open -a "Creality Print" "${lp.plate.replace(/^~/, "$HOME")}"`, op, "Copied"));
  const rv = el("button", "btn", "⧉ Reveal in Finder");
  rv.addEventListener("click", () => copyText(`open -R "${lp.plate.replace(/^~/, "$HOME")}"`, rv, "Copied"));
  acts.append(op, rv); card.appendChild(acts);
  const ex = b.querySelector(".acts");
  if (ex) ex.after(card); else b.appendChild(card);
})(showPlateBody);
renderInspector = (orig => function(p){
  orig(p);
  if (!inArtifact()) return;
  for (const x of shBody.querySelectorAll("button")) if (/Download STL/.test(x.textContent))
    x.textContent = "⤓ STL · zipped by the viewer — tap to unzip";
})(renderInspector);

/* ===========================================================================
   OVERLAYS — pivot dot, 3D flow, the cube; once per frame from drawOverlays
   =========================================================================== */
const pivEl = document.createElement("div"); pivEl.className = "pivot"; marks.appendChild(pivEl);
drawMotionOverlays = (orig => function(MVP, W, H){
  orig(MVP, W, H);
  const P = drag && drag.mode === "orbit" && moved > 3 ? V7.pivot : null;
  const s = P ? project(MVP, P, W, H) : null;
  pivEl.style.display = s ? "" : "none";
  if (s) pivEl.style.transform = `translate(${s[0].toFixed(1)}px,${s[1].toFixed(1)}px)`;
  drawFlow3D(MVP, W, H);
  syncCube();
})(drawMotionOverlays);

/* ===========================================================================
   VERIFIER HOOKS (verify_av_v4.py)
   =========================================================================== */
window.__avV7 = {
  ver: () => V7.ver,
  cam: () => ({yaw: cam.yaw, pitch: cam.pitch, dist: cam.dist, pan: PAN.slice(), target: target(), ortho: V7.ortho}),
  models: () => parts.filter(p => p.kind !== "wire").map(p => ({id: p.id, m: instancesOf(p)[0]})),
  project: (pt) => { const r = cv.getBoundingClientRect(); const {MVP} = curMVP(); const s = project(MVP, pt, r.width, r.height);
                     return s ? [s[0], s[1]] : null; },
  worldAt: (x, y) => { const w = worldAt(x, y); return {p: w.p, hit: w.hit, part: w.part && w.part.id}; },
  bbox: id => { const p = byId.get(id); const b = p && v7Box([p]); return b; },
  bboxScreen: id => {
    const p = byId.get(id); if (!p) return null;
    const r = cv.getBoundingClientRect(); const {MVP} = curMVP(); const b = v7Box([p]); const out = [];
    for (let i=0;i<8;i++){ const c=[(i&1)?b.hi[0]:b.lo[0], (i&2)?b.hi[1]:b.lo[1], (i&4)?b.hi[2]:b.lo[2]];
      out.push(project(MVP, c, r.width, r.height)); }
    return {pts: out, W: r.width, H: r.height, shift: viewShiftY};
  },
  cubePoint, fitAll, setOrtho, viewOfNormal,
  anim: () => SA ? {n: SA.n, u: SA.u, paused: SA.paused, dur: SA.dur, keys: SA.keys.size} : null,
  stepPose: () => parts.filter(p => p.step === step && p.kind !== "wire").map(p => {
    const now = instancesOf(p)[0], ref = M.trans(explodeVec(p));
    let d = 0; for (let i=0;i<16;i++) d = Math.max(d, Math.abs(now[i] - ref[i])); return {id: p.id, d}; }),
  midPose: () => parts.filter(p => SA && p.step === SA.n && p.kind !== "wire").map(p => {
    const now = instancesOf(p)[0], ref = M.trans(explodeVec(p));
    let d = 0; for (let i=0;i<16;i++) d = Math.max(d, Math.abs(now[i] - ref[i])); return {id: p.id, d}; }),
  budget: () => { const b = powerBudget(); return {sup: b.sup && b.sup.id, rating: b.rating, total: +b.total.toFixed(3),
    pct: b.pct, status: b.status, ground: {ok: b.ground.ok, n: b.ground.n, missing: b.ground.missing.map(n => n.id)},
    loads: b.loads.map(l => [l.node.id, l.amps])}; },
  pinouts: () => NODES.map(n => ({id: n.id, connector: nodeConn(n),
    pins: pinsInOrder(n).map(({p, o}) => ({id: p.id, order: o, wires: conductors(n, p).map(c => ({label: c.label, color: c.colName, src: c.src}))}))})),
  flow: id => { const r = RUNS.find(x => x.id === id); return r ? flowDir(r) : null; },
  platePath: n => plateLocalPath(n || plateIdx),
  mat: id => { const p = byId.get(id); return p ? matOf(p).kind : null; },
  edgeSkipped: () => V7.edgeSkipped || 0,
  flags: o => { Object.assign(V7, o || {}); draw(); return {edges: V7.edges, shadow: V7.shadow, cube: V7.cube !== false, fs: V7.fs !== false}; },
};
