/* ===========================================================================
   SP AV ENGINE v7.1 — module (inlined by patch_engine_v7_1.py, before BOOT,
   after the v7 module). Same mechanism as v7: wrap declarations by name.
   R16 wires: any-colour leads, colours carried along a run, pin ranges
   R17 explode trace lines · R18 part search · R19 bench checklist
   R20 snapshot PNG + wire cut-list CSV · R21 long-press peek
   R22 scale bar · R23 camera in the copied link · R24 focus mode · haptics
   =========================================================================== */
V7.ver = "7.1";
const buzz = ms => { try { if (navigator.vibrate) navigator.vibrate(ms || 8); } catch(e){} };
const lsGet = k => { try { return localStorage.getItem(k); } catch(e){ return null; } };
const lsSet = (k, v) => { try { localStorage.setItem(k, v); } catch(e){} };
const SLUG = META.slug || "av";

/* ===========================================================================
   R16 — WIRE COLOURS THAT MATCH HOW SP ACTUALLY WIRES
   SP jumpers are whatever colour is in the kit. So a conductor's colour is,
   in order: config → factory lead (label / part library) → carried along its
   run from a factory lead at the other end (the servo's orange SIG lead is
   what reaches UNO D5) → red / black convention for power and ground →
   "any colour — tag it". Unset is no longer a state a real build ends in.
   Ranges ("D8–11", "IN1–4") and "5-pin" plugs expand to one row per wire.
   =========================================================================== */
const FULLC = {brn:"brown", blk:"black", wht:"white", grn:"green", yel:"yellow", org:"orange", blu:"blue", gray:"grey"};
const fullName = c => c ? (FULLC[String(c).toLowerCase()] || String(c).toLowerCase()) : c;
CONN.unshift([/button|door|limit switch|microswitch/i, "Dupont / solder tab"]);   // before the generic "switch" → screw terminal
/* one pin → N conductors, before any colour is decided */
function expandPin(n, pn){
  const lab = String(pn.label || pn.id);
  const lib = libOf(n);
  const rg = lab.match(/^([A-Za-z]+)\s*(\d+)\s*[–-]\s*(\d+)$/);       // D8–11, IN1–4
  if (rg){
    const a = +rg[2], b = +rg[3], out = [];
    if (b > a && b - a < 16) for (let i = a; i <= b; i++) out.push({label: rg[1] + i, color: null, colName: null, src: "unset"});
    if (out.length) return out;
  }
  const mN = lab.match(/[×x]\s*(\d+)|(\d+)\s*[- ]?pins?\b/i);
  const k = mN ? +(mN[1] || mN[2]) : 0;
  if (k > 1 && k <= 16 && !Array.isArray(pn.wires) && !pn.color){
    const potLib = /pot/i.test(lab + " " + n.label) ? LIB.find(([re]) => re.test("pot")) : lib;
    const out = [];
    for (let i = 0; i < k; i++){
      const r = potLib && potLib[2][i];
      const c = r && r[2];
      out.push({label: r ? r[1] : "#" + (i+1), colName: c || null, color: c ? colourOf(c) : null, src: c ? "library" : "unset"});
    }
    return out;
  }
  return null;
}
let inheriting = false;
conductors = (orig => function(n, pn){
  let cds = expandPin(n, pn) || orig(n, pn);
  cds = cds.map(c => ({...c, colName: fullName(c.colName)}));
  for (const c of cds) if (c.colName === "any"){ c.color = null; c.src = "any"; }
  if (inheriting) return cds;
  // carry a factory colour along the run from the far end
  const runs = RUNS.filter(r => r.from === n.id + "." + pn.id || r.to === n.id + "." + pn.id);
  for (const r of runs){
    const other = r.from === n.id + "." + pn.id ? endRef(r.to) : endRef(r.from);
    const on = nodeById.get(other[0]); const op = on && (on.pins || []).find(x => x.id === other[1]);
    if (!op) continue;
    inheriting = true; let far; try { far = conductors(on, op); } finally { inheriting = false; }
    const factory = far.filter(f => f.color && (f.src === "config" || f.src === "label" || f.src === "library"));
    if (!factory.length) continue;
    // a single generic pin ("MOTOR") mating a factory plug ("5-pin JST") IS that plug's socket
    if (cds.length === 1 && cds[0].src === "unset" && far.length > 1 && factory.length === far.length){
      cds = far.map(f => ({label: f.label, color: f.color, colName: f.colName, src: "run"}));
      continue;
    }
    cds.forEach((c, i) => {
      if (!(c.src === "unset" || c.src === "convention")) return;
      const role = /gnd|ground/i.test(c.label) ? "g" : /^\+|v\b|vcc|vin|5 ?v|com/i.test(c.label) ? "v" : null;
      let m = null;
      if (role) m = factory.find(f => (role === "g") === /gnd|ground|brown|black/i.test(f.label + " " + f.colName));
      if (!m && far.length === cds.length) m = far[i].color ? far[i] : null;
      if (!m && cds.length === 1 && factory.length === 1 && far.length === 1) m = factory[0];
      if (m){ c.color = m.color; c.colName = m.colName; c.src = "run"; }
    });
  }
  for (const c of cds) if (c.src === "unset"){ c.src = "any"; c.colName = "any"; }
  return cds;
})(conductors);
showWire = (orig => function(){
  orig();
  if (!RUNS.length) return;
  for (const x of shBody.querySelectorAll('.pcr[data-src="any"] .pcx')) x.textContent = "any colour · tag it";
  for (const x of shBody.querySelectorAll('.pcr[data-src="run"] .pcx')) x.textContent += " · via lead";
  /* R20: the cut list a person takes to the bench */
  const acts = el("div", "acts");
  const b = el("button", "btn", "⤓ Wire cut list (CSV)"); b.id = "bCutList";
  b.addEventListener("click", () => saveDirect(new Blob([cutListCSV()], {type: "text/csv"}), SLUG + "_wire_cut_list.csv", b));
  acts.appendChild(b);
  const sec = shBody.querySelector("#pinouts");
  (sec ? sec : shBody.lastChild).after(acts);
})(showWire);
function cutListCSV(){
  const q = v => { const s = String(v == null ? "" : v); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
  const rows = [["run","label","from","to","net","kind","gauge","routed_mm","cut_mm","conductors","colours_from_end","connector_from","connector_to","amps","drop_v"]];
  for (const r of RUNS){
    const a = runEnd(r, "from"), bb = runEnd(r, "to");
    const ap = (a.n.pins || []).find(x => x.id === a.pid);
    const cols = ap ? conductors(a.n, ap).map(c => c.colName || "any").join("/") : "";
    // +20 mm at each end: the strip length, a crimp or a solder joint, and a little service loop
    rows.push([r.id, r.label, r.from, r.to, r.net || "", r.kind, r.gauge || (r.awg + " AWG"), r.length_mm,
               Math.ceil((+r.length_mm || 0) + 40), r.conductors || 1, cols, a.connector || "", bb.connector || "", r.amps, r.drop_v]);
  }
  return rows.map(r => r.map(q).join(",")).join("\n") + "\n";
}

/* ===========================================================================
   R20 — FILES THE PLATFORM ALLOWS AS-IS (png, csv) go straight out: no zip
   =========================================================================== */
async function saveDirect(blob, name, btn){
  if (inArtifact()){
    let dl = null;
    try { dl = await window.claude.use("downloads"); } catch(e){ dl = null; }
    if (dl && dl.save){
      try { await dl.save({filename: name, data: blob}); }
      catch(err){ if (!(err && err.code === "declined")) console.error("save failed", err); }
      return;
    }
    if (btn){ btn.disabled = true; btn.textContent = "Download not available here"; }
    return;
  }
  const u = URL.createObjectURL(blob);
  const a = document.createElement("a"); a.href = u; a.download = name;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(u), 4000);
}
function snapPNG(){
  draw();                                       // same task as the read: no preserveDrawingBuffer needed
  cv.toBlob(b => { if (b) saveDirect(b, SLUG + "_view.png", $("bSnap")); }, "image/png");
  buzz(10);
}
$("bSnap") && $("bSnap").addEventListener("click", snapPNG);

/* ===========================================================================
   R17 — EXPLODE TRACE LINES: where every part came from
   =========================================================================== */
const traceEls = new Map();
function drawTraces(MVP, W, H){
  const on = explode > 0.04 && !stepMode && !plateMode && !wireMode && !motionMode && V7.traces !== false;
  if (!on && !V7.traceCount) return;                 // nothing drawn, nothing to hide: free while assembled
  let n = 0;
  if (on) for (const p of parts){
    if (p.kind === "wire" || state(p) === "off") continue;
    const e = explodeVec(p);
    if (Math.hypot(e[0], e[1], e[2]) < 1) continue;
    const c = [p.lo[0]+p.span[0]/2, p.lo[1]+p.span[1]/2, p.lo[2]+p.span[2]/2];
    const s0 = project(MVP, c, W, H), s1 = project(MVP, add(c, e), W, H);
    if (!s0 || !s1) continue;
    let ln = traceEls.get(p.id);
    if (!ln){ ln = document.createElementNS("http://www.w3.org/2000/svg", "line"); ln.setAttribute("class", "trace");
              leads.insertBefore(ln, leads.firstChild.nextSibling); traceEls.set(p.id, ln); }
    ln.setAttribute("x1", s0[0].toFixed(1)); ln.setAttribute("y1", s0[1].toFixed(1));
    ln.setAttribute("x2", s1[0].toFixed(1)); ln.setAttribute("y2", s1[1].toFixed(1));
    ln.style.display = ""; ln._on = true; n++;
  }
  for (const [id, ln] of traceEls) if (!on || !ln._on) ln.style.display = "none"; else ln._on = false;
  V7.traceCount = n;
}

/* ===========================================================================
   R22 — SCALE BAR: millimetres at the orbit target (exact in ortho)
   =========================================================================== */
const scaleEl = $("scalebar");
function drawScale(W, H){
  if (!scaleEl) return;
  const mmPerPx = 2*dist()*Math.tan(FOV/2) / Math.max(1, H);
  const want = 90*mmPerPx;                                 // aim for ~90 px
  const p10 = Math.pow(10, Math.floor(Math.log10(want)));
  const mm = [1, 2, 5, 10].map(k => k*p10).filter(v => v <= want*1.25).pop() || p10;
  const px = mm / mmPerPx;
  const txt = (mm >= 1 ? mm.toFixed(0) : mm.toPrecision(1)) + " mm" + (V7.ortho ? "" : " at target");
  // orbiting changes none of this: write the DOM only when the numbers move
  if (scaleEl._t !== txt){ scaleEl.querySelector("span").textContent = txt; scaleEl._t = txt; scaleEl.dataset.mm = mm; }
  const pw = px.toFixed(2);
  if (scaleEl._p !== pw){ scaleEl._p = pw; scaleEl.querySelector("i").style.width = px.toFixed(1) + "px"; scaleEl.dataset.px = pw; }
}
drawMotionOverlays = (orig => function(MVP, W, H){
  orig(MVP, W, H);
  drawTraces(MVP, W, H);
  drawScale(W, H);
})(drawMotionOverlays);

/* ===========================================================================
   R18 — PART SEARCH: type, Enter picks the first hit, fits it, opens it
   =========================================================================== */
let partQuery = "";
function filterParts(q){
  partQuery = q;
  const t = q.trim().toLowerCase();
  let first = null, byName = null, n = 0;
  for (const r of shBody.querySelectorAll(".row[data-id]")){
    const p = byId.get(r.dataset.id); if (!p) continue;
    const hit = !t || (p.label + " " + p.id + " " + (p.material || "") + " " + (p.note || "")).toLowerCase().includes(t);
    r.style.display = hit ? "" : "none";
    if (hit){ n++; if (!first) first = p; if (!byName && t && (p.label + " " + p.id).toLowerCase().includes(t)) byName = p; }
  }
  first = byName || first;                       // a name match beats a match buried in a note
  // a group heading stays only while something under it is still showing
  for (const g of shBody.querySelectorAll(".grp")){
    let s = g.nextElementSibling, any = !t;
    for (; s && !s.classList.contains("grp"); s = s.nextElementSibling)
      if (s.matches(".row[data-id]") && s.style.display !== "none") any = true;
    g.style.display = any ? "" : "none";
  }
  const c = $("pqCount"); if (c) c.textContent = t ? n + " found" : "";
  return first;
}
showParts = (orig => function(){
  orig();
  const box = el("div", "pq");
  const inp = document.createElement("input");
  inp.type = "search"; inp.id = "partQ"; inp.placeholder = "Find a part — name, material, note";
  inp.setAttribute("aria-label", "Find a part"); inp.value = partQuery; inp.autocomplete = "off";
  const cnt = el("span", "pqn"); cnt.id = "pqCount";
  inp.addEventListener("input", () => filterParts(inp.value));
  inp.addEventListener("keydown", e => {
    if (e.key === "Enter"){ e.preventDefault(); const p = filterParts(inp.value);
      if (p){ sel.clear(); sel.add(p.id); syncUI(); fitParts([p]); renderInspector(p); buzz(); } }
    else if (e.key === "Escape"){ inp.value = ""; filterParts(""); }
  });
  box.append(inp, cnt);
  shBody.prepend(box);
  if (partQuery) filterParts(partQuery);
})(showParts);

/* ===========================================================================
   R19 — BENCH CHECKLIST: tick steps off as you build; kept on this device
   =========================================================================== */
const DONE_KEY = "spav:" + SLUG + ":done";
const doneSet = new Set((lsGet(DONE_KEY) || "").split(",").filter(Boolean).map(Number));
const saveDone = () => lsSet(DONE_KEY, [...doneSet].sort((a, b) => a - b).join(","));
function syncDone(){
  const w = $("tl"); if (!w) return;
  for (const t of w.querySelectorAll(".tick")) t.classList.toggle("ok", doneSet.has(+t.dataset.n));
  const b = $("stDone");
  if (b){ const on = doneSet.has(step); b.setAttribute("aria-pressed", String(on)); b.textContent = on ? "✓ Done" : "Mark done"; }
  const c = $("stProg"); if (c) c.textContent = doneSet.size + " / " + NSTEP + " built";
}
showBuild = (orig => function(){
  orig();
  const w = $("tl"); if (!w) return;
  const bar = el("div", "dnbar");
  const b = el("button", "btn", "Mark done"); b.id = "stDone"; b.setAttribute("aria-pressed", "false");
  b.addEventListener("click", () => {
    doneSet.has(step) ? doneSet.delete(step) : doneSet.add(step); saveDone(); syncDone(); buzz();
  });
  const nx = el("button", "btn", "Next to build →"); nx.id = "stNext";
  nx.addEventListener("click", () => { for (let i = 1; i <= NSTEP; i++){ const n = ((step - 1 + i) % NSTEP) + 1;
    if (!doneSet.has(n)){ stopPlay(); gotoStep(n); return; } } flash("Every step is built"); });
  const pr = el("span", "dnp"); pr.id = "stProg";
  bar.append(b, nx, pr);
  const sab = w.querySelector(".sabar"); (sab || w.querySelector(".tlbar")).after(bar);
  syncDone();
})(showBuild);
paintStep = (orig => function(){ orig(); syncDone(); })(paintStep);

/* ===========================================================================
   R21 — LONG-PRESS A PART: select it and open its card (no hover on a phone)
   =========================================================================== */
let lp = null;
V7.lpFired = false;
cv.addEventListener("pointerdown", e => {
  clearTimeout(lp && lp.t); lp = null;
  if (motionMode || measOn || e.button !== 0 || ptrs.size > 1) return;
  const [cx, cy] = cssPt(e);
  lp = {x: e.clientX, y: e.clientY, t: setTimeout(() => {
    if (!lp || ptrs.size !== 1 || moved > 8) return;
    const h = raycast(cx, cy, true);
    if (!h) return;
    V7.lpFired = true; lp = null;
    sel.clear(); sel.add(h.part.id); syncUI();
    renderInspector(h.part); buzz(14);
  }, 520)};
});
cv.addEventListener("pointermove", e => { if (lp && Math.hypot(e.clientX - lp.x, e.clientY - lp.y) > 8){ clearTimeout(lp.t); lp = null; } });
for (const ev of ["pointerup", "pointercancel"]) cv.addEventListener(ev, () => { if (lp){ clearTimeout(lp.t); lp = null; } });
navTap = (orig => function(cx, cy, hp){
  if (V7.lpFired){ V7.lpFired = false; return true; }      // the release that ends a long-press is not a tap
  const r = orig(cx, cy, hp); if (r) buzz(); return r;
})(navTap);
cubeTo = (orig => function(N){ buzz(6); return orig(N); })(cubeTo);

/* ===========================================================================
   R23 — THE COPIED LINK CARRIES THE CAMERA (yaw, pitch, dist, pan, ortho)
   =========================================================================== */
V7.camLink = false;
hashNow = (orig => function(){
  const h = orig();
  if (!V7.camLink) return h;
  let kv = h.replace(/^#/, "");
  const m = /^(motion|step|plate|wire|part)-(.+)$/.exec(kv);
  if (m) kv = m[1] + "=" + encodeURIComponent(m[2]);
  else if (kv && !kv.includes("=")) kv = "tab=" + kv;
  const c = [cam.yaw, cam.pitch, cam.dist, PAN[0], PAN[1], PAN[2]].map(v => +v.toFixed(3)).join(",") + (V7.ortho ? ",o" : "");
  return "#" + (kv ? kv + "&" : "") + "cam=" + c;
})(hashNow);
$("shLink").addEventListener("click", () => { V7.camLink = true; setTimeout(() => { V7.camLink = false; }, 0); }, true);
function applyCam(s){
  const a = String(s).split(",");
  const v = a.slice(0, 6).map(Number);
  if (v.length < 3 || v.some(x => !isFinite(x))) return false;
  setOrtho(a[6] === "o");
  animGen++;                                    // stop whatever the tab switch started
  cam.yaw = v[0]; cam.pitch = Math.max(-1.45, Math.min(1.45, v[1])); cam.dist = v[2];
  PAN[0] = v[3] || 0; PAN[1] = v[4] || 0; PAN[2] = v[5] || 0;
  clearPreset(); draw(); return true;
}
applyHash = (orig => function(o){
  const did = orig(o);
  if (o && o.cam){
    // the tab switch glides for ~400 ms; land the camera after it
    setTimeout(() => applyCam(o.cam), V7RM() ? 0 : 480);
    return true;
  }
  return did;
})(applyHash);

/* ===========================================================================
   R24 — FOCUS: hide the header, presets and explode row; the model gets the
   screen. Tools, the dock and the sheet stay where the thumb is.
   =========================================================================== */
function setFocus(on){
  document.documentElement.classList.toggle("av-focus", !!on);
  const b = $("bFocus"); if (b) b.setAttribute("aria-pressed", String(!!on));
  setTimeout(() => { syncSvg(); updateShift(); vcSize(); draw(); }, 30);
}
$("bFocus") && $("bFocus").addEventListener("click", () => setFocus(!document.documentElement.classList.contains("av-focus")));

/* ---------- verifier hooks ---------- */
Object.assign(window.__avV7, {
  traces: () => V7.traceCount || 0,
  scale: () => scaleEl ? {mm: +scaleEl.dataset.mm, px: +scaleEl.dataset.px, text: scaleEl.textContent,
                          mmPerPx: 2*dist()*Math.tan(FOV/2) / Math.max(1, cv.getBoundingClientRect().height)} : null,
  done: () => [...doneSet].sort((a, b) => a - b),
  cutList: () => cutListCSV(),
  camHash: () => { V7.camLink = true; try { return hashNow(); } finally { V7.camLink = false; } },
  focus: setFocus,
});
