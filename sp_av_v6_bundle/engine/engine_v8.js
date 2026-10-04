/* ===========================================================================
   SP AV ENGINE v8 — module (inlined by patch_engine_v8.py, before BOOT, after v7 … v7.4)
   R38 phase bar LOAD → FIT → SECURE → TEST, each phase a URL-hash state
   R39 source labels on every engineering number (MEASURED · CALC · CAD · SLICER · DATASHEET · ASSUMED · SPEC)
   R40 caliper tool          R41 tolerance bands from the printer's measured profile
   R42 tolerance stack-up    R43 SECURE overlays: insert iron temp + torque, with their source
   R44 TEST load slider -> CALC stress heatmap + servo-stall warning (same formulas as calc_v8.py)
   R45 "what breaks first?" ranking, fly-to, fillet fix with Kt before / after
   R46 X-ray + true wireframe   R47 capped (hatched) section faces
   R48 parts tree drawer + engineering data in the inspector (bottom sheet under 768 px)
   R49 Share View (phase, camera, explode, section, load, toggles in the hash)
   R50 STL per part + Send to slicer (3MF)   R51 BOM: OWNED $0
   R52 perf HUD (fps, triangles, draw calls) + LOD swap past 2× zoom
   R53 engineering data contract: checks tiles, UNVERIFIED / MISSING, MEASURE_ME
   R54 fix: view history ◀ returned to a view recorded before Reset (v7.4 gate failure)
   R55 build-step fly-ins draw at interaction resolution, clock clamped to 50 ms/frame   R56 CSS variables cached (patch script)
   R57 interaction-resolution ladder: 0.75× rung + double step when far over budget
   =========================================================================== */
V7.ver = "8.0";
const ENG = META.eng || null;
const MD = ENG && ENG.model;
const BRAND = META.brand || {accent: "#FF6B35", loader: "Shawarma Prints · Designed in Vaughan, ON", footer: "Prototyped on Ender 3 S1 Pro · Toronto, Canada"};
const V8 = {phase: null, calOn: false, calPts: [], cal: null, tol: false, heat: false, xray: false, wire: false,
            kg: MD ? MD.kg.v : 0, lever: MD ? MD.lever.v : 0, perf: false, lodOn: true, lodNow: false,
            spacing: 50, hover: null, measured: {}, frame: {calls: 0, tris: 0, scene: 0}, last: {calls: 0, tris: 0, scene: 0}};
const SRC_TXT = (ENG && ENG.sources) || {};
const G8 = 9.80665, KGCM8 = 98.0665;

/* ===========================================================================
   R39 — numbers with their source
   =========================================================================== */
function fmt8(v, d){
  if (v == null || !isFinite(v)) return "—";
  const a = Math.abs(v);
  if (d == null) d = a >= 100 ? 0 : a >= 10 ? 1 : a >= 1 ? 2 : 3;
  return (+v).toFixed(d);
}
function srcEl(src, formula){
  const s = el("span", "src s-" + src, src);
  s.title = src + " — " + (SRC_TXT[src] || "") + (formula ? "\n" + formula : "");
  return s;
}
function num8(v, u, src, formula, d){
  const w = el("span", "num"); w.dataset.src = src || "?";
  if (formula) w.dataset.f = formula;
  w.appendChild(document.createTextNode(typeof v === "number" ? fmt8(v, d) : (v == null ? "—" : String(v))));
  if (u){ const sm = document.createElement("small"); sm.textContent = " " + u; w.appendChild(sm); }
  w.appendChild(srcEl(src || "?", formula));
  return w;
}
const nameEl = (tag, cls, txt) => { const e = el(tag, cls, txt); e.dataset.nonum = "1"; return e; };
function engBox(){ const d = el("div"); d.dataset.eng = "1"; return d; }
function statusPill(st){
  const ic = {pass: "✓", fail: "✗", warn: "!", unverified: "?", na: "–"}[st] || "?";
  const lb = {pass: "PASS", fail: "FAIL", warn: "WARN", unverified: "UNVERIFIED", na: "N/A"}[st] || st;
  return nameEl("span", "v8st " + st, ic + " " + lb);
}

/* ===========================================================================
   R44 — the live model: a line-for-line mirror of calc_v8.Model (verify_av_v9 compares them)
   =========================================================================== */
function ktStep8(D, d, r){
  const T = MD.kt_table, q = Math.max(1.01, Math.min(6.0, D/d));
  let A = T[0][1], B = T[0][2];
  for (let i = 0; i < T.length - 1; i++){
    const [q0, a0, b0] = T[i], [q1, a1, b1] = T[i+1];
    if (q0 <= q && q <= q1){ const f = (q - q0)/(q1 - q0); A = a0 + f*(a1 - a0); B = b0 + f*(b1 - b0); break; }
  }
  const rd = Math.max(0.002, Math.min(0.3, r/d));
  return Math.max(1.0, A*Math.pow(rd, B));
}
const o8 = () => MD.shaft.origin;
function mass8(pid, kg){ return pid === "weight" ? kg*1000 : MD.masses[pid].g; }
function com8(pid, lever){ const u = MD.arm_dir; return pid === "weight" ? [o8()[0] + lever*u[0], MD.load_point[1], o8()[2] + lever*u[2]] : MD.masses[pid].com; }
function xz8(pid, lever){ const c = com8(pid, lever), o = o8(), u = MD.arm_dir; return [(c[0]-o[0])*u[0] + (c[1]-o[1])*u[1] + (c[2]-o[2])*u[2], c[2] - o[2]]; }
const ahead8 = (y, yr) => (y - yr)*MD.front[1];
function tau8(kg, lever, th){
  const t = th*Math.PI/180; let n = 0;
  for (const pid of MD.moving){ const [x, z] = xz8(pid, lever); n += mass8(pid, kg)/1000*G8*(x*Math.cos(t) - z*Math.sin(t)); }
  return n;
}
function tauMax8(kg, lever){
  const [lo, hi] = MD.limits; let b = 0;
  for (let th = Math.trunc(lo); th <= Math.trunc(hi); th++) b = Math.max(b, Math.abs(tau8(kg, lever, th)));
  return b;
}
function inertia8(kg, lever){ let I = 0; for (const pid of MD.moving){ const [x, z] = xz8(pid, lever); I += mass8(pid, kg)*(x*x + z*z); } return I; }
function tauDyn8(kg, lever){
  const k = MD.path.keys, sp = MD.path.speed_dps; let amax = 0;
  for (let i = 0; i < k.length - 1; i++){
    const dd = Math.abs(k[i+1] - k[i]), T = 1.875*dd/sp;          /* the path player: speed_dps is the peak speed */
    if (T > 0) amax = Math.max(amax, 5.774*dd*Math.PI/180/(T*T));
  }
  return [inertia8(kg, lever)*1e-9*amax*1000, amax];
}
function armRoot8(kg, lever, r){
  const S = MD.sections.arm_root, x = MD.arm_root.x_from_shaft, d = S.d, t = S.t, D = S.D;
  r = r == null ? S.r : r;
  const F = kg*G8, xa = xz8("arm", lever)[0], ga = MD.masses.arm.g/1000*G8;
  const Mb = F*Math.max(0, lever - x) + ga*Math.max(0, xa - x), V = F + ga;
  const I = t*d*d*d/12, c = d/2, sig = Mb*c/I, kt = ktStep8(D, d, r), tau = 1.5*V/(t*d);
  const vm = Math.sqrt((kt*sig)**2 + 3*tau*tau);
  return {M: Mb, V, I, c, sigma: sig, kt, tau, vm, sf: vm > 0 ? MD.yield_xy/vm : Infinity, x, r};
}
function hanging8(kg, lever){ return [...MD.moving, "servo", "tab0", "tab1"].map(pid => [mass8(pid, kg), com8(pid, lever)[1]]); }
function wallRoot8(kg, lever){
  const S = MD.sections.wall_root;
  const Mw = hanging8(kg, lever).reduce((a, [m, y]) => a + m/1000*G8*ahead8(y, S.y_mid), 0);
  const I = S.b*S.h**3/12, sig = Math.abs(Mw)*(S.h/2)/I, vm = S.kt_bound*sig, st = MD.yield_xy*MD.z_factor;
  return {M: Mw, I, sigma: sig, kt: S.kt_bound, vm, sf: vm > 0 ? st/vm : Infinity, strength: st};
}
function tabs8(kg, lever){
  const S = MD.fgs.tab_screws;
  const Mx = hanging8(kg, lever).filter(([m, y]) => ahead8(y, S.y_wall) > 0).reduce((a, [m, y]) => a + m/1000*G8*ahead8(y, S.y_wall), 0);
  const F = Math.max(0, Mx)/(S.n*S.lever), tau = F/(Math.PI*S.d*S.Le*0.5), allow = 0.577*MD.yield_xy*MD.z_factor;
  return {Mx, F, tau, allow, sf: tau > 0 ? allow/tau : Infinity};
}
function inserts8(kg, lever){
  const S = MD.fgs.inserts;
  const Mt = hanging8(kg, lever).filter(([m, y]) => ahead8(y, S.y_edge) > 0).reduce((a, [m, y]) => a + m/1000*G8*ahead8(y, S.y_edge), 0);
  return {M: Mt, F: Math.max(0, Mt)/(S.n*S.arm), limit: S.limit};
}
function defl8(kg, lever){
  const S = MD.sections.arm_root, L = Math.max(0, lever - MD.arm_root.x_from_shaft), I = MD.arm_t_full*S.d**3/12;
  return kg*G8*L**3/(3*MD.E*I);
}
function bisect8(f){ let lo = 0, hi = arguments[1] || 50; for (let i = 0; i < 60; i++){ const m = (lo + hi)/2; if (f(m)) hi = m; else lo = m; } return lo; }
const kgStall8 = lever => bisect8(m => tauMax8(m, lever) > MD.stall_nmm, 50);
const kgBreak8 = (lever, r) => bisect8(m => armRoot8(m, lever, r).sf < 1.0, 100);
function calc8(kg, lever){
  kg = kg == null ? V8.kg : kg; lever = lever == null ? V8.lever : lever;
  const th = tauMax8(kg, lever), [td, amax] = tauDyn8(kg, lever), ks = kgStall8(lever);
  return {kg, lever, tau_hold: th, frac_hold: th/MD.stall_nmm, tau_dyn: td, alpha: amax, frac_dyn: (th + td)/MD.stall_nmm,
          arm: armRoot8(kg, lever), arm_fix: armRoot8(kg, lever, MD.sections.arm_root.r_fix), wall: wallRoot8(kg, lever),
          tabs: tabs8(kg, lever), inserts: inserts8(kg, lever), defl: defl8(kg, lever), kg_stall: ks, arm_at_stall: armRoot8(ks, lever)};
}
/* §5 mechanism formulas (N/A on this design, unit-tested against calc_v8 by verify_av_v9) */
const F8 = {
  lewis: (Ft, b, m, Y) => Ft/(b*m*Y),
  grashof: L => { const s = Math.min(...L), l = Math.max(...L), pq = L.reduce((a, x) => a + x, 0) - s - l; return s + l <= pq; },
  transAngle: (a, b, c, d, th) => { const e2 = a*a + d*d - 2*a*d*Math.cos(th*Math.PI/180); return Math.acos(Math.max(-1, Math.min(1, (b*b + c*c - e2)/(2*b*c))))*180/Math.PI; },
  gripNeed: (m, mu, sf, a) => m*(G8 + (a || 0))/(2*mu)*(sf == null ? 2 : sf),
  leadscrew: (tau, eta, lead) => 2*Math.PI*tau*eta/lead,
  beltTeeth: (z, d1, d2, C) => z*(Math.PI - 2*Math.asin((d2 - d1)/(2*C)))/(2*Math.PI),
  minjerk: (dth, T) => 5.774*dth/(T*T),
  kt: (D, d, r) => ktStep8(D, d, r),
};
/* the checks the slider moves: same thresholds and the same UNVERIFIED rule as calc_v8.check() */
function liveChecks(R){
  if (!ENG) return [];
  const map = {torque_hold: R.frac_hold*100, torque_dyn: R.frac_dyn*100, sf_arm: R.arm.sf, sf_arm_stall: R.arm_at_stall.sf,
               sf_wall: R.wall.sf, sf_tabs: R.tabs.sf, insert_pull: R.inserts.F, defl: R.defl};
  return ENG.checks.map(c => {
    if (!(c.id in map)) return c;
    const value = map[c.id];
    let would;
    if (value == null || c.limit == null) would = "unverified";
    else if (c.cmp === "ge") would = value >= c.limit ? "pass" : value >= c.limit*0.7 ? "warn" : "fail";
    else would = value <= c.limit ? "pass" : value <= c.limit*1.4 ? "warn" : "fail";
    let status = would === "fail" ? "fail" : (c.assumed.length ? "unverified" : would);
    if (value == null || c.limit == null) status = "unverified";
    const inputs = c.inputs.map(i => i.k === "load mass" ? {...i, v: R.kg} : i.k === "lever arm" ? {...i, v: R.lever} : i.k === "load at stall" ? {...i, v: R.kg_stall} : i);
    return {...c, value, would, status, inputs};
  });
}

/* ===========================================================================
   R41 — tolerance: printed size and fit band FROM THE PROFILE (never hard-coded)
   =========================================================================== */
function printed8(cad, kind){
  const T = ENG.tolerance;
  if (kind === "rect") return [cad.map(c => c + T.rect.delta), T.rect.src];
  const meas = (T.coupon || []).filter(c => c.measured != null || V8.measured[c.cad] != null)
                 .map(c => [c.cad, V8.measured[c.cad] != null ? V8.measured[c.cad] : c.measured]).sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  if (meas.length >= 2){
    const ds = meas.map(([c, m]) => [c, m - c]);
    let d;
    if (cad <= ds[0][0]) d = ds[0][1];
    else if (cad >= ds[ds.length-1][0]) d = ds[ds.length-1][1];
    else for (let i = 0; i < ds.length - 1; i++) if (ds[i][0] <= cad && cad <= ds[i+1][0]){ d = ds[i][1] + (ds[i+1][1] - ds[i][1])*(cad - ds[i][0])/(ds[i+1][0] - ds[i][0]); break; }
    return [cad + d, "MEASURED"];
  }
  return [cad + T.model.a + T.model.b/cad, T.model.src];
}
function band8(purpose, clr){
  const T = ENG.tolerance;
  for (const b of T.bands[purpose] || []){
    const lo = b.min == null ? -1e9 : b.min, hi = b.max == null ? 1e9 : b.max;
    if (lo <= clr && clr < hi) return {cls: b.cls, label: b.label, color: T.colors[b.color], tone: b.color};
  }
  return {cls: "?", label: "?", color: "#888888", tone: "red"};
}
function fits8(){
  if (!ENG || !ENG.fits) return [];
  return ENG.fits.map(f => {
    const cad = f.cad.v, mate = f.mate_size.v;
    const [pr, psrc] = printed8(cad, f.kind);
    const meas = V8.measured[f.id] != null ? V8.measured[f.id] : f.measured.v;
    const basis = meas != null ? meas : pr;
    const clr = f.kind === "rect" ? Math.min(...basis.map((p, i) => p - mate[i])) : basis - mate;
    return {...f, printedJS: pr, psrc, clr, measuredJS: meas, band: band8(f.purpose, clr)};
  });
}

/* ===========================================================================
   SHADER HOOKS — heat, wireframe, the colour of a hovered part (called from the patched draw)
   =========================================================================== */
let HEAT = new Map();
let heatCols = null, heatTheme = "";
function heatColours(){
  const th = document.documentElement.dataset.theme || "dark";
  if (heatCols && heatTheme === th) return heatCols;
  heatTheme = th;
  heatCols = ["--heat-0", "--heat-1", "--heat-2", "--heat-3", "--heat-over"].map(n => hex(cssVar(n) || "#2a78d6"));
  return heatCols;
}
function v8Uniforms(){
  if (!gl || uni.uH0 == null) return;
  const c = heatColours();
  gl.uniform3fv(uni.uH0, c[0]); gl.uniform3fv(uni.uH1, c[1]); gl.uniform3fv(uni.uH2, c[2]);
  gl.uniform3fv(uni.uH3, c[3]); gl.uniform3fv(uni.uHO, c[4]);
  gl.uniform1f(uni.uWire, V8.wire ? 1 : 0);
}
function v8PartUniforms(p){
  if (!gl || uni.uHeatA == null) return;
  const h = V8.heat && HEAT.get(p.id);
  if (!h){ gl.uniform4f(uni.uHeatA, 0, 0, 0, 0); return; }
  gl.uniform4f(uni.uHeatA, h.o[0], h.o[1], h.o[2], 1);
  gl.uniform4f(uni.uHeatB, h.d[0], h.d[1], h.d[2], Math.max(1e-3, h.L));
  gl.uniform2f(uni.uHeatS, h.s0, h.s1);
}
const ACC = () => hex((cssVar("--accent") || "#ff6b35").slice(0, 7));
function v8Tint(p){
  if (V8.hover && V8.hover === p.id){ const a = ACC(), c = p.rgb; return [a[0]*0.7 + c[0]*0.3, a[1]*0.7 + c[1]*0.3, a[2]*0.7 + c[2]*0.3]; }
  return null;
}
v7Uniforms = (orig => function(V){ orig(V); v8Uniforms(); })(v7Uniforms);
/* the heat / wireframe program: built from the base source the first time it is needed */
const U8X = ["uHeatA", "uHeatB", "uHeatS", "uH0", "uH1", "uH2", "uH3", "uHO", "uWire"];
const prog0 = prog, uni0 = {...uni}, uniH = {};
let progH = null, progHfail = false;
function heatProg(){
  if (progH || progHfail || !gl) return progH;
  const rep = (src, a, b) => { if (src.indexOf(a) < 0) throw new Error("heat shader anchor missing: " + a.slice(0, 40)); return src.replace(a, b); };
  try {
    let vs = rep(VS, "out vec3 vP; out vec3 vW;\nvoid main(){\n  vec3 q = (aQ*0.5+0.5)*uSpan + uLo;",
      "out vec3 vP; out vec3 vW; out vec3 vQ; out vec3 vB;\nvoid main(){\n  vec3 q = (aQ*0.5+0.5)*uSpan + uLo;\n  vQ = q;\n" +
      "  int k3 = gl_VertexID - 3*(gl_VertexID/3);\n  vB = vec3(k3==0 ? 1.0 : 0.0, k3==1 ? 1.0 : 0.0, k3==2 ? 1.0 : 0.0);");
    let fs = rep(FS, "out vec4 o;\nvoid main(){",
      "uniform vec4 uHeatA, uHeatB; uniform vec2 uHeatS; uniform vec3 uH0, uH1, uH2, uH3, uHO; uniform float uWire;\nin vec3 vQ; in vec3 vB;\n" +
      "vec3 heatRamp(float s){ if (s >= 1.0) return uHO; float x = clamp(s,0.0,1.0)*3.0;\n" +
      "  if (x < 1.0) return mix(uH0,uH1,x); if (x < 2.0) return mix(uH1,uH2,x-1.0); return mix(uH2,uH3,x-2.0); }\nout vec4 o;\nvoid main(){");
    fs = rep(fs, "  vec3 c = uCol;\n",
      "  vec3 c = uCol;\n  if (uHeatA.w > 0.5){ float th = clamp(dot(vQ - uHeatA.xyz, uHeatB.xyz)/max(uHeatB.w,1e-3), 0.0, 1.0); c = heatRamp(mix(uHeatS.x, uHeatS.y, th)); }\n");
    fs = rep(fs, "  o = vec4(col, uAlpha);",
      "  if (uWire > 0.5){ vec3 fw = fwidth(vB); vec3 a3 = smoothstep(vec3(0.0), fw*1.4, vB);\n" +
      "    float edge = 1.0 - min(min(a3.x, a3.y), a3.z); if (edge < 0.1) discard; col = mix(col*0.6, col + 0.25, edge); }\n  o = vec4(col, uAlpha);");
    progH = link(vs, fs, "aQ");
    for (const k of [...U, ...U8X]) uniH[k] = gl.getUniformLocation(progH, k);
  } catch(e){ progHfail = true; console.warn("v8 heat program unavailable:", e.message); }
  return progH;
}
function pickProgram(){
  const want = (V8.heat && HEAT.size > 0) || V8.wire;
  if (want && heatProg()){ prog = progH; Object.assign(uni, uniH); }
  else { prog = prog0; Object.assign(uni, uni0); for (const k of U8X) uni[k] = null; }
}

/* ===========================================================================
   R52 — perf HUD + LOD: count what the GPU is asked to draw; swap fine meshes in close up
   =========================================================================== */
if (gl){
  const _da = gl.drawArrays.bind(gl);
  gl.drawArrays = function(mode, first, count){ V8.frame.calls++; if (mode === gl.TRIANGLES) V8.frame.tris += count/3; return _da(mode, first, count); };
}
const drawT = [];
let perfEl = null;
function lodWanted(){ return V8.lodOn && !plateMode && cam.dist < HOME.dist/2; }
draw = (orig => function(){
  V8.frame = {calls: 0, tris: 0, scene: 0};
  const swap = lodWanted(), saved = [];
  if (swap) for (const p of parts) if (p.lod){ saved.push([p, p.off, p.n, p.lo, p.span]); p.off = p.lod.off; p.n = p.lod.n; p.lo = p.lod.lo; p.span = p.lod.span; }
  V8.lodNow = swap && saved.length > 0;
  pickProgram();
  for (const p of parts) if (state(p) === "solid") V8.frame.scene += p.n/3;
  try { orig(); }
  finally { for (const [p, off, n, lo, span] of saved){ p.off = off; p.n = n; p.lo = lo; p.span = span; } }
  V8.last = V8.frame;
  const t = performance.now(); drawT.push(t); while (drawT.length > 40) drawT.shift();
  if (V8.perf) perfPaint();
})(draw);
function fps8(){
  const t = performance.now(), d = drawT.filter(x => t - x < 1500);
  if (d.length < 3) return null;
  let run = [d[d.length-1]];
  for (let i = d.length - 2; i >= 0; i--){ if (run[0] - d[i] > 120) break; run.unshift(d[i]); }
  return run.length < 3 ? null : (run.length - 1)*1000/(run[run.length-1] - run[0]);
}
let perfT = 0;
function perfPaint(){
  const t = performance.now(); if (t - perfT < 250 && perfEl && perfEl.textContent) return; perfT = t;
  if (!perfEl){ perfEl = el("div"); perfEl.id = "v8perf"; perfEl.setAttribute("aria-live", "off"); $("stage").appendChild(perfEl); }
  const f = fps8();
  perfEl.textContent = `fps   ${f == null ? "idle" : f.toFixed(0)}\ntris  ${(V8.last.scene/1000).toFixed(1)}k scene${V8.lodNow ? " · LOD" : ""}\n      ${(V8.last.tris/1000).toFixed(1)}k drawn\ncalls ${V8.last.calls}`;
  perfEl.classList.toggle("bad", f != null && f < 30);
}
function setPerf(on){
  V8.perf = !!on; const b = $("bPerf"); if (b) b.setAttribute("aria-pressed", String(V8.perf));
  if (perfEl) perfEl.hidden = !V8.perf;
  if (V8.perf){ if (perfEl) perfEl.hidden = false; draw(); }
}
$("bPerf") && $("bPerf").addEventListener("click", () => setPerf(!V8.perf));

/* ===========================================================================
   R46 — X-ray (everything but the selection ghosts) and true wireframe (barycentric edges)
   =========================================================================== */
state = (orig => function(p){
  const s = orig(p);
  if (V8.xray && s === "solid" && p.kind !== "wire" && !sel.has(p.id)) return "ghost";
  return s;
})(state);
function setXray(on){ V8.xray = !!on; syncToggles(); draw(); writeHash(); }
function setWire(on){ V8.wire = !!on; syncToggles(); draw(); writeHash(); }
function syncToggles(){
  for (const [id, on] of [["v8Xray", V8.xray], ["v8Wire", V8.wire], ["v8Tol", V8.tol], ["bCal", V8.calOn]]){
    const b = $(id); if (b) b.setAttribute("aria-pressed", String(!!on));
  }
}

/* ===========================================================================
   R40 — CALIPER: tap two features -> an animated caliper reads the distance (CAD)
   =========================================================================== */
function setCal(on){
  V8.calOn = !!on; V8.calPts = [];
  if (V8.calOn){ if (typeof diaOn !== "undefined" && diaOn) setDia(false); if (typeof gapOn !== "undefined" && gapOn) setGap(false);
                 if (typeof angOn !== "undefined" && angOn) setAng(false); if (measOn) $("bMeas").click();
                 flash2("Caliper · tap two features", "corners and hole edges snap"); }
  cv.style.cursor = V8.calOn ? "crosshair" : "";
  syncToggles(); draw();
}
$("bCal") && $("bCal").addEventListener("click", () => setCal(!V8.calOn));
setDia = (o => function(on){ if (on && V8.calOn) setCal(false); return o(on); })(setDia);
setGap = (o => function(on){ if (on && V8.calOn) setCal(false); return o(on); })(setGap);
setAng = (o => function(on){ if (on && V8.calOn) setCal(false); return o(on); })(setAng);
$("bMeas").addEventListener("click", () => { if (measOn && V8.calOn) setCal(false); });
navTap = (orig => function(cx, cy, hp){
  if (!V8.calOn || V7.lpFired) return orig(cx, cy, hp);
  const h = raycast(cx, cy);
  if (!h){ flash("No part under that tap"); return true; }
  if (V8.calPts.length >= 2) V8.calPts.length = 0;
  V8.calPts.push({part: h.part.id, local: h.local});
  if (V8.calPts.length === 1) flash2("Caliper · 1 / 2", "now the second feature");
  else {
    const w = V8.calPts.map(q => M.xform(modelOf(byId.get(q.part)), q.local));
    const d = Math.hypot(w[0][0] - w[1][0], w[0][1] - w[1][1], w[0][2] - w[1][2]);
    V8.cal = {d, t0: performance.now()};
    flash2("Caliper " + d.toFixed(2) + " mm", "CAD · straight line between the two snapped points");
    calAnim();
  }
  buzz(); draw(); return true;
})(navTap);
function calAnim(){
  const step = () => { draw(); if (V8.cal && performance.now() - V8.cal.t0 < 480) requestAnimationFrame(step); };
  requestAnimationFrame(step);
}
const SVGNS8 = "http://www.w3.org/2000/svg";
const svg8 = (tag, cls) => { const e = document.createElementNS(SVGNS8, tag); if (cls) e.setAttribute("class", cls); leads.appendChild(e); return e; };
let calG = null, calLbl = null;
function drawCal(MVP, W, H){
  if (!calG){ calG = {beam: svg8("path", "v8cal beam"), jaws: svg8("path", "v8cal")};
              calLbl = el("div", "v8lbl cal"); calLbl.dataset.eng = "1"; marks.appendChild(calLbl); }
  const on = V8.calOn && V8.calPts.length > 0;
  showEl(calG.beam, on); showEl(calG.jaws, on); showEl(calLbl, on && V8.calPts.length === 2);
  if (!on) return;
  const P = V8.calPts.map(q => project(MVP, M.xform(modelOf(byId.get(q.part)), q.local), W, H));
  if (!P[0]) return;
  if (P.length < 2 || !P[1]){ calG.beam.setAttribute("d", `M${P[0][0]-6},${P[0][1]} h12 M${P[0][0]},${P[0][1]-6} v12`); calG.jaws.setAttribute("d", ""); return; }
  let ux = P[1][0] - P[0][0], uy = P[1][1] - P[0][1]; const L = Math.hypot(ux, uy) || 1; ux /= L; uy /= L;
  let nx = -uy, ny = ux; if (ny > 0){ nx = -nx; ny = -ny; }           // jaws reach up the screen
  const t = Math.min(1, (performance.now() - (V8.cal ? V8.cal.t0 : 0))/450), e = V7RM() ? 1 : 1 - Math.pow(1 - t, 3);
  const Lb = L*(1 + 0.6*(1 - e));                                     // the moving jaw closes onto the feature
  const A = P[0], B = [A[0] + ux*Lb, A[1] + uy*Lb], off = 28, jaw = 40;
  calG.jaws.setAttribute("d", `M${A[0]},${A[1]} L${A[0]+nx*jaw},${A[1]+ny*jaw} M${B[0]},${B[1]} L${B[0]+nx*jaw},${B[1]+ny*jaw}`);
  calG.beam.setAttribute("d", `M${A[0]+nx*off - ux*10},${A[1]+ny*off - uy*10} L${B[0]+nx*off + ux*16},${B[1]+ny*off + uy*16}`);
  if (V8.cal){
    calLbl.textContent = "";
    calLbl.appendChild(num8(V8.cal.d, "mm", "CAD", "distance between the two snapped mesh points", 2));
    const mx = (A[0] + B[0])/2 + nx*(off + 16), my = (A[1] + B[1])/2 + ny*(off + 16);
    calLbl.style.transform = `translate(${Math.round(mx)}px,${Math.round(my)}px) translate(-50%,-50%)`;
  }
}

/* ===========================================================================
   R41 — TOLERANCE RINGS around every hole / window, coloured from the profile
   =========================================================================== */
const tolEls = [];
function ringPts(f, m){
  const c = M.xform(m, f.at);
  const a0 = M.xform(m, add(f.at, f.axis)), ax = nrm(sub(a0, c));
  const ref = Math.abs(ax[2]) > 0.9 ? [1, 0, 0] : [0, 0, 1];
  const e1 = nrm(cross(ax, ref)), e2 = cross(ax, e1);
  const pts = [];
  if (f.kind === "rect"){
    const w = f.size[0]/2 + 0.8, h = f.size[1]/2 + 0.8;
    // window: e1 runs along the long side when the axis is Y
    const E1 = Math.abs(e1[0]) > 0.5 ? e1 : e2, E2 = Math.abs(e1[0]) > 0.5 ? e2 : e1;
    for (const [s, t] of [[-1, -1], [1, -1], [1, 1], [-1, 1], [-1, -1]]) pts.push(add(c, add(scl(E1, s*w), scl(E2, t*h))));
  } else {
    const r = f.d/2 + 0.7;
    for (let i = 0; i <= 28; i++){ const t = i/28*2*Math.PI; pts.push(add(c, add(scl(e1, r*Math.cos(t)), scl(e2, r*Math.sin(t))))); }
  }
  return pts;
}
function drawTol(MVP, W, H){
  const F = (V8.tol && ENG) ? fits8() : [];
  while (tolEls.length < F.length){
    const ring = svg8("path", "v8tol"), lb = el("div", "v8lbl"); lb.dataset.eng = "1"; marks.appendChild(lb);
    tolEls.push({ring, lb});
  }
  tolEls.forEach((t, i) => {
    const f = F[i], p = f && byId.get(f.part);
    const on = !!(f && p && state(p) !== "off");
    showEl(t.ring, on); showEl(t.lb, on && labelsOn);
    if (!on) return;
    const m = modelOf(p), S = ringPts(f, m).map(q => project(MVP, q, W, H));
    if (S.some(s => !s)){ showEl(t.ring, false); showEl(t.lb, false); return; }
    t.ring.setAttribute("d", "M" + S.map(s => s[0].toFixed(1) + "," + s[1].toFixed(1)).join(" L") + (f.kind === "rect" ? " Z" : ""));
    t.ring.setAttribute("stroke", f.band.color);
    t.ring.dataset.fit = f.id; t.ring.dataset.cls = f.band.cls;
    const top = S.reduce((a, s) => s[1] < a[1] ? s : a, S[0]);
    const full = V8.fitSel === f.id;
    const key = f.id + f.band.cls + f.clr.toFixed(3) + full;
    if (t.lb.dataset.k !== key){
      t.lb.dataset.k = key; t.lb.textContent = "";
      const ic = {green: "✓", yellow: "!", red: "✗"}[f.band.tone] || "?";
      const dot = nameEl("span", null, ic + (full ? " " : "")); dot.style.color = f.band.color; t.lb.appendChild(dot);
      if (full){ t.lb.appendChild(nameEl("span", null, f.label + " ")); t.lb.appendChild(num8(f.clr, "mm", "CALC", "printed (profile " + f.psrc + ") − " + f.mate, 2)); }
      t.lb.style.zIndex = full ? 4 : 3;
    }
    t.lb.style.transform = `translate(${Math.round(top[0])}px,${Math.round(top[1] - 8)}px) translate(-50%,-100%)`;
  });
}

/* ===========================================================================
   R43 — SECURE overlays: iron temperature on inserts, torque on screws (with their source)
   =========================================================================== */
const secEls = [];
function secureItems(){
  if (!(V8.phase === "secure" && stepMode && ENG)) return [];
  const out = [];
  for (const p of parts){
    if (p.step !== step) continue;
    const fs = (ENG.fasteners || []).find(f => f.id === p.id);
    if (fs && fs.torque) out.push({p, txt: "⟳ ", v: fs.torque.v, u: "N·m", src: fs.torque.src, f: fs.torque.note || ""});
    if (/^ins/.test(p.id)){
      const ins = (ENG.inserts || [])[0], mat = ENG.materials && ENG.materials.PETG;
      const ic = ins && ins.iron_c ? ins.iron_c : (mat && mat.iron_c);
      if (ic) out.push({p, txt: "🔥 ", v: ic.v, u: "°C", src: ic.src, f: ic.note || "iron temperature (material table)"});
    }
  }
  return out;
}
function drawSecure(MVP, W, H){
  const It = secureItems();
  while (secEls.length < It.length){ const d = el("div", "v8lbl"); d.dataset.eng = "1"; marks.appendChild(d); secEls.push(d); }
  secEls.forEach((d, i) => {
    const it = It[i]; showEl(d, !!it); if (!it) return;
    const s = project(MVP, partCentre(it.p), W, H); if (!s){ showEl(d, false); return; }
    const key = it.p.id + it.v;
    if (d.dataset.k !== key){ d.dataset.k = key; d.textContent = ""; d.appendChild(nameEl("span", null, it.txt)); d.appendChild(num8(it.v, it.u, it.src, it.f, it.u === "°C" ? 0 : 2)); }
    d.style.transform = `translate(${Math.round(s[0] + 14)}px,${Math.round(s[1] - 10)}px)`;
  });
}

/* ===========================================================================
   R44 — load arrow at the load point (TEST)
   =========================================================================== */
let arrEl = null, arrLbl = null;
function drawArrow(MVP, W, H){
  if (!arrEl){ arrEl = svg8("path", "v8arrow"); arrEl.setAttribute("marker-end", "url(#arwh)"); arrLbl = el("div", "v8lbl"); arrLbl.dataset.eng = "1"; marks.appendChild(arrLbl); }
  const arm = byId.get("arm"), on = !!(V8.phase === "test" && MD && arm && V8.kg > 0);
  showEl(arrEl, on); showEl(arrLbl, on); if (!on) return;
  const m = modelOf(arm), P = M.xform(m, com8("weight", V8.lever));
  const Lw = 8 + 22*Math.min(1, V8.kg/1.0), Q = [P[0], P[1], P[2] - Lw];
  const a = project(MVP, P, W, H), b = project(MVP, Q, W, H); if (!a || !b){ showEl(arrEl, false); showEl(arrLbl, false); return; }
  arrEl.setAttribute("d", `M${a[0]},${a[1]} L${b[0]},${b[1]}`);
  const key = V8.kg.toFixed(3);
  if (arrLbl.dataset.k !== key){ arrLbl.dataset.k = key; arrLbl.textContent = ""; arrLbl.appendChild(num8(V8.kg*G8, "N", "SPEC", "F = m·g, m from the TEST slider", 2)); }
  arrLbl.style.transform = `translate(${Math.round(b[0] + 8)}px,${Math.round(b[1])}px)`;
}

/* all v8 overlays ride the existing per-frame overlay hook */
drawMotionOverlays = (orig => function(MVP, W, H){ orig(MVP, W, H); drawCal(MVP, W, H); drawTol(MVP, W, H); drawSecure(MVP, W, H); drawArrow(MVP, W, H); })(drawMotionOverlays);

/* ===========================================================================
   LOAD — hover / tap tooltip: name, material, mass, print time — every number labelled
   =========================================================================== */
let tipEl = null, hovT = 0;
function tipFor(p){
  const e = ENG && ENG.parts[p.id];
  const box = engBox(); box.appendChild(nameEl("b", null, p.label));
  const row = (k, node) => { const r = el("div"); r.appendChild(nameEl("span", null, k + " ")); r.appendChild(node); box.appendChild(r); };
  if (e && e.material) row("material", nameEl("span", null, e.material));
  else if (p.material) row("material", nameEl("span", null, p.material));
  if (e){
    if (e.mass) row("mass", num8(e.mass.v, "g", e.mass.src, e.mass.note || ""));
    const mt = e.mat && e.mat.density;
    if (mt && e.volume) row("solid", num8(e.volume.v/1000*mt.v, "g", "CALC", "CAD volume " + fmt8(e.volume.v, 0) + " mm³ × ρ " + mt.v + " g/cm³ (" + mt.src + ")"));
    if (e.slicer) row("print", num8(e.slicer.time_min.v, "min", "SLICER", e.slicer.slicer || ""));
    else if (e.kind === "printed") row("print", num8(null, "min", "ASSUMED"));
  } else if (p.print && p.print.time_min){ row("print", num8(p.print.time_min, "min", "SLICER")); }
  return box;
}
function ensureTip(){ if (!tipEl){ tipEl = el("div", "v8tipbox"); tipEl.style.display = "none"; $("stage").appendChild(tipEl); } return tipEl; }
function showTip(p, x, y){
  ensureTip();
  showEl(tipEl, !!p);
  if (!p) return;
  if (tipEl.dataset.k !== p.id){ tipEl.dataset.k = p.id; tipEl.textContent = ""; tipEl.appendChild(tipFor(p)); }
  const r = $("stage").getBoundingClientRect(), w = tipEl.offsetWidth || 180, h = tipEl.offsetHeight || 80;
  const tx = Math.max(6, Math.min(r.width - w - 6, x + 14)), ty = Math.max(6, Math.min(r.height - h - 6, y + 14));
  tipEl.style.transform = `translate(${Math.round(tx)}px,${Math.round(ty)}px)`;
}
cv.addEventListener("pointermove", e => {
  if (e.pointerType !== "mouse" || e.buttons || !ENG || V8.calOn) return;
  const t = performance.now(); if (t - hovT < 70) return; hovT = t;
  const r = cv.getBoundingClientRect(), x = e.clientX - r.left, y = e.clientY - r.top;
  const h = raycast(x, y, true), id = h ? h.part.id : null;
  if (id !== V8.hover){ V8.hover = id; draw(); }
  showTip(h ? h.part : null, x, y);
});
cv.addEventListener("pointerleave", e => { if (e.pointerType !== "mouse") return; if (V8.hover){ V8.hover = null; draw(); } showTip(null); });   /* a touch "leaves" after every tap */
syncUI = (orig => function(){
  orig();
  if (!ENG || !tipEl) return;
  const p = lastSel();
  if (p && V8.phase === "load" && !wide()){ const s = project(lastMVP8(), partCentre(p), cv.width/curDpr, cv.height/curDpr); if (s) showTip(p, s[0], s[1]); }
  else if (!V8.hover) showTip(null);
})(syncUI);
function lastMVP8(){
  const r = cv.getBoundingClientRect(), V = M.look(eye(), target(), [0, 0, 1]), P = M.persp(FOV, r.width/r.height, 1, 2000);
  skewY(P); return M.mul(P, V);
}

/* ===========================================================================
   R38 — PHASES
   =========================================================================== */
const PHASES = [["load", "LOAD"], ["fit", "FIT"], ["secure", "SECURE"], ["test", "TEST"]];
const phaseOK = ph => ENG && (!ENG.phases || ENG.phases.includes(ph)) && (ph !== "test" || (MO && MD)) && (ph !== "secure" || NSTEP > 0);
function syncPhaseBar(){
  const bar = $("v8phase"); if (!bar) return;
  let past = true;
  for (const b of bar.querySelectorAll("button")){
    const here = b.dataset.ph === V8.phase;
    if (here){ b.setAttribute("aria-current", "step"); past = false; } else b.removeAttribute("aria-current");
    b.classList.toggle("done", past && !!V8.phase);
    b.disabled = !phaseOK(b.dataset.ph);
  }
}
/* leaving through the dock (BOM, Plate, …) ends the guided phase */
goTab = (orig => function(tab){
  if (!V8.inPhase && V8.phase){ V8.phase = null; V8.heat = false; V8.tol = false; V8.xray = V8.wire = false; if (V8.calOn) setCal(false); syncPhaseBar(); syncToggles(); }
  return orig(tab);
})(goTab);
function setPhase(ph, opt){
  opt = opt || {};
  if (!phaseOK(ph)) return false;
  V8.phase = ph; V8.inPhase = true;
  try { enterPhase(ph, opt); } finally { V8.inPhase = false; }
  syncPhaseBar(); syncToggles(); writeHash(); draw();
  return true;
}
function enterPhase(ph, opt){
  if (ph !== "fit"){ if (V8.calOn) setCal(false); V8.tol = false; }
  if (ph !== "test" && !opt.restore){ V8.xray = V8.wire = false; }   /* their toggles live on the TEST card only */
  if (ph === "load") ensureTip();
  V8.heat = ph === "test";
  if (ph !== "load") showTip(null);
  if (ph === "load"){
    goTab("parts"); openSheet("phase"); renderLoad();
    if (!opt.restore) glide({explode: 0});
  } else if (ph === "fit"){
    goTab("parts"); openSheet("phase"); V8.tol = true; renderFit();
    if (!opt.restore) glide({explode: V8.spacing/EXK}, 520);
  } else if (ph === "secure"){
    goTab("build");
    if (!opt.restore){ glide({explode: 0}, 300); gotoStep(1); if (!V7RM()) setTimeout(() => { if (V8.phase === "secure" && !playing) togglePlay(); }, 450); }
  } else if (ph === "test"){
    moTab = "path"; goTab("motion"); syncLoad();
  }
}
(function phaseBar(){
  const bar = $("v8phase"); if (!bar) return;
  if (!ENG){ bar.hidden = true; return; }
  for (const [ph, lab] of PHASES){
    const b = el("button"); b.dataset.ph = ph; b.type = "button";
    const i = document.createElement("i"); i.textContent = String(PHASES.findIndex(x => x[0] === ph) + 1);
    b.append(i, document.createTextNode(lab));
    b.addEventListener("click", () => { setPhase(ph); buzz(6); });
    bar.appendChild(b);
  }
  syncPhaseBar();
})();
/* phase panels don't need the scrim: the model stays touchable under them */
openSheet = (orig => function(tab){
  orig(tab);
  if (tab === "phase" || tab === "tree"){ scrim.classList.remove("open"); document.body.classList.add("moSheet"); }
  else if (!motionMode) document.body.classList.remove("moSheet");
})(openSheet);

/* ---- LOAD panel ---- */
function kpi8(lab, node, cls){ const d = el("div", "kpi" + (cls ? " " + cls : "")); d.appendChild(nameEl("div", "k", lab)); const v = el("div", "v"); v.appendChild(node); d.appendChild(v); return d; }
function missingCard(box){
  if (!(ENG.missing && ENG.missing.length)) return;
  const c = el("div", "v8warn"); c.appendChild(nameEl("span", "v8miss", "MISSING " + ENG.missing.length));
  const l = el("div"); for (const m of ENG.missing.slice(0, 8)) l.appendChild(nameEl("div", null, m.path + " — " + m.why)); c.appendChild(l); box.appendChild(c);
}
function renderLoad(){
  shTitle.textContent = "LOAD · " + (ENG.assembly.name || "");
  shBody.textContent = "";
  const box = engBox(); shBody.appendChild(box);
  missingCard(box);
  const pr = Object.entries(ENG.parts).filter(([, e]) => e.slicer);
  const g = pr.reduce((a, [, e]) => a + e.slicer.grams.v, 0), t = pr.reduce((a, [, e]) => a + e.slicer.time_min.v, 0);
  const k = el("div", "kpis"); k.style.gridTemplateColumns = "repeat(3,1fr)";
  k.appendChild(kpi8("Parts", num8(parts.filter(p => p.kind !== "wire").length, "", "CAD", "parts in the assembly", 0)));
  k.appendChild(kpi8("Filament", num8(g, "g", "SLICER", ENG.slicer ? ENG.slicer.name : ""), "accent"));
  k.appendChild(kpi8("Print", num8(t/60, "h", "SLICER", "sum of per-part G-code estimates", 1)));
  box.appendChild(k);
  const list = el("div", "v8card"); list.appendChild(nameEl("h3", null, "Tap a part · hover on desktop"));
  for (const p of parts.filter(q => q.kind !== "wire")){
    const e = ENG.parts[p.id]; if (!e) continue;
    const r = el("div", "v8row"); r.style.cursor = "pointer";
    const nm = el("button", "lb lnk"); nm.dataset.nonum = "1";
    const sw = el("span", "sw"); sw.style.cssText = `display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:7px;background:${p.color}`;
    nm.append(sw, document.createTextNode(p.label));
    nm.addEventListener("click", () => { pickPart(p, false); fitParts([p]); renderInspector(p); });
    const vl = el("div", "vl"); vl.appendChild(num8(e.mass.v, "g", e.mass.src, e.mass.note || ""));
    r.append(nm, vl);
    if (e.slicer){ const s = el("div", "sub"); s.appendChild(nameEl("span", null, "print ")); s.appendChild(num8(e.slicer.time_min.v, "min", "SLICER", e.slicer.slicer)); r.appendChild(s); }
    list.appendChild(r);
  }
  box.appendChild(list);
  box.appendChild(sourceKey());
  box.appendChild(footer8());
}
function sourceKey(){
  const c = el("div", "v8card"); c.appendChild(nameEl("h3", null, "Where every number comes from"));
  for (const [k, v] of Object.entries(SRC_TXT)){ const r = el("div", "v8row"); const a = el("div", "lb"); a.appendChild(srcEl(k)); a.appendChild(nameEl("span", null, " " + v)); r.appendChild(a); c.appendChild(r); }
  return c;
}
function footer8(){ const f = nameEl("div", "empty", BRAND.footer); f.style.cssText = "text-align:center;font:10px var(--f-mono);color:var(--faint);padding:8px 0 16px"; return f; }

/* ---- FIT panel: spacing, caliper, rings, fits table, stack-ups, calculator ---- */
function slider8(lab, min, max, step, val, fmtv, on){
  const w = el("div", "v8sl"); const l = nameEl("label", null, lab); const i = document.createElement("input");
  i.type = "range"; i.min = min; i.max = max; i.step = step; i.value = val; i.setAttribute("aria-label", lab);
  const o = el("span"); const paint = () => { o.textContent = ""; o.appendChild(fmtv(+i.value)); };
  i.addEventListener("input", () => { on(+i.value); paint(); });
  paint(); w.append(l, i, o); return {w, i, paint};
}
function renderFit(){
  shTitle.textContent = "FIT · tolerances";
  shBody.textContent = "";
  const box = engBox(); shBody.appendChild(box);
  const c1 = el("div", "v8card"); c1.appendChild(nameEl("h3", null, "Explode"));
  const sp = slider8("Spacing", 0, 50, 1, V8.spacing, v => num8(v, "mm", "SPEC", "explode = spacing ÷ " + EXK + " mm", 0), v => {
    V8.spacing = v; explode = v/EXK; $("ex").value = Math.round(Math.min(1, explode)*100); $("exv").textContent = Math.round(explode*100) + "%"; draw(); writeHash(); });
  c1.appendChild(sp.w);
  const bt = el("div", "v8btns");
  const bc = el("button", "btn", "Caliper"); bc.id = "v8CalBtn"; bc.addEventListener("click", () => setCal(!V8.calOn));
  const bt2 = el("button", "btn", "Tolerance rings"); bt2.id = "v8Tol"; bt2.addEventListener("click", () => { V8.tol = !V8.tol; syncToggles(); draw(); writeHash(); });
  bt.append(bc, bt2); c1.appendChild(bt); box.appendChild(c1);
  /* fits table */
  const T = ENG.tolerance;
  const c2 = el("div", "v8card"); c2.appendChild(nameEl("h3", null, "Fits · profile " + T.profile + " (" + T.src + ")"));
  for (const f of fits8()){
    const r = el("div", "v8row"); r.dataset.fit = f.id;
    const nm = el("button", "lb lnk"); nm.dataset.nonum = "1";
    const ic = {green: "✓", yellow: "!", red: "✗"}[f.band.tone] || "?";
    const dot = nameEl("span", null, ic + " "); dot.style.color = f.band.color;
    nm.append(dot); if (f.kind === "hole"){ nm.appendChild(num8(f.cad.v, "mm", "CAD", "CAD diameter", 2)); nm.appendChild(document.createTextNode(" ")); }
    nm.appendChild(document.createTextNode(f.label + " · " + f.part));
    nm.addEventListener("click", () => { V8.fitSel = f.id; flyTo(f.at, byId.get(f.part)); });
    const vl = el("div", "vl"); vl.appendChild(num8(f.clr, "mm", "CALC", "clearance = " + (f.measuredJS != null ? "measured" : "printed (" + f.psrc + ")") + " − " + f.mate, 2));
    const sub = el("div", "sub");
    const cadV = f.kind === "rect" ? f.cad.v.join("×") : f.cad.v, prV = f.kind === "rect" ? f.printedJS.map(x => x.toFixed(2)).join("×") : f.printedJS;
    sub.appendChild(nameEl("span", null, "CAD ")); sub.appendChild(num8(cadV, "", "CAD"));
    sub.appendChild(nameEl("span", null, " → printed ")); sub.appendChild(num8(prV, "", "CALC", "cad + profile (" + f.psrc + ")"));
    sub.appendChild(nameEl("span", null, " → measured ")); sub.appendChild(num8(f.measuredJS, "", "MEASURED"));
    sub.appendChild(nameEl("span", null, " · mate ")); sub.appendChild(num8(f.kind === "rect" ? f.mate_size.v.join("×") : f.mate_size.v, "", f.mate_size.src));
    sub.appendChild(nameEl("span", null, " · " + f.band.label));
    r.append(nm, vl, sub); c2.appendChild(r);
  }
  box.appendChild(c2);
  /* stack-ups */
  for (const st of (ENG.stackups || [])) box.appendChild(stackCard(st));
  box.appendChild(calcCard());
  if (ENG.kind === "coupon") box.appendChild(couponCard());
  box.appendChild(footer8());
  syncToggles();
}
function stackCard(st){
  const c = el("div", "v8card"); c.dataset.stack = st.id; c.appendChild(nameEl("h3", null, "Stack-up · " + st.label));
  const mx = Math.max(...st.links.map(l => Math.abs(l.t)), 1e-6);
  const bars = el("div", "v8bars");
  for (const l of [...st.links].sort((a, b) => Math.abs(b.t) - Math.abs(a.t))){
    const w = el("div"); w.appendChild(nameEl("div", "nm", l.name));
    const b = el("div", "bt" + (l.name === st.eats ? " top" : "")); b.style.width = Math.max(2, 100*Math.abs(l.t)/mx) + "%"; w.appendChild(b);
    const v = el("div", "vl"); v.appendChild(num8(l.t, "mm", l.src, "tolerance ± on this link", 2));
    bars.append(w, v);
  }
  c.appendChild(bars);
  /* range diagram: want band, worst case, RSS, nominal */
  const lo = Math.min(st.want.min, st.worst[0]) - 0.1, hi = Math.max(Math.min(st.want.max, st.worst[1] + 1), st.worst[1]) + 0.1;
  const X = v => (100*(v - lo)/(hi - lo)).toFixed(2) + "%";
  const rg = el("div", "v8range"); rg.setAttribute("role", "img");
  rg.setAttribute("aria-label", `want ${st.want.min} to ${st.want.max}, worst ${st.worst[0]} to ${st.worst[1]}, RSS ${st.rss[0]} to ${st.rss[1]}`);
  const add8 = (cls, a, b) => { const d = el("div", cls); d.style.left = X(a); if (b != null) d.style.width = `calc(${X(b)} - ${X(a)})`; rg.appendChild(d); };
  add8("want", Math.max(lo, st.want.min), Math.min(hi, st.want.max)); add8("wc", st.worst[0], st.worst[1]); add8("rs", st.rss[0], st.rss[1]); add8("nom", st.nominal);
  c.appendChild(rg);
  const k = el("div", "kpis"); k.style.gridTemplateColumns = "repeat(3,1fr)";
  k.appendChild(kpi8("Nominal", num8(st.nominal, "mm", "CALC", "Σ nominal", 2)));
  k.appendChild(kpi8("Worst min", num8(st.worst[0], "mm", "CALC", "nominal − Σ|tᵢ|", 2), st.ok_worst ? "" : "bad"));
  k.appendChild(kpi8("RSS min", num8(st.rss[0], "mm", "CALC", "nominal − √Σtᵢ²", 2), st.ok_rss ? "" : "bad"));
  c.appendChild(k);
  const eat = el("div", "sub"); eat.style.cssText = "font-size:12px;color:var(--mut);margin-top:6px";
  eat.appendChild(nameEl("span", null, "eats most: " + st.eats + " · want "));
  eat.appendChild(num8(st.want.min, "", st.want.src || "SPEC", st.want.note || "", 2)); eat.appendChild(nameEl("span", null, " … "));
  eat.appendChild(num8(st.want.max, "mm", st.want.src || "SPEC", st.want.note || "", 2));
  c.appendChild(eat);
  return c;
}
function calcCard(){
  const c = el("div", "v8card"); c.appendChild(nameEl("h3", null, "Fit calculator · CAD → printed → measured → class"));
  const row = el("div", "v8btns"); row.style.alignItems = "center";
  const mk = (ph, v) => { const i = document.createElement("input"); i.type = "number"; i.step = "0.01"; i.placeholder = ph; i.value = v == null ? "" : v;
                          i.setAttribute("aria-label", ph); i.style.cssText = "width:88px;min-height:44px;padding:0 8px;border-radius:8px;border:1px solid var(--line);background:var(--ground);color:var(--ink);font:13px var(--f-mono)"; return i; };
  const iC = mk("CAD Ø", 3.4), iMate = mk("mate Ø", 3.0), iM = mk("measured Ø", null);
  const sel8 = document.createElement("select"); sel8.setAttribute("aria-label", "purpose");
  sel8.style.cssText = "min-height:44px;border-radius:8px;border:1px solid var(--line);background:var(--ground);color:var(--ink);font:13px var(--f-mono);padding:0 6px";
  for (const p of Object.keys(ENG.tolerance.bands)){ const o = document.createElement("option"); o.value = p; o.textContent = p.replace("_", " "); sel8.appendChild(o); }
  row.append(iC, iMate, iM, sel8); c.appendChild(row);
  const out = el("div"); out.id = "v8calcOut"; out.style.marginTop = "8px"; c.appendChild(out);
  const paint = () => {
    out.textContent = "";
    const cad = +iC.value, mate = +iMate.value, meas = iM.value === "" ? null : +iM.value;
    if (!(cad > 0 && mate > 0)) return;
    const [pr, psrc] = printed8(cad, "hole"), basis = meas == null ? pr : meas, clr = basis - mate, b = band8(sel8.value, clr);
    const r = el("div", "v8row");
    const a = el("div", "lb"); a.appendChild(nameEl("span", null, "printed ")); a.appendChild(num8(pr, "mm", "CALC", "cad + a + b/cad · profile " + psrc, 3));
    const v = el("div", "vl"); v.appendChild(num8(clr, "mm", meas == null ? "CALC" : "MEASURED", "basis − mate", 3));
    const s = el("div", "sub"); const ic = {green: "✓", yellow: "!", red: "✗"}[b.tone]; const d = nameEl("span", null, ic + " " + b.label); d.style.color = b.color; s.appendChild(d);
    r.append(a, v, s); out.appendChild(r);
  };
  for (const i of [iC, iMate, iM, sel8]) i.addEventListener("input", paint);
  paint();
  return c;
}
function couponCard(){
  const c = el("div", "v8card"); c.appendChild(nameEl("h3", null, "Your measurements → shared in the link"));
  for (const h of ENG.tolerance.coupon){
    const r = el("div", "v8btns"); r.style.alignItems = "center";
    const lb = num8(h.cad, "", "CAD", "CAD hole diameter", 1); lb.style.cssText = "width:96px;font:13px var(--f-mono)";
    const i = document.createElement("input"); i.type = "number"; i.step = "0.01"; i.placeholder = "measured";
    i.value = V8.measured[h.cad] != null ? V8.measured[h.cad] : (h.measured != null ? h.measured : "");
    i.setAttribute("aria-label", "measured Ø" + h.cad);
    i.style.cssText = "width:110px;min-height:44px;padding:0 8px;border-radius:8px;border:1px solid var(--line);background:var(--ground);color:var(--ink);font:13px var(--f-mono)";
    i.addEventListener("change", () => {
      if (i.value === "") delete V8.measured[h.cad]; else V8.measured[h.cad] = +i.value;
      for (const f of ENG.fits) if (Math.abs(f.cad.v - h.cad) < 1e-6){ if (i.value === "") delete V8.measured[f.id]; else V8.measured[f.id] = +i.value; }
      writeHash(); draw(); renderFit();
    });
    r.append(lb, i); c.appendChild(r);
  }
  return c;
}
function flyTo(at, p){
  const w = p ? M.xform(modelOf(p), at) : at;
  if (p){ sel.clear(); sel.add(p.id); syncUI(); }
  const base = sub(target(), PAN);
  glide({pan: sub(w, base), dist: Math.max(HOME.dist*0.32, _bb*0.8)}, 420);
}

/* ---- SECURE: a card on top of the Build panel ---- */
showBuild = (orig => function(){
  orig();
  if (V8.phase !== "secure" || !ENG) return;
  const c = engBox(); c.className = "v8card";
  c.appendChild(nameEl("h3", null, "SECURE · auto-assembly from the sequence"));
  const mat = ENG.materials && ENG.materials.PETG, ins = (ENG.inserts || [])[0];
  const r1 = el("div", "v8row"); const a1 = el("div", "lb"); a1.appendChild(nameEl("span", null, "🔥 Insert iron (" + ((ins && ins.spec) || "M3×5.7") + ")"));
  const v1 = el("div", "vl"); const ic = (ins && ins.iron_c) || (mat && mat.iron_c); if (ic) v1.appendChild(num8(ic.v, "°C", ic.src, ic.note || "", 0));
  r1.append(a1, v1); c.appendChild(r1);
  for (const f of (ENG.fasteners || []).filter((f, i, a) => a.findIndex(g => g.spec === f.spec) === i)){
    const r = el("div", "v8row"); const a = el("div", "lb"); a.appendChild(nameEl("span", null, "⟳ " + f.spec + " · from " + f.side));
    const v = el("div", "vl"); v.appendChild(num8(f.torque.v, "N·m", f.torque.src, f.torque.note || "", 2));
    r.append(a, v); c.appendChild(r);
  }
  shBody.prepend(c);
})(showBuild);

/* ---- TEST: load slider, meter, stall warning, heat legend, ranking, fix, chart, toggles ---- */
function syncLoad(){
  if (!MD) return;
  const R = calc8();
  V8.R = R;
  /* the Motion lane feels the same load: the test weight's mass + where it hangs */
  const w = byId.get("weight");
  if (w && w.mass){ w.mass = {...w.mass, g: V8.kg*1000, com: com8("weight", V8.lever)}; }
  /* heat: σ ÷ strength (servo: τ ÷ stall) */
  HEAT = new Map();
  const x0 = MD.arm_root.x_from_shaft, o = o8();
  const u = MD.arm_dir;
  HEAT.set("arm", {o: [o[0] + x0*u[0], 0, o[2] + x0*u[2]], d: u, L: Math.max(0.5, V8.lever - x0), s0: R.arm.vm/MD.yield_xy, s1: 0});
  HEAT.set("cradle", {o: [0, 0, 0], d: [1, 0, 0], L: 1, s0: R.wall.vm/R.wall.strength, s1: R.wall.vm/R.wall.strength});
  HEAT.set("servo", {o: [0, 0, 0], d: [1, 0, 0], L: 1, s0: R.frac_hold, s1: R.frac_hold});
  for (const id of ["tab0", "tab1"]) HEAT.set(id, {o: [0, 0, 0], d: [1, 0, 0], L: 1, s0: 1/R.tabs.sf, s1: 1/R.tabs.sf});
  draw();
}
function testCard(){
  const R = V8.R || calc8();
  const c = engBox(); c.className = "v8card"; c.id = "v8test";
  c.appendChild(nameEl("h3", null, "TEST · load the arm"));
  const live = el("div"); live.id = "v8live";
  const s1 = slider8("Load", MD.kg.min, MD.kg.max, MD.kg.step, V8.kg, v => num8(v, "kg", "SPEC", "", 2), v => { V8.kg = v; syncLoad(); paintLive(live); writeHash(); });
  const s2 = slider8("Lever", MD.lever.min, MD.lever.max, MD.lever.step, V8.lever, v => num8(v, "mm", "SPEC", "", 1), v => { V8.lever = v; syncLoad(); paintLive(live); writeHash(); });
  s1.i.id = "v8kg"; s2.i.id = "v8lev";
  c.append(s1.w, s2.w, live);
  paintLive(live);
  const tg = el("div", "v8btns");
  const sw = el("button", "btn pri", "▶ Sweep"); sw.id = "v8Sweep"; sw.addEventListener("click", sweep8);
  const xr = el("button", "btn", "X-ray"); xr.id = "v8Xray"; xr.addEventListener("click", () => setXray(!V8.xray));
  const wf = el("button", "btn", "Wireframe"); wf.id = "v8Wire"; wf.addEventListener("click", () => setWire(!V8.wire));
  tg.append(sw, xr, wf); c.appendChild(tg);
  /* section-cut slider with capped faces */
  const sc = el("div"); sc.style.marginTop = "8px";
  const ax = el("div", "v8btns");
  for (const [i, a] of [[0, "X"], [1, "Y"], [2, "Z"]]){ const b = el("button", "btn", "Cut " + a); b.dataset.nonum = "1"; b.setAttribute("aria-pressed", String(sectOn && sectAxis === i));
    b.addEventListener("click", () => { if (!sectOn) $("bSect").click(); sectAxis = i; syncSect(); testRefresh(); writeHash(); }); ax.appendChild(b); }
  const off = el("button", "btn", "No cut"); off.addEventListener("click", () => { if (sectOn) $("bSect").click(); testRefresh(); writeHash(); }); ax.appendChild(off);
  sc.appendChild(ax);
  const ss = slider8("Section", 0, 1000, 1, Math.round(sectT*1000), v => num8(sectOn ? sectValue() : null, "mm", "CAD", "cut-plane position along the axis", 1),
                     v => { if (!sectOn) $("bSect").click(); sectT = v/1000; $("sec").value = v; syncSect(); writeHash(); });
  ss.i.id = "v8sec"; sc.appendChild(ss.w); c.appendChild(sc);
  syncToggles();
  return c;
}
function testRefresh(){ if (V8.phase === "test" && motionMode) showMotion(); }
function paintLive(box){
  const R = V8.R || calc8(); box.textContent = "";
  const stallK = MD.stall_nmm/KGCM8, tk = R.tau_hold/KGCM8;
  /* torque meter */
  const mrow = el("div", "v8row");
  const a = el("div", "lb"); a.appendChild(nameEl("span", null, "SG90 holding torque "));
  const v = el("div", "vl"); v.appendChild(num8(tk, "kgf·cm", "CALC", "τ = g·Σ mᵢ·(xᵢ cosθ − zᵢ sinθ), worst θ", 2));
  mrow.append(a, v); box.appendChild(mrow);
  const mt = el("div", "v8meter"); mt.setAttribute("role", "img"); mt.setAttribute("aria-label", `${(R.frac_hold*100).toFixed(0)} percent of stall`);
  const fill = document.createElement("i"); fill.style.width = Math.min(100, R.frac_hold*100) + "%"; if (R.frac_hold > 1) fill.className = "over"; mt.appendChild(fill);
  for (const [f, t] of [[MD.targets.hold_frac, (MD.targets.hold_frac*100).toFixed(0) + " %"], [MD.targets.dyn_frac, (MD.targets.dyn_frac*100).toFixed(0) + " %"], [1, "stall"]]){
    const u = document.createElement("u"); u.style.left = (f*100) + "%"; const sp = document.createElement("span"); sp.textContent = t; sp.className = "num"; sp.dataset.src = f >= 1 ? "DATASHEET" : "SPEC";
    if (f >= 1){ sp.style.left = "auto"; sp.style.right = "0"; } u.appendChild(sp); mt.appendChild(u); }
  box.appendChild(mt);
  if (R.frac_hold > 1){
    const w = el("div", "v8warn"); w.id = "v8stall"; w.dataset.eng = "1";
    w.appendChild(nameEl("b", null, "✗"));
    const t = el("div"); t.appendChild(nameEl("b", null, "SG90 stalls. ")); t.appendChild(nameEl("span", null, "Needs "));
    t.appendChild(num8(tk, "kgf·cm", "CALC")); t.appendChild(nameEl("span", null, ", has ")); t.appendChild(num8(stallK, "kgf·cm", "DATASHEET", "", 1));
    t.appendChild(nameEl("span", null, ". The bracket survives it: arm SF at stall ")); t.appendChild(num8(R.arm_at_stall.sf, "", "CALC", "arm σ_vm at the stall load", 1));
    w.appendChild(t); box.appendChild(w);
  } else if (R.frac_hold > MD.targets.hold_frac){
    const w = el("div", "v8warn soft"); w.id = "v8stall"; w.appendChild(nameEl("b", null, "!"));
    const t = el("div"); t.appendChild(nameEl("span", null, "Above the continuous-duty rule (")); t.appendChild(num8(MD.targets.hold_frac*100, "% stall", "SPEC", "", 0)); t.appendChild(nameEl("span", null, ") — servos cook near stall. "));
    t.appendChild(num8(R.frac_hold*100, "% stall", "CALC", "", 0)); w.appendChild(t); box.appendChild(w);
  }
  /* heat legend */
  const lg = el("div", "v8leg"); lg.dataset.eng = "1";
  lg.appendChild(el("div", "rmp")); const ov = el("span", "ov"); ov.appendChild(document.createElement("i")); ov.appendChild(nameEl("span", null, "✗ over")); lg.appendChild(ov);
  const tk2 = el("div", "ticks"); for (const t of ["0", "50", "100 % of strength"]) tk2.appendChild(nameEl("span", null, t)); lg.appendChild(tk2);   /* scale ticks, not data */
  const cap = nameEl("div", null, "colour = σ_vm ÷ strength (servo: τ ÷ stall) · CALC"); cap.style.cssText = "grid-column:1/-1;font-size:10.5px"; lg.appendChild(cap);
  box.appendChild(lg);
  /* ranking */
  box.appendChild(rankCard(R));
  box.appendChild(chartCard(R));
}
function ranking8(R){
  const items = [
    {id: "servo", label: "SG90 stalls (torque)", sf: MD.stall_nmm/Math.max(1e-9, R.tau_hold), where: MD.shaft.origin, part: "servo", src: "DATASHEET", f: "stall ÷ holding torque"},
    {id: "arm", label: "Arm root snaps (bending, sharp step)", sf: R.arm.sf, where: MD.arm_root.point, part: "arm", src: "CALC", f: "yield ÷ σ_vm (Kt " + R.arm.kt.toFixed(2) + ")"},
    {id: "wall", label: "Cradle wall root peels (Z)", sf: R.wall.sf, where: MD.wall_root.point, part: "cradle", src: "CALC", f: "z·yield ÷ Kt·σ"},
    {id: "tabs", label: "Tab screws strip out", sf: R.tabs.sf, where: (ENG.ranking.find(r => r.id === "tabs") || {}).where, part: "tab0", src: "CALC", f: "0.577·z·yield ÷ thread shear"},
  ].sort((a, b) => a.sf - b.sf);
  items.push({id: "inserts", label: "M3 inserts pull out", sf: null, where: (ENG.ranking.find(r => r.id === "inserts") || {}).where, part: "ins_a", src: "ASSUMED", f: "no pull-out data — MEASURE_ME", F: R.inserts.F});
  return items;
}
function rankCard(R){
  const c = el("div"); c.style.marginTop = "6px"; c.id = "v8rank";
  c.appendChild(nameEl("h3", null, "What breaks first?")).style.cssText = "margin:10px 0 4px;font:700 11px var(--f-mono);letter-spacing:.08em;color:var(--mut)";
  ranking8(R).forEach((it, i) => {
    const r = el("div", "v8row"); r.dataset.rank = it.id;
    const b = el("button", "lb lnk"); b.dataset.nonum = "1"; b.textContent = (i + 1) + ". " + it.label;
    b.addEventListener("click", () => { const p = byId.get(it.part); if (it.where) flyTo(it.where, p); if (it.id === "arm") showFix(c, R); });
    const v = el("div", "vl");
    if (it.sf == null){ v.appendChild(num8(it.F, "N each", "CALC", "", 2)); }
    else v.appendChild(num8(it.sf, "SF", it.src, it.f, it.sf >= 10 ? 0 : 2));
    r.append(b, v); c.appendChild(r);
  });
  return c;
}
function showFix(c, R){
  let f = c.querySelector(".v8fix"); if (f) f.remove();
  f = el("div", "v8card v8fix"); f.dataset.eng = "1";
  f.appendChild(nameEl("h3", null, "Fix · fillet the arm root"));
  const S = MD.sections.arm_root, kb = kgBreak8(V8.lever, S.r), ka = kgBreak8(V8.lever, S.r_fix);
  const bars = el("div", "v8bars"); const mx = Math.max(R.arm.kt, R.arm_fix.kt);
  for (const [lab, kt, r] of [["sharp r " + S.r + " (v1)", R.arm.kt, S.r], ["fillet r " + S.r_fix, R.arm_fix.kt, S.r_fix]]){
    const w = el("div"); w.appendChild(nameEl("div", "nm", lab)); const b = el("div", "bt" + (r === S.r ? " top" : "")); b.style.width = (100*kt/mx) + "%"; w.appendChild(b);
    const v = el("div", "vl"); v.appendChild(num8(kt, "Kt", "CALC", "Peterson stepped bar in bending: Kt = A·(r/d)^b, D/d = " + (S.D/S.d).toFixed(2), 2)); bars.append(w, v);
  }
  f.appendChild(bars);
  const k = el("div", "kpis"); k.style.gridTemplateColumns = "repeat(2,1fr)";
  k.appendChild(kpi8("Breaks at · sharp", num8(kb, "kg", "CALC", "load where arm SF = 1, sharp step", 2), "bad"));
  k.appendChild(kpi8("Breaks at · fillet", num8(ka, "kg", "CALC", "load where arm SF = 1, r " + S.r_fix + " fillet", 2), "accent"));
  f.appendChild(k);
  c.appendChild(f);
}
function chartCard(R){
  const c = el("div", "v8chartw"); c.dataset.eng = "1"; c.style.marginTop = "8px";
  c.appendChild(nameEl("h3", null, "Holding torque over the sweep (kgf·cm)")).style.cssText = "margin:10px 0 4px;font:700 11px var(--f-mono);letter-spacing:.08em;color:var(--mut)";
  const W = 340, H = 130, L = 34, Rr = 8, T = 8, B = 22;
  const [lo, hi] = MD.limits, pts = [];
  for (let th = lo; th <= hi; th += 2) pts.push([th, Math.abs(tau8(V8.kg, V8.lever, th))/KGCM8]);
  const stallK = MD.stall_nmm/KGCM8, ymax = Math.max(stallK*1.15, ...pts.map(p => p[1]), 0.1);
  const X = th => L + (th - lo)/(hi - lo)*(W - L - Rr), Y = v => T + (1 - v/ymax)*(H - T - B);
  const s = document.createElementNS(SVGNS8, "svg"); s.setAttribute("viewBox", `0 0 ${W} ${H}`); s.setAttribute("class", "v8chart");
  s.setAttribute("role", "img"); s.setAttribute("aria-label", "holding torque versus arm angle, CALC, with the SG90 stall line");
  const mk = (tag, at) => { const e = document.createElementNS(SVGNS8, tag); for (const k in at) e.setAttribute(k, at[k]); s.appendChild(e); return e; };
  for (const v of [0, ymax/2, ymax]) mk("line", {x1: L, x2: W - Rr, y1: Y(v), y2: Y(v), class: "gl"});
  mk("line", {x1: L, x2: W - Rr, y1: Y(0), y2: Y(0), class: "ax"});
  mk("line", {x1: L, x2: W - Rr, y1: Y(stallK), y2: Y(stallK), class: "ref"});
  mk("line", {x1: L, x2: W - Rr, y1: Y(stallK*MD.targets.hold_frac), y2: Y(stallK*MD.targets.hold_frac), class: "ref2"});
  mk("text", {x: W - Rr, y: Y(stallK) - 4, "text-anchor": "end", class: "num", "data-src": "DATASHEET"}).textContent = "stall " + stallK.toFixed(1) + " DATASHEET";
  mk("text", {x: W - Rr, y: Y(stallK*MD.targets.hold_frac) - 4, "text-anchor": "end", class: "num", "data-src": "SPEC"}).textContent = (MD.targets.hold_frac*100).toFixed(0) + " % SPEC";
  for (const th of [lo, 0, hi]) mk("text", {x: X(th), y: H - 6, "text-anchor": "middle", "data-nonum": "1"}).textContent = th + "°";
  mk("text", {x: L - 4, y: Y(ymax) + 4, "text-anchor": "end", "data-nonum": "1"}).textContent = ymax.toFixed(1);
  mk("text", {x: L - 4, y: Y(0) + 4, "text-anchor": "end", "data-nonum": "1"}).textContent = "0";
  mk("path", {d: "M" + pts.map(p => X(p[0]).toFixed(1) + "," + Y(p[1]).toFixed(1)).join(" L"), class: "ln"});
  const hv = mk("line", {x1: 0, x2: 0, y1: T, y2: H - B, class: "hov", visibility: "hidden"}), dot = mk("circle", {r: 4, cx: 0, cy: 0, visibility: "hidden"});
  const tip = el("div", "v8tip"); tip.hidden = true; c.append(s, tip);
  const move = e => {
    const r = s.getBoundingClientRect(), x = (e.clientX - r.left)/r.width*W;
    const th = Math.max(lo, Math.min(hi, Math.round((x - L)/(W - L - Rr)*(hi - lo) + lo))), v = Math.abs(tau8(V8.kg, V8.lever, th))/KGCM8;
    hv.setAttribute("x1", X(th)); hv.setAttribute("x2", X(th)); hv.setAttribute("visibility", "visible");
    dot.setAttribute("cx", X(th)); dot.setAttribute("cy", Y(v)); dot.setAttribute("visibility", "visible");
    tip.hidden = false; tip.textContent = ""; tip.appendChild(nameEl("span", null, th + "° · ")); tip.appendChild(num8(v, "kgf·cm", "CALC", "", 2));
    tip.style.left = (X(th)/W*r.width) + "px"; tip.style.top = (Y(v)/H*r.height + 20) + "px";
  };
  s.addEventListener("pointermove", move); s.addEventListener("pointerdown", move);
  s.addEventListener("pointerleave", () => { hv.setAttribute("visibility", "hidden"); dot.setAttribute("visibility", "hidden"); tip.hidden = true; });
  return c;
}
function sweep8(){
  if (!motionMode) setPhase("test");
  if (moTab !== "path"){ moTab = "path"; showMotion(); }
  let n = 0;
  const go = () => { const b = $("pPlay"); if (b && !b.disabled){ if (!(pathView && pathView.playing)) b.click(); return; } if (++n < 60) setTimeout(go, 100); };
  go();
}
showMotion = (orig => function(){
  orig();
  if (V8.phase === "test" && MD){ shBody.prepend(testCard()); shTitle.textContent = "TEST · " + shTitle.textContent; }
})(showMotion);

/* ===========================================================================
   R53 — CHECKS: every engineering check as a tile, formula + inputs on tap
   =========================================================================== */
showChecks = (orig => function(){
  orig();
  if (!ENG || !ENG.checks || !ENG.checks.length) return;
  const C = liveChecks(V8.R || calc8());
  const box = engBox(); box.id = "v8checks";
  missingCard(box);
  const cnt = s => C.filter(c => c.status === s).length;
  const k = el("div", "kpis"); k.style.gridTemplateColumns = "repeat(5,1fr)";
  for (const [s, lab] of [["pass", "Pass"], ["unverified", "Unverif."], ["warn", "Warn"], ["fail", "Fail"], ["na", "N/A"]])
    k.appendChild(kpi8(lab, num8(cnt(s), "", "CALC", "count of tiles", 0), s === "fail" && cnt(s) ? "bad" : ""));
  box.appendChild(k);
  for (const g of [...new Set(C.map(c => c.group))]){
    const card = el("div", "v8card"); card.appendChild(nameEl("h3", null, g));
    for (const c of C.filter(x => x.group === g)){
      const r = el("div", "v8row"); r.dataset.check = c.id; r.dataset.status = c.status;
      const b = el("button", "lb lnk"); b.dataset.nonum = "1"; b.style.minHeight = "44px"; b.textContent = c.label;
      const v = el("div", "vl");
      if (c.status !== "na"){ v.appendChild(num8(c.value, c.unit, "CALC", c.formula)); if (c.limit != null){ v.appendChild(nameEl("span", null, " / ")); v.appendChild(num8(c.limit, "", "SPEC", "limit")); } }
      v.appendChild(document.createTextNode(" ")); v.appendChild(statusPill(c.status));
      const det = el("div", "sub"); det.hidden = true;
      const fm = el("div", "v8f"); fm.dataset.nonum = "1"; fm.textContent = c.formula; det.appendChild(fm);
      for (const i of c.inputs){ const ir = el("div"); ir.appendChild(nameEl("span", null, i.k + " ")); ir.appendChild(num8(i.v, i.u, i.src)); det.appendChild(ir); }
      if (c.note){ const n = nameEl("div", null, c.note); n.style.color = "var(--mut)"; det.appendChild(n); }
      if (c.status === "unverified" && c.assumed.length){ const n = nameEl("div", null, "UNVERIFIED because ASSUMED: " + c.assumed.join(", ")); n.style.color = "var(--warn)"; det.appendChild(n); }
      b.addEventListener("click", () => { det.hidden = !det.hidden; if (!det.hidden && c.where) flyTo(c.where, null); });
      r.append(b, v, det); card.appendChild(r);
    }
    box.appendChild(card);
  }
  if (ENG.measure && ENG.measure.length){
    const m = el("div", "v8card"); m.appendChild(nameEl("h3", null, "MEASURE_ME · sorted by blast radius"));
    ENG.measure.forEach((x, i) => { const r = el("div", "v8row"); r.appendChild(nameEl("div", "lb", (i + 1) + ". " + x.what));
      const v = el("div", "vl"); v.appendChild(num8(x.n, "checks", "CALC", "checks this measurement unlocks", 0)); r.appendChild(v);
      r.appendChild(nameEl("div", "sub", x.tool)); m.appendChild(r); });
    box.appendChild(m);
  }
  shBody.prepend(box);
})(showChecks);

/* ===========================================================================
   R48 — inspector: engineering data + print panel + downloads
   =========================================================================== */
renderInspector = (orig => function(p){
  orig(p);
  if (!ENG || !p) return;
  const e = ENG.parts[p.id]; if (!e) return;
  const box = engBox(); box.className = "v8card"; box.id = "v8eng";
  box.appendChild(nameEl("h3", null, "Engineering data"));
  const row = (k, node, sub) => { const r = el("div", "v8row"); r.appendChild(nameEl("div", "lb", k)); const v = el("div", "vl"); v.appendChild(node); r.appendChild(v);
                                  if (sub){ const s = nameEl("div", "sub", sub); r.appendChild(s); } box.appendChild(r); };
  if (e.mass) row("Mass", num8(e.mass.v, "g", e.mass.src, e.mass.note || ""), e.mass.note);
  if (e.measured_mass) row("Measured mass", num8(e.measured_mass.v, "g", "MEASURED"), e.measured_mass.v == null ? "weigh it → MEASURE_ME" : "");
  if (e.volume) row("Volume", num8(e.volume.v, "mm³", "CAD", "", 0));
  if (e.com) row("Centre of mass", num8(e.com.v.map(x => x.toFixed(1)).join(", "), "mm", "CALC", e.com.note));
  if (e.mat){
    for (const [k, lab] of [["yield_xy", "Yield XY"], ["z_factor", "Z factor"], ["E", "E"], ["tg", "Tg"], ["density", "Density"]]){
      const m = e.mat[k]; if (m) row(lab, num8(m.v, m.u, m.src, m.note || ""));
    }
    if (e.mat.yield_xy && e.mat.z_factor) row("Yield Z (layers)", num8(e.mat.yield_xy.v*e.mat.z_factor.v, "MPa", "CALC", "yield XY × z factor"));
  }
  if (e.print){
    const pc = el("div"); pc.appendChild(nameEl("h3", null, "Print panel · " + (ENG.printers && ENG.printers.ender3s1pro ? ENG.printers.ender3s1pro.name : "printer"))).style.marginTop = "12px";
    box.appendChild(pc);
    const nz = ENG.printers && ENG.printers.ender3s1pro && ENG.printers.ender3s1pro.nozzle;
    if (nz) row("Nozzle", num8(nz.v, "mm", nz.src, nz.note || ""));
    for (const [k, lab] of [["layer", "Layer"], ["walls", "Walls"], ["top_bottom", "Top / bottom"], ["infill", "Infill"]]){ const x = e.print[k]; if (x) row(lab, num8(x.v, x.u, x.src, "", k === "layer" ? 2 : 0)); }
    for (const [k, lab] of [["pattern", "Pattern"], ["supports", "Supports"], ["orientation", "Orientation"]]){ const x = e.print[k]; if (x){ const r = el("div", "v8row"); r.appendChild(nameEl("div", "lb", lab)); r.appendChild(nameEl("div", "vl", String(x.v))); if (x.why) r.appendChild(nameEl("div", "sub", x.why)); box.appendChild(r); } }
  }
  if (e.slicer){ row("Filament", num8(e.slicer.grams.v, "g", "SLICER", e.slicer.slicer)); row("Print time", num8(e.slicer.time_min.v, "min", "SLICER", e.slicer.slicer)); if (e.slicer.layers) row("Layers", num8(e.slicer.layers.v, "", "SLICER", "", 0)); }
  const fs = (ENG.fasteners || []).find(f => f.id === p.id);
  if (fs){ row("Torque", num8(fs.torque.v, fs.torque.u, fs.torque.src, fs.torque.note || ""), fs.torque.note);
           row("Thread engagement", num8(fs.engagement.v, "mm", fs.engagement.src, fs.engagement.note || ""));
           const r = el("div", "v8row"); r.appendChild(nameEl("div", "lb", "Goes in from")); r.appendChild(nameEl("div", "vl", fs.side)); box.appendChild(r); }
  const bt = el("div", "v8btns");
  const st = el("button", "btn", "⤓ STL"); st.dataset.nonum = "1"; st.addEventListener("click", () => downloadSTL(p));
  bt.appendChild(st);
  if (p.plate){ const mf = el("button", "btn pri", "Send to slicer · 3MF"); mf.dataset.nonum = "1"; mf.addEventListener("click", () => export3MF(p.plate.idx, mf)); bt.appendChild(mf); }
  box.appendChild(bt);
  shBody.appendChild(box);
})(renderInspector);

/* ===========================================================================
   R48 — PARTS TREE (Assembly › Part › Feature) with visibility toggles
   =========================================================================== */
function treeNode(){
  const ul = el("ul", "v8tr");
  const root = el("li"); const rr = el("div", "row");
  const re = el("button", "eye", "◉"); re.setAttribute("aria-label", "show all"); re.addEventListener("click", () => { hidden.clear(); draw(); syncUI(); paintTree(); });
  const rn = nameEl("button", null, (ENG && ENG.assembly.name) || META.title); rn.style.fontWeight = "700";
  rr.append(re, rn); root.appendChild(rr);
  const kids = el("ul", "v8tr kids");
  for (const p of parts.filter(q => q.kind !== "wire")){
    const li = el("li"); const row = el("div", "row" + (sel.has(p.id) ? " sel" : "")); row.dataset.part = p.id;
    const eye = el("button", "eye", "◉"); eye.setAttribute("aria-label", "toggle " + p.label); eye.setAttribute("aria-pressed", String(!hidden.has(p.id)));
    eye.addEventListener("click", () => { hidden.has(p.id) ? hidden.delete(p.id) : hidden.add(p.id); draw(); syncUI(); paintTree(); });
    const nm = nameEl("button"); const sw = el("span", "sw"); sw.style.background = p.color; nm.append(sw, document.createTextNode(p.label));
    nm.addEventListener("click", () => { pickPart(p, false); fitParts([p]); paintTree(); });
    row.append(eye, nm); li.appendChild(row);
    const feats = (ENG && ENG.fits || []).filter(f => f.part === p.id).map(f => ({lab: "◎ " + f.label, at: f.at}))
                  .concat(FAST.filter(f => f.part === p.id).map(f => ({lab: "⟳ " + f.spec + " · " + (f.side || ""), at: f.at})));
    if (feats.length){
      const fu = el("ul", "v8tr kids");
      for (const f of feats){ const fl = el("li"); const fr = el("div", "row"); fr.append(el("span"), nameEl("button", "feat", f.lab));
        fr.lastChild.addEventListener("click", () => flyTo(f.at, p)); fl.appendChild(fr); fu.appendChild(fl); }
      li.appendChild(fu);
    }
    kids.appendChild(li);
  }
  root.appendChild(kids); ul.appendChild(root);
  return ul;
}
let treeEl = null;
function paintTree(){
  if (treeEl && treeEl.classList.contains("open")){ treeEl.textContent = ""; treeEl.appendChild(treeNode()); }
  if (sheetOpen && sheetTab === "tree"){ shBody.textContent = ""; shBody.appendChild(treeNode()); }
}
function toggleTree(){
  if (matchMedia("(min-width:768px)").matches){
    if (!treeEl){ treeEl = el("aside"); treeEl.id = "v8tree"; treeEl.setAttribute("aria-label", "Parts tree"); $("stage").appendChild(treeEl); }
    const on = !treeEl.classList.contains("open");
    treeEl.classList.toggle("open", on); document.documentElement.classList.toggle("v8tree-open", on);
    $("bTree") && $("bTree").setAttribute("aria-pressed", String(on));
    paintTree(); setTimeout(() => { vcSize(); draw(); }, 240);
  } else {
    if (sheetOpen && sheetTab === "tree"){ closeSheet(); return; }
    openSheet("tree"); shTitle.textContent = "Parts tree"; paintTree();
  }
}
$("bTree") && $("bTree").addEventListener("click", toggleTree);
pickPart = (orig => function(p, additive){ const r = orig(p, additive); if (treeEl && treeEl.classList.contains("open")) paintTree(); return r; })(pickPart);

/* ===========================================================================
   R51 — BOM: what you already own reads OWNED $0 for unit #1
   =========================================================================== */
showBom = (orig => function(){
  orig();
  for (const c of shBody.querySelectorAll(".stc.have")) c.textContent = "OWNED $0";
  const rows = bomRows(), own = rows.filter(r => bomStatus(r) === "have"), buy = rows.filter(r => bomStatus(r) === "buy");
  const prn = rows.filter(r => bomStatus(r) === "print" && r.cost && r.cost.each != null).reduce((a, r) => a + r.cost.each*r.qty, 0);
  const n = el("div", "v8warn soft"); n.id = "v8owned"; n.style.borderColor = "var(--line)";
  n.appendChild(nameEl("b", null, "$"));
  const t = el("div"); t.appendChild(nameEl("span", null, "Unit #1 out of pocket: "));
  t.appendChild(num8(prn + buy.reduce((a, r) => a + (r.cost && r.cost.each || 0)*r.qty, 0), CUR, "CALC", "filament + anything not on the shelf", 2));
  t.appendChild(nameEl("span", null, " · " + own.length + " lines OWNED $0 (bulk rows still priced)"));
  n.appendChild(t);
  shBody.prepend(n);
})(showBom);

/* ===========================================================================
   R49 — SHARE VIEW + the hash: phase, camera, explode, section, load, toggles
   =========================================================================== */
V8.camInHash = false;
/* bare-token hash: a published artifact passes only [A-Za-z0-9._~-] through, so no "=" or "&":
   #v8~test~kg0.75~lev22.5~ex0.000~sec1_0.4000_0~st6~xr~wf~tol0~m2.8_2.61_3.0_2.8~cam-0.86_0.4_173.5_0_0_0_o~pservo */
const N8 = (v, d) => (+v).toFixed(d).replace(/^-0(\.0+)?$/, "0$1");
function v8Hash(withCam){
  const o = ["v8", V8.phase, "ex" + N8(explode, 3)];
  if (sectOn) o.push("sec" + [sectAxis, N8(sectT, 4), sectFlip ? 1 : 0].join("_"));
  if (V8.phase === "test") o.push("kg" + N8(V8.kg, 2), "lev" + N8(V8.lever, 1));
  if (V8.phase === "secure" && stepMode) o.push("st" + step);
  if (V8.phase === "fit" && !V8.tol) o.push("tol0");
  if (V8.xray) o.push("xr");
  if (V8.wire) o.push("wf");
  const ms = Object.entries(V8.measured).filter(([k]) => !isNaN(+k));
  if (ms.length) o.push("m" + ms.map(([k, v]) => k + "_" + v).join("_"));
  if (withCam) o.push("cam" + [cam.yaw, cam.pitch, cam.dist, PAN[0], PAN[1], PAN[2]].map(v => N8(v, 3)).join("_") + (V7.ortho ? "_o" : ""));
  if (sel.size === 1 && /^[A-Za-z0-9._-]+$/.test([...sel][0])) o.push("p" + [...sel][0]);
  return "#" + o.join("~");
}
function parseV8(h){
  const f = h.split("~"); if (f[0] !== "v8" || !f[1]) return null;
  const o = {phase: f[1]};
  for (const x of f.slice(2)){
    let m;
    if ((m = /^ex(-?[\d.]+)$/.exec(x))) o.ex = m[1];
    else if ((m = /^sec([0-2])_([\d.]+)_([01])$/.exec(x))) o.sec = [m[1], m[2], m[3]].join(",");
    else if ((m = /^kg([\d.]+)$/.exec(x))) o.kg = m[1];
    else if ((m = /^lev([\d.]+)$/.exec(x))) o.lev = m[1];
    else if ((m = /^st(\d+)$/.exec(x))) o.st = m[1];
    else if (x === "tol0") o.tol = "0";
    else if (x === "xr") o.xr = "1";
    else if (x === "wf") o.wf = "1";
    else if ((m = /^m([\d._]+)$/.exec(x))){ const a = m[1].split("_"); const kv = []; for (let i = 0; i + 1 < a.length; i += 2) kv.push(a[i] + ":" + a[i+1]); o.m = kv.join(";"); }
    else if ((m = /^cam(.+)$/.exec(x))){ const a = m[1].split("_"); o.cam = a.slice(0, 6).join(",") + (a[6] === "o" ? ",o" : ""); }
    else if ((m = /^p(.+)$/.exec(x))) o.part = m[1];
  }
  return o;
}
readHash = (orig => function(){
  const h = location.hash.replace(/^#/, "");
  if (/^v8~/.test(h)) return parseV8(h);
  return orig();
})(readHash);
hashNow = (orig => function(){
  if (!V8.phase) return orig();
  return v8Hash(V8.camInHash || V7.camLink);
})(hashNow);
function applyV8(o){
  const ok = setPhase(o.phase, {restore: true});
  if (!ok) return false;
  if (o.m) for (const kv of o.m.split(";")){ const [k, v] = kv.split(":"); if (k && v != null && !isNaN(+v)){ V8.measured[+k] = +v;
    for (const f of (ENG.fits || [])) if (Math.abs(f.cad.v - +k) < 1e-6) V8.measured[f.id] = +v; } }
  if (o.kg != null && isFinite(+o.kg)) V8.kg = Math.max(MD ? MD.kg.min : 0, Math.min(MD ? MD.kg.max : 5, +o.kg));
  if (o.lev != null && isFinite(+o.lev)) V8.lever = Math.max(MD ? MD.lever.min : 0, Math.min(MD ? MD.lever.max : 50, +o.lev));
  V8.xray = o.xr === "1"; V8.wire = o.wf === "1";
  if (o.phase === "fit") V8.tol = o.tol !== "0";
  const land = () => {
    if (V8.phase !== o.phase) return;                       /* the user moved on before the restore landed */
    if (o.ex != null && isFinite(+o.ex)){ explode = Math.max(0, Math.min(50/EXK, +o.ex)); $("ex").value = Math.round(Math.min(1, explode)*100); $("exv").textContent = Math.round(explode*100) + "%"; V8.spacing = Math.round(explode*EXK); }
    if (o.sec){ const [a, t, f] = o.sec.split(",").map(Number); if (!sectOn) $("bSect").click(); sectAxis = Math.min(2, Math.max(0, a|0)); sectT = Math.max(0, Math.min(1, isFinite(t) ? t : 1)); sectFlip = !!f; $("sec").value = Math.round(sectT*1000); syncSect(); }
    if (o.st && stepMode){ stopPlay(); gotoStep(+o.st); }
    if (o.part){ const p = byId.get(o.part); if (p){ sel.clear(); sel.add(p.id); syncUI(); } }
    if (o.phase === "test") syncLoad();
    if (o.phase === "fit") renderFit();
    if (o.phase === "test" && motionMode){ V8.inPhase = true; try { showMotion(); } finally { V8.inPhase = false; } }
    syncToggles(); draw(); writeHash();
  };
  setTimeout(land, V7RM() ? 0 : 460);
  return true;
}
applyHash = (orig => function(o){
  if (o && o.phase && ENG){
    const did = applyV8(o);
    if (did && o.cam) setTimeout(() => applyCam(o.cam), V7RM() ? 0 : 520);
    return did;
  }
  return orig(o);
})(applyHash);
function shareView(btn){
  const h = V8.phase ? v8Hash(true) : (V7.camLink = true, (() => { try { return hashNow(); } finally { V7.camLink = false; } })());
  copyText(location.href.split("#")[0] + h, btn || $("bShare"), "Link copied — opens this exact view");
  return h;
}
$("bShare") && $("bShare").addEventListener("click", () => shareView($("bShare")));

/* ===========================================================================
   R54 — view history: a fresh Reset is a stop of its own (v7.4 recorded the pre-reset view only)
   =========================================================================== */
$("bReset").addEventListener("click", () => {
  if (V8.calOn) setCal(false);
  setTimeout(() => { if (!interacting) vhRecord(); }, V7RM() ? 0 : 520);
});

/* ===========================================================================
   R55 — build-step fly-ins draw at interaction resolution (no edge pass, tuned DPR) and land on
   one crisp full-resolution frame. v7.x drew every animated frame as a "still" frame: 100–350 ms
   per frame on SwiftShader with the servo mount, so a 1 s step finished in 4 frames.
   =========================================================================== */
tickStep = (orig => function(){
  const run = SA && !SA.paused && SA.u < 1;
  if (run){
    /* the animation clock advances at most 50 ms per frame: a slow GPU shows every stage of the
       fly-in (a little slower) instead of jumping to the end in three frames */
    const now = performance.now();
    if (SA.v8last != null){ const dt = now - SA.v8last; if (dt > 50) SA.t0 += dt - 50; }
    SA.v8last = now;
    beginInteract();
  }
  orig();
  if (!SA || SA.paused || SA.u >= 1) endInteract();
})(tickStep);
saResume = (orig => function(){ if (SA) SA.v8last = null; return orig(); })(saResume);   /* a pause is not a slow frame */

/* ===========================================================================
   R57 — the interaction-resolution ladder gets a 0.75× rung, and a run of frames far over budget
   (median > 50 ms) drops two rungs at once. Dragging on a slow phone goes soft for a moment and
   lands crisp on release (the still frame is always full resolution). v7.x: one rung per 0.5 s,
   floor 1× — a 2.5 s orbit on a slow device spent most of its time at a resolution it couldn't hold.
   =========================================================================== */
if (RUNGS.indexOf(0.75) < 0) RUNGS.push(0.75);
frameTick = (orig => function(){
  const before = DPR_INT;
  orig();
  if (DPR_INT !== before && fTimes.length >= 12){
    const last = fTimes.slice(-12).slice().sort((a, b) => a - b), i = RUNGS.indexOf(DPR_INT);
    if (last[6] > 50 && DPR_INT < before && i >= 0 && i < RUNGS.length - 1) DPR_INT = RUNGS[i + 1];
  }
})(frameTick);

/* keys: C caliper, X x-ray, W wireframe, T tree (desktop) */
addEventListener("keydown", e => {
  if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA" || e.target.tagName === "SELECT" || e.ctrlKey || e.metaKey) return;
  if (e.key === "c") setCal(!V8.calOn);
  else if (e.key === "x") setXray(!V8.xray);
  else if (e.key === "w") setWire(!V8.wire);
  else if (e.key === "t") toggleTree();
});
$("bTheme").addEventListener("click", () => { heatCols = null; setTimeout(draw, 0); });

/* loader brand line + footer + the first phase */
(function brand8(){
  const f = $("v8foot"); if (f) f.textContent = BRAND.footer;
  document.title = document.title || META.title;
  if (ENG){ addEventListener("load", () => {}); }
})();

/* ---------- verifier hooks (verify_av_v9.py) ---------- */
window.__avV8 = {
  ver: () => "8.0", eng: () => !!ENG, phase: () => V8.phase, setPhase: (p, o) => setPhase(p, o),
  calc: (kg, lever) => { const R = calc8(kg, lever); return {...R, arm: {...R.arm}, wall: {...R.wall}}; },
  setLoad: (kg, lever) => { if (kg != null) V8.kg = kg; if (lever != null) V8.lever = lever; syncLoad(); if (V8.phase === "test" && motionMode) showMotion(); return calc8(); },
  checks: () => liveChecks(V8.R || calc8()), fits: () => fits8().map(f => ({id: f.id, clr: f.clr, printed: f.printedJS, psrc: f.psrc, band: f.band})),
  rings: () => [...leads.querySelectorAll("path.v8tol")].filter(e => e.style.display !== "none").map(e => ({fit: e.dataset.fit, cls: e.dataset.cls, stroke: e.getAttribute("stroke")})),
  setCal, caliper: () => V8.cal ? {d: V8.cal.d, pts: V8.calPts.length} : null,
  perf: () => ({fps: fps8(), scene: V8.last.scene, drawn: V8.last.tris, calls: V8.last.calls, lod: V8.lodNow}), setPerf,
  hash: withCam => V8.phase ? v8Hash(!!withCam) : hashNow(), share: () => shareView(null),
  heat: () => [...HEAT].map(([k, h]) => ({id: k, s0: h.s0, s1: h.s1})), ranking: () => ranking8(V8.R || calc8()).map(r => ({id: r.id, sf: r.sf})),
  motionTau: q => { const st = poseFromQ({...homeQ(), shaft: q || 0}); const L = loads(st).find(l => l.id === "shaft"); return L ? L.kgcm : null; },
  setXray, setWire, state: () => ({xray: V8.xray, wire: V8.wire, tol: V8.tol, heat: V8.heat, kg: V8.kg, lever: V8.lever, explode, sectOn, sectAxis, sectT, step, stepMode, motionMode, sel: [...sel], pan: PAN.slice(), ortho: !!V7.ortho}),
  toggleTree, tree: () => ({drawer: !!(treeEl && treeEl.classList.contains("open")), sheet: sheetOpen && sheetTab === "tree"}),
  numScan: () => {
    const bad = [];
    for (const root of document.querySelectorAll("[data-eng]")){
      if (root.closest("[hidden]") || root.offsetParent === null && getComputedStyle(root).position !== "fixed") continue;
      const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
      let n; while ((n = w.nextNode())){
        if (!/\d/.test(n.nodeValue)) continue;
        const pe = n.parentElement;
        if (pe.closest(".num[data-src],[data-nonum],.src")) continue;
        bad.push((typeof pe.className === 'string' ? pe.className : pe.tagName) + ": " + n.nodeValue.trim().slice(0, 40));
      }
    }
    return bad;
  },
  nums: () => [...document.querySelectorAll("[data-eng] .num[data-src]")].filter(e => !e.closest("[hidden]") && (e.offsetParent !== null || getComputedStyle(e).position === "fixed")).length,
  capProbe: (pt) => {
    draw();
    const r = cv.getBoundingClientRect(), W = cv.width, H = cv.height, V = M.look(eye(), target(), [0, 0, 1]), P = M.persp(FOV, W/H, 1, 2000); skewY(P);
    const s = project(M.mul(P, V), pt, W, H); if (!s) return null;
    const px = new Uint8Array(4); gl.readPixels(Math.round(s[0]), Math.round(H - s[1]), 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px);
    const cut = hex(cssVar("--cut") || "#c98b4b").map(x => Math.round(x*255)), bg = stageBG().map(x => Math.round(x*255));
    const near = (a, k) => Math.abs(px[0] - a[0]*k) < 14 && Math.abs(px[1] - a[1]*k) < 14 && Math.abs(px[2] - a[2]*k) < 14;
    return {px: [px[0], px[1], px[2]], cut, bg, cap: near(cut, 1) || near(cut, 0.78), isBg: near(bg, 1), at: [s[0]/curDpr, s[1]/curDpr]};
  },
  measured: () => ({...V8.measured}),
  formulas: (name, args) => F8[name](...args),
  meta: k => k ? META[k] : META,
  view: o => { o = o || {}; animGen++; if (o.yaw != null) cam.yaw = o.yaw; if (o.pitch != null) cam.pitch = o.pitch; if (o.dist != null) cam.dist = o.dist;
               if (o.zoom != null) cam.dist = HOME.dist*o.zoom; if (o.pan) for (let i = 0; i < 3; i++) PAN[i] = o.pan[i];
               if (o.explode != null){ explode = o.explode; } draw(); return {yaw: cam.yaw, pitch: cam.pitch, dist: cam.dist, home: HOME.dist, explode}; },
  section: o => { if (!o){ if (sectOn) $("bSect").click(); return {on: sectOn}; }
                  if (!sectOn) $("bSect").click(); sectAxis = o.axis|0; sectFlip = !!o.flip;
                  if (o.at != null){ const [a, b] = sectRange(); sectT = (o.at - a)/(b - a); } else if (o.t != null) sectT = o.t;
                  $("sec").value = Math.round(sectT*1000); syncSect(); return {on: sectOn, axis: sectAxis, t: sectT, v: sectValue()}; },
  stepTo: n => { stopPlay(); gotoStep(n); return step; },
  screwFly: () => {                     /* where does each screw START its SECURE fly-in, relative to its seat? */
    const out = [];
    for (const f of FAST){
      const pp = byId.get(f.screw); if (!pp) continue;
      stopPlay(); gotoStep(f.step); if (!SA) continue;
      /* track the screw's own seat point (on its axis), not the mesh origin — the fly-in also spins the
         screw about that axis, which swings the origin sideways */
      const a = (pp.screw && pp.screw.at) || [0, 0, 0];
      const tp = m => [0, 1, 2].map(i => m[i]*a[0] + m[4 + i]*a[1] + m[8 + i]*a[2] + m[12 + i]);
      SA.paused = true; SA.u = 0.15; const q0 = tp(modelOf(pp)); SA.u = 1; const q1 = tp(modelOf(pp));
      const d = [q0[0] - q1[0], q0[1] - q1[1], q0[2] - q1[2]];
      out.push({id: f.id, side: f.side, dot: d[0]*f.axis[0] + d[1]*f.axis[1] + d[2]*f.axis[2], off: d});
    }
    draw(); return out;
  },
  recolour: (tone, col) => { ENG.tolerance.colors[tone] = col; draw(); return fits8().filter(f => f.band.tone === tone).map(f => f.id); },
  fasteners: () => FAST.map(f => ({id: f.id, side: f.side, axis: f.axis, step: f.step, screw: f.screw})),
};
