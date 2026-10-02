/* ===========================================================================
   SP AV ENGINE v7.3 — module (inlined by patch_engine_v7_3.py, before BOOT,
   after v7 / v7.1 / v7.2)
   R29 Gap tool: tap two parts -> minimum clearance, closest points, a 3D
       dimension line, and the FDM verdict (< 0.2 mm will fuse or bind)
   R30 Tight-gaps report: every pair of parts closer than 2 mm that does not
       touch, smallest first — CHECKPOINT's open "Stage 4 clearance callouts"
   R31 BOM CSV: the order list, with bulk breaks, status and supplier links
   R32 Section handle: drag the cut plane on the model itself
   =========================================================================== */
V7.ver = "7.3";
const FDM_MIN = 0.2;                 // mm — under this two printed faces fuse or bind (CHECKPOINT Stage 4)
const FLUSH = 0.005;                 // mm — closer than this is two faces sitting flush (int16 geometry is ~2 µm)

/* ===========================================================================
   R29 — GAP: the same BVH distance query the Motion lane uses for clearance
   =========================================================================== */
function gapBetween(pa, pb, maxD){
  const A = modelOf(pa), B = modelOf(pb);
  const r = MC.distance(bvhOf(pa), bvhOf(pb), MC.mul4(MC.inv4(A), B), maxD == null ? 1e30 : maxD);
  if (!r.pa && r.d !== 0) return null;                               // further than maxD
  return {d: r.d, pa: r.pa ? MC.xf(A, r.pa) : null, pb: r.pb ? MC.xf(A, r.pb) : null};
}
/* printed = at least one of the two is FDM: its faces land ±0.2 mm off the model */
const gapVerdict = (d, printed) => d < FLUSH ? {cls: "bad", txt: "touching (flush or clashing)"}
  : d < FDM_MIN && printed !== false ? {cls: "warn", txt: "under " + FDM_MIN + " mm — prints fused / binds"}
  : d < FDM_MIN ? {cls: "ok", txt: "tight, but neither part is printed"}
  : {cls: "ok", txt: "prints free"};
const anyPrinted = (a, b) => a.kind === "printed" || b.kind === "printed";
let gapOn = false, gapPick = [], GAP = null;
function setGap(on){
  gapOn = !!on; gapPick = [];
  const b = $("bGap"); if (b) b.setAttribute("aria-pressed", String(gapOn));
  if (gapOn){ if (diaOn) setDia(false); if (measOn) $("bMeas").click(); flash2("Gap · tap the first part", "then the second"); }
  cv.style.cursor = gapOn ? "crosshair" : "";
  draw();
}
$("bGap") && $("bGap").addEventListener("click", () => setGap(!gapOn));
setDia = (orig => function(on){ if (on && gapOn) setGap(false); return orig(on); })(setDia);   // one pick tool at a time
navTap = (orig => function(cx, cy, hp){
  if (!gapOn || V7.lpFired) return orig(cx, cy, hp);
  const h = raycast(cx, cy, true);
  if (!h){ flash("No part under that tap"); return true; }
  if (gapPick.length >= 2) gapPick = [];
  if (gapPick[0] === h.part.id){ flash("That is the same part — tap a second one"); return true; }
  gapPick.push(h.part.id);
  sel.clear(); for (const id of gapPick) sel.add(id); syncUI();
  if (gapPick.length < 2){ flash2("Gap · " + h.part.label, "now tap the second part"); return true; }
  const [a, b] = gapPick.map(id => byId.get(id));
  const g = gapBetween(a, b);
  GAP = g && {a: a.id, b: b.id, ...g};
  const v = g ? gapVerdict(g.d, anyPrinted(a, b)) : null;
  if (g) flash2("Gap " + g.d.toFixed(2) + " mm", a.label + " ↔ " + b.label + " · " + v.txt);
  buzz(10); draw(); return true;
})(navTap);
const gapEl = document.createElement("div"); gapEl.className = "gaplab"; marks.appendChild(gapEl);
let gapLine = null;
function drawGap(MVP, W, H){
  if (!gapLine){ gapLine = document.createElementNS("http://www.w3.org/2000/svg", "line"); gapLine.setAttribute("class", "gapln");
                 gapLine.setAttribute("marker-start", "url(#arwf)"); gapLine.setAttribute("marker-end", "url(#arwf)"); leads.appendChild(gapLine); }
  const g = GAP && GAP.pa && GAP.pb && sel.has(GAP.a) && sel.has(GAP.b) ? GAP : null;
  const s0 = g && project(MVP, g.pa, W, H), s1 = g && project(MVP, g.pb, W, H);
  const on = !!(s0 && s1);
  showEl(gapLine, on); showEl(gapEl, on);
  if (!on) return;
  gapLine.setAttribute("x1", s0[0]); gapLine.setAttribute("y1", s0[1]); gapLine.setAttribute("x2", s1[0]); gapLine.setAttribute("y2", s1[1]);
  gapEl.textContent = g.d.toFixed(2) + " mm";
  gapEl.className = "gaplab " + gapVerdict(g.d, anyPrinted(byId.get(g.a), byId.get(g.b))).cls;
  gapEl.style.transform = `translate(${((s0[0]+s1[0])/2).toFixed(1)}px,${((s0[1]+s1[1])/2 - 16).toFixed(1)}px)`;
}

/* ===========================================================================
   R30 — TIGHT GAPS: every non-touching pair within 2 mm, smallest first
   =========================================================================== */
let TIGHT = null;
async function tightGaps(within, onProgress){
  within = within || 2;
  const sol = parts.filter(p => state(p) === "solid" && p.kind !== "wire" && p.kind !== "screw");
  const mats = new Map(sol.map(p => [p.id, modelOf(p)]));
  const box = new Map(sol.map(p => [p.id, wbox(p, mats.get(p.id))]));
  const cand = [];
  for (let i = 0; i < sol.length; i++) for (let k = i+1; k < sol.length; k++)
    if (boxHit(box.get(sol[i].id), box.get(sol[k].id), within)) cand.push([sol[i], sol[k]]);
  const out = [], t0 = performance.now();
  for (let i = 0; i < cand.length; i++){
    const [pa, pb] = cand[i];
    const g = gapBetween(pa, pb, within);
    if (g && g.d >= FLUSH && g.d < within) out.push({a: pa.id, b: pb.id, d: +g.d.toFixed(3), pa: g.pa, pb: g.pb,
                                                     printed: anyPrinted(pa, pb)});
    if (i % 8 === 7){ if (onProgress) onProgress(i+1, cand.length); await new Promise(r => setTimeout(r, 0)); }
  }
  out.sort((x, y) => x.d - y.d);
  TIGHT = {pairs: out, candidates: cand.length, ms: Math.round(performance.now() - t0), within};
  return TIGHT;
}
function showGapPair(g){
  const a = byId.get(g.a), b = byId.get(g.b); if (!a || !b) return;
  GAP = {a: a.id, b: b.id, d: g.d, pa: g.pa, pb: g.pb};
  sel.clear(); sel.add(a.id); sel.add(b.id); isolate = true; syncUI(); fitParts([a, b]);
  flash2("Gap " + g.d.toFixed(2) + " mm", a.label + " ↔ " + b.label + " · " + gapVerdict(g.d, g.printed).txt);
}
showChecks = (orig => function(){
  orig();
  shBody.appendChild(el("div", "sect", "Tight gaps · under 2 mm"));
  const card = el("div", "ckcard"); card.id = "gapCard";
  const run = el("button", "btn pri", TIGHT ? "Re-scan" : "Find tight gaps"); run.id = "bTight";
  const out = el("div"); out.id = "tightOut";
  run.addEventListener("click", async () => {
    run.disabled = true; run.textContent = "measuring…";
    await tightGaps(2, (i, n) => { run.textContent = "measuring " + i + " / " + n; });
    run.disabled = false; run.textContent = "Re-scan"; paintTight(out); buzz(12);
  });
  const gb = el("button", "btn", gapOn ? "Gap on — tap two parts" : "Measure the gap between two parts"); gb.id = "bGapSheet";
  gb.addEventListener("click", () => { setGap(!gapOn); gb.textContent = gapOn ? "Gap on — tap two parts" : "Measure the gap between two parts";
    if (gapOn && !wide()) closeSheet(); });
  card.append(gb, run, out); shBody.appendChild(card);
  if (TIGHT) paintTight(out);
})(showChecks);
function paintTight(out){
  out.textContent = "";
  const risk = TIGHT.pairs.filter(g => g.d < FDM_MIN && g.printed);
  const k = el("div", "kpis"); k.style.gridTemplateColumns = "repeat(3,1fr)";
  const t = (lab, v, cls) => { const d = el("div", "kpi" + (cls ? " " + cls : "")); d.appendChild(el("div", "k", lab));
    d.appendChild(el("div", "v", String(v))); return d; };
  k.appendChild(t("Print risk < 0.2", risk.length, risk.length ? "bad" : "accent"));
  k.appendChild(t("Under 2 mm", TIGHT.pairs.length));
  k.appendChild(t("Tightest", TIGHT.pairs.length ? TIGHT.pairs[0].d.toFixed(2) + " mm" : "—"));
  out.appendChild(k);
  out.appendChild(el("div", "ckline", `${TIGHT.candidates} close pairs measured · ${TIGHT.ms} ms · screws left out (their holes are sized by the screw table)`));
  for (const g of TIGHT.pairs.slice(0, 40)){
    const a = byId.get(g.a), b = byId.get(g.b), v = gapVerdict(g.d, g.printed);
    const r = el("div", "ckrow " + (v.cls === "warn" ? "clash" : "contact")); r.tabIndex = 0; r.setAttribute("role", "button");
    r.appendChild(el("span", "ckg", v.cls === "warn" ? "!" : "↔"));
    r.appendChild(el("span", "ckp", (a ? a.label : g.a) + "  ↔  " + (b ? b.label : g.b)));
    r.appendChild(el("span", "ckd", g.d.toFixed(2) + " mm"));
    const go = () => showGapPair(g);
    r.addEventListener("click", go);
    r.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " "){ e.preventDefault(); go(); } });
    out.appendChild(r);
  }
}

/* ===========================================================================
   R31 — BOM CSV: what you paste into an order, numbers exactly as the tab shows
   =========================================================================== */
function bomCSV(){
  const q = v => { const s = String(v == null ? "" : v); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
  const money = v => v == null ? "" : (+v).toFixed(2);
  const rows = [["item","qty","status","each","line","each_x10","each_x50","each_x100","supplier","url","checked","part_id"]];
  for (const r of bomRows()){
    const c = r.cost || {};
    const st = bomStatus(r);
    rows.push([r.label, r.qty, st || "", money(c.each), c.each != null ? money(c.each*r.qty) : "TBD",
               money(bulkAt(r, 10)), money(bulkAt(r, 50)), money(bulkAt(r, 100)), c.supplier || "", c.url || "", c.checked || "", r.id || ""]);
  }
  return rows.map(r => r.map(q).join(",")).join("\n") + "\n";
}
showBom = (orig => function(){
  orig();
  const a = el("div", "acts");
  const b = el("button", "btn", "⤓ BOM (CSV)"); b.id = "bBomCsv";
  b.addEventListener("click", () => saveDirect(new Blob([bomCSV()], {type: "text/csv"}), SLUG + "_bom.csv", b));
  a.appendChild(b);
  shBody.appendChild(a);
})(showBom);

/* ===========================================================================
   R32 — SECTION HANDLE: grab the cut where it is and pull it along its axis
   =========================================================================== */
const secH = document.createElement("div"); secH.className = "sechandle"; secH.setAttribute("role", "slider");
secH.setAttribute("aria-label", "Drag the cut plane"); secH.tabIndex = 0; secH.innerHTML = "<i></i>";
$("stage").appendChild(secH);
let secDrag = null;
function secAnchor(){                                  // the plane's centre and its axis, on screen
  const n = [0,0,0]; n[sectAxis] = 1;
  const c = [(BB.lo[0]+BB.hi[0])/2, (BB.lo[1]+BB.hi[1])/2, (BB.lo[2]+BB.hi[2])/2]; c[sectAxis] = sectValue();
  const {MVP, W, H} = curMVP();
  const s0 = project(MVP, c, W, H), s1 = project(MVP, add(c, scl(n, 10)), W, H);
  return s0 && s1 ? {s0, ax: [(s1[0]-s0[0])/10, (s1[1]-s0[1])/10]} : null;   // px per mm along the axis
}
function placeSecHandle(){
  const a = sectOn && !plateMode ? secAnchor() : null;
  showEl(secH, !!a);
  if (!a) return;
  const ang = Math.atan2(a.ax[1], a.ax[0]) * 180/Math.PI;
  secH.style.transform = `translate(${a.s0[0].toFixed(1)}px,${a.s0[1].toFixed(1)}px) rotate(${ang.toFixed(1)}deg)`;
}
function moveSect(mm){
  const [lo, hi] = sectRange();
  sectT = Math.max(0, Math.min(1, sectT + mm/(hi - lo)));
  $("sec").value = Math.round(sectT*1000); syncSect();
}
secH.addEventListener("pointerdown", e => { e.stopPropagation(); secH.setPointerCapture(e.pointerId);
  secDrag = {x: e.clientX, y: e.clientY, a: secAnchor()}; beginInteract(); });
secH.addEventListener("pointermove", e => {
  if (!secDrag || !secDrag.a) return;
  const ax = secDrag.a.ax, L2 = ax[0]*ax[0] + ax[1]*ax[1]; if (L2 < 1e-6) return;
  const dx = e.clientX - secDrag.x, dy = e.clientY - secDrag.y;
  moveSect((dx*ax[0] + dy*ax[1]) / L2);                  // pixels along the axis -> mm
  secDrag.x = e.clientX; secDrag.y = e.clientY; secDrag.a = secAnchor();
});
for (const ev of ["pointerup", "pointercancel"]) secH.addEventListener(ev, () => { if (secDrag){ secDrag = null; endInteract(); } });
secH.addEventListener("keydown", e => {
  if (e.key === "ArrowRight" || e.key === "ArrowUp"){ e.preventDefault(); moveSect(1); }
  else if (e.key === "ArrowLeft" || e.key === "ArrowDown"){ e.preventDefault(); moveSect(-1); }
});
drawMotionOverlays = (orig => function(MVP, W, H){
  orig(MVP, W, H);
  drawGap(MVP, W, H);
  placeSecHandle();
})(drawMotionOverlays);
$("bReset").addEventListener("click", () => { if (gapOn) setGap(false); GAP = null; });

/* ---------- verifier hooks ---------- */
Object.assign(window.__avV7, {
  gap: (a, b) => { const g = gapBetween(byId.get(a), byId.get(b)); return g && {d: g.d, pa: g.pa, pb: g.pb}; },
  gapBrute: (a, b) => {                  // every triangle of A against every triangle of B, no BVH
    const pa = byId.get(a), pb = byId.get(b), A = modelOf(pa), B = modelOf(pb);
    const fa = floatsOf(pa), fb = floatsOf(pb), Mx = MC.mul4(MC.inv4(A), B);
    const tb = []; for (let j = 0; j < fb.length; j += 9) tb.push([0,3,6].map(k => MC.xf(Mx, [fb[j+k], fb[j+k+1], fb[j+k+2]])));
    let best = 1e30;
    for (let i = 0; i < fa.length; i += 9){
      const P = [[fa[i],fa[i+1],fa[i+2]],[fa[i+3],fa[i+4],fa[i+5]],[fa[i+6],fa[i+7],fa[i+8]]];
      for (const T of tb){ const r = MC.triDist(P, T); if (r.d < best) best = r.d; }
    }
    return best;
  },
  tight: async () => { const t = await tightGaps(2); return {n: t.pairs.length, candidates: t.candidates, ms: t.ms,
    risk: t.pairs.filter(g => g.d < FDM_MIN && g.printed).map(g => ({a: g.a, b: g.b, d: g.d})),
    first: t.pairs.slice(0, 6).map(g => ({a: g.a, b: g.b, d: g.d, printed: g.printed}))}; },
  bomCSV: () => bomCSV(),
  setGap, secHandle: () => { const a = sectOn ? secAnchor() : null; return a && {x: a.s0[0], y: a.s0[1], ax: a.ax, t: sectT, v: sectValue()}; },
});
