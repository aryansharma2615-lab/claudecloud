/* ===========================================================================
   SP AV ENGINE v7.4 — module (inlined by patch_engine_v7_4.py, before BOOT,
   after v7 … v7.3)
   R33 ∠ angle tool: three snapped taps -> the angle at the middle one
   R34 view history: ◀ / ▶ step back and forward through where you looked
   R35 swipe the Build step card left / right to change step
   R36 wire to buy: metres per gauge on the Wiring tab (cut lengths, rounded up)
   R37 "?" key map overlay (desktop discoverability; Esc closes)
   =========================================================================== */
V7.ver = "7.4";

/* ===========================================================================
   R33 — ANGLE: three taps A, B, C -> angle ABC (snapped to mesh corners)
   =========================================================================== */
let angOn = false; const angPts = [];
function angleAt(a, b, c){
  const u = sub(a, b), v = sub(c, b), L = Math.hypot(...u)*Math.hypot(...v);
  return L < 1e-12 ? null : Math.acos(Math.max(-1, Math.min(1, dot(u, v)/L)))*180/Math.PI;
}
function setAng(on){
  angOn = !!on; angPts.length = 0;
  const b = $("bAng"); if (b) b.setAttribute("aria-pressed", String(angOn));
  if (angOn){ if (diaOn) setDia(false); if (gapOn) setGap(false); if (measOn) $("bMeas").click();
              flash2("∠ · tap 3 points", "the angle is read at the middle one"); }
  cv.style.cursor = angOn ? "crosshair" : "";
  draw();
}
$("bAng") && $("bAng").addEventListener("click", () => setAng(!angOn));
setDia = (orig => function(on){ if (on && angOn) setAng(false); return orig(on); })(setDia);
setGap = (orig => function(on){ if (on && angOn) setAng(false); return orig(on); })(setGap);
navTap = (orig => function(cx, cy, hp){
  if (!angOn || V7.lpFired) return orig(cx, cy, hp);
  const h = raycast(cx, cy);
  if (!h){ flash("No part under that tap"); return true; }
  if (angPts.length >= 3) angPts.length = 0;
  angPts.push({part: h.part.id, local: h.local});
  if (angPts.length < 3) flash2("∠ · " + angPts.length + " / 3", angPts.length === 1 ? "now the corner (vertex)" : "now the third point");
  else {
    const w = angPts.map(q => M.xform(modelOf(byId.get(q.part)), q.local));
    const a = angleAt(w[0], w[1], w[2]);
    V7.angle = a;
    if (a == null) flash("Two of those points are the same — tap again");
    else flash2("∠ " + a.toFixed(1) + "°", "at the middle point · supplement " + (180 - a).toFixed(1) + "°");
  }
  buzz(); draw(); return true;
})(navTap);
const angEls = [];
let angPath = null;
function drawAng(MVP, W, H){
  while (angEls.length < 3){ const d = document.createElement("div"); d.className = "dot ang"; marks.appendChild(d); angEls.push(d); }
  if (!angPath){ angPath = document.createElementNS("http://www.w3.org/2000/svg", "polyline"); angPath.setAttribute("class", "angln"); leads.appendChild(angPath); }
  const pts = [];
  angEls.forEach((d, i) => {
    const q = angOn && angPts[i];
    const s = q && project(MVP, M.xform(modelOf(byId.get(q.part)), q.local), W, H);
    showEl(d, !!s);
    if (s){ d.style.transform = `translate(${s[0]}px,${s[1]}px)`; pts.push(s); }
  });
  showEl(angPath, pts.length >= 2);
  if (pts.length >= 2) angPath.setAttribute("points", pts.map(s => s[0].toFixed(1) + "," + s[1].toFixed(1)).join(" "));
}

/* ===========================================================================
   R34 — VIEW HISTORY: every settled camera move is a stop you can go back to
   =========================================================================== */
const VH = [], VHmax = 30; let vhI = -1, vhLock = false, vhT = null;
const camNow = () => ({yaw: cam.yaw, pitch: cam.pitch, dist: cam.dist, pan: PAN.slice(), ortho: V7.ortho});
const camSame = (a, b) => a && b && Math.abs(a.yaw - b.yaw) < 1e-3 && Math.abs(a.pitch - b.pitch) < 1e-3 &&
  Math.abs(a.dist - b.dist) < 1e-2 && a.pan.every((v, i) => Math.abs(v - b.pan[i]) < 1e-2) && a.ortho === b.ortho;
function vhRecord(){
  if (vhLock) return;
  const c = camNow();
  if (camSame(c, VH[vhI])) return;
  VH.splice(vhI + 1); VH.push(c); if (VH.length > VHmax) VH.shift();
  vhI = VH.length - 1; vhSync();
}
function vhGo(d){
  const j = vhI + d; if (j < 0 || j >= VH.length) return;
  vhI = j; vhLock = true;
  const c = VH[j];
  if (c.ortho !== V7.ortho) setOrtho(c.ortho);
  clearPreset();
  animate({yaw: c.yaw, pitch: c.pitch, dist: c.dist, pan: c.pan}, V7RM() ? 0 : 320);
  setTimeout(() => { vhLock = false; }, V7RM() ? 0 : 360);
  vhSync(); buzz(6);
}
function vhSync(){
  const b = $("bBack"), f = $("bFwd");
  if (b) b.disabled = vhI <= 0;
  if (f) f.disabled = vhI >= VH.length - 1;
}
/* a view "settles" 450 ms after the last frame that moved the camera */
draw = (orig => function(){
  orig();
  clearTimeout(vhT);
  vhT = setTimeout(() => { if (!interacting) vhRecord(); }, 450);
})(draw);
$("bBack") && $("bBack").addEventListener("click", () => vhGo(-1));
$("bFwd") && $("bFwd").addEventListener("click", () => vhGo(1));
addEventListener("keydown", e => {
  if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
  if (e.key === "[" ){ e.preventDefault(); vhGo(-1); }
  else if (e.key === "]"){ e.preventDefault(); vhGo(1); }
  else if (e.key === "a" && !e.ctrlKey && !e.metaKey){ setAng(!angOn); }
  else if (e.key === "?" ){ e.preventDefault(); toggleKeys(); }
  else if (e.key === "Escape" && keysEl && !keysEl.hidden){ toggleKeys(false); }
});

/* ===========================================================================
   R35 — SWIPE BETWEEN STEPS on the step card (a thumb, not a target)
   =========================================================================== */
showBuild = (orig => function(){
  orig();
  const w = $("tl"); if (!w) return;
  let sx = null, sy = null;
  w.addEventListener("pointerdown", e => {
    if (e.target.closest("button,input,.tick,.tag")) return;
    sx = e.clientX; sy = e.clientY;
  });
  w.addEventListener("pointerup", e => {
    if (sx == null) return;
    const dx = e.clientX - sx, dy = e.clientY - sy; sx = null;
    if (Math.abs(dx) > 60 && Math.abs(dx) > 2*Math.abs(dy)){ stopPlay(); gotoStep(step + (dx < 0 ? 1 : -1)); buzz(6); }
  });
  w.addEventListener("pointercancel", () => { sx = null; });
  w.style.touchAction = "pan-y";
})(showBuild);

/* ===========================================================================
   R36 — WIRE TO BUY: cut lengths summed per gauge and kind, rounded up
   =========================================================================== */
function wireToBuy(){
  const m = new Map();
  for (const r of RUNS){
    const g = r.gauge || (r.awg + " AWG");
    const cut = ((+r.length_mm || 0) + 40) * (r.conductors || 1);
    m.set(g, (m.get(g) || 0) + cut);
  }
  return [...m].map(([g, mm]) => ({gauge: g, mm: Math.round(mm), m: Math.ceil(mm/100)/10})).sort((a, b) => b.mm - a.mm);
}
showWire = (orig => function(){
  orig();
  if (!RUNS.length) return;
  const card = el("div", "ckcard wbuy"); card.id = "wireBuy";
  card.appendChild(el("div", "lph", "Wire to buy · cut lengths, every conductor"));
  const k = el("div", "kpis");
  for (const w of wireToBuy()){
    const d = el("div", "kpi"); d.appendChild(el("div", "k", w.gauge));
    const v = el("div", "v", w.m.toFixed(1)); const sm = document.createElement("small"); sm.textContent = " m"; v.appendChild(sm);
    d.appendChild(v); k.appendChild(d);
  }
  card.appendChild(k);
  const pb = $("pBudget"); if (pb) pb.after(card); else shBody.prepend(card);
})(showWire);

/* ===========================================================================
   R37 — "?" KEY MAP
   =========================================================================== */
let keysEl = null;
function toggleKeys(force){
  if (!keysEl){
    keysEl = el("div", "keymap"); keysEl.id = "keymap"; keysEl.hidden = true;
    keysEl.setAttribute("role", "dialog"); keysEl.setAttribute("aria-label", "Keyboard shortcuts");
    const rows = [["drag", "orbit about the point under the cursor"], ["right / middle / shift drag", "pan"],
      ["wheel", "zoom to the cursor"], ["double-click", "fit that part"], ["F", "fit all (or the selection)"],
      ["1 · 3 · 7", "front · right · top  (Ctrl = opposite)"], ["0", "iso"], ["5", "perspective / ortho"], ["9", "flip to the other side"],
      ["[  ]", "previous / next view"], ["← →", "build step"], ["M", "measure"], ["A", "angle"], ["S", "section"],
      ["B", "bolts"], ["H · I", "hide · isolate the selection"], ["Esc", "clear"], ["` or P", "fps"], ["?", "this map"]];
    const t = document.createElement("table");
    for (const [k, v] of rows){ const tr = document.createElement("tr");
      const a = document.createElement("th"); a.textContent = k; const b = document.createElement("td"); b.textContent = v;
      tr.append(a, b); t.appendChild(tr); }
    const x = el("button", "btn", "✕"); x.setAttribute("aria-label", "Close"); x.addEventListener("click", () => toggleKeys(false));
    keysEl.append(x, t);
    $("stage").appendChild(keysEl);
  }
  keysEl.hidden = force === undefined ? !keysEl.hidden : !force;
}
$("bKeys") && $("bKeys").addEventListener("click", () => toggleKeys());

drawMotionOverlays = (orig => function(MVP, W, H){ orig(MVP, W, H); drawAng(MVP, W, H); })(drawMotionOverlays);
$("bReset").addEventListener("click", () => { if (angOn) setAng(false); });

/* ---------- verifier hooks ---------- */
Object.assign(window.__avV7, {
  angleAt: (a, b, c) => angleAt(a, b, c), angle: () => V7.angle == null ? null : V7.angle, setAng,
  history: () => ({n: VH.length, i: vhI, now: camNow()}), back: () => vhGo(-1), fwd: () => vhGo(1),
  wireToBuy: () => wireToBuy(), keys: () => !!(keysEl && !keysEl.hidden),
});
