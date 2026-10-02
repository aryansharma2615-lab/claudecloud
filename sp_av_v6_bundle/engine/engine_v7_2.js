/* ===========================================================================
   SP AV ENGINE v7.2 — module (inlined by patch_engine_v7_2.py, before BOOT,
   after v7 and v7.1). CAD-quality tools, in one new dock tab: Checks.
   R25 Checks lane (ports the v5.3 META.checks tiles into the v6 line)
   R26 Clash scan of the assembled pose: clash / contact / by design
   R27 Centre of gravity + support footprint + the tilt it tips over at
   R28 Ø tool: three taps on a hole's rim -> diameter and centre
   =========================================================================== */
V7.ver = "7.2";
/* write display only when it changes: an untouched overlay costs nothing per frame */
const showEl = (e, on) => { if (e._on !== on){ e._on = on; e.style.display = on ? "" : "none"; } };

/* ===========================================================================
   R26 — CLASH SCAN
   Every pair of solid parts whose boxes overlap is walked with the same BVH
   the Motion lane uses, collecting EVERY intersecting triangle pair, then
   each hit is sorted:
     contact  faces lying in one plane, or an edge resting on a face (nothing
              of either triangle reaches more than 0.05 mm into the other)
     clash    both triangles cross into each other's solid by more than that
   and each pair: by design (a screw into its host, a declared touch / gear
   mesh, a heat-set insert or a press-fit bearing in its seat), clash, contact.
   =========================================================================== */
const PEN = 0.05;                                  // mm — below this a crossing is a touch
function nodeBoxIn(Bv, b, M){                      // node b of B, as an AABB in A's frame
  const o = b*6, bb = Bv.bb;
  const c = [(bb[o]+bb[o+3])/2, (bb[o+1]+bb[o+4])/2, (bb[o+2]+bb[o+5])/2];
  const e = [(bb[o+3]-bb[o])/2, (bb[o+4]-bb[o+1])/2, (bb[o+5]-bb[o+2])/2];
  const C = MC.xf(M, c);
  const E = [Math.abs(M[0])*e[0]+Math.abs(M[4])*e[1]+Math.abs(M[8])*e[2],
             Math.abs(M[1])*e[0]+Math.abs(M[5])*e[1]+Math.abs(M[9])*e[2],
             Math.abs(M[2])*e[0]+Math.abs(M[6])*e[1]+Math.abs(M[10])*e[2]];
  return [C[0]-E[0], C[1]-E[1], C[2]-E[2], C[0]+E[0], C[1]+E[1], C[2]+E[2]];
}
const triN = (a, b, c) => nrm(cross(sub(b, a), sub(c, a)));
/* how far the triangle T reaches behind the plane of P (into P's solid), mm */
function reachBehind(P, T){
  const n = triN(P[0], P[1], P[2]);
  let d = 0; for (const v of T) d = Math.max(d, -dot(n, sub(v, P[0])));
  return d;
}
function collideAll(A, B, M, cap){
  const out = {contact: 0, clash: 0, depth: 0, at: null, pairs: 0};
  if (!A.nt || !B.nt) return out;
  const sa = [0], sb = [0], fa = A.f, fb = B.f;
  while (sa.length){
    const a = sa.pop(), b = sb.pop();
    const ab = A.bb, o = a*6, bx = nodeBoxIn(B, b, M);
    if (ab[o] > bx[3]+1e-3 || ab[o+3] < bx[0]-1e-3 || ab[o+1] > bx[4]+1e-3 || ab[o+4] < bx[1]-1e-3 ||
        ab[o+2] > bx[5]+1e-3 || ab[o+5] < bx[2]-1e-3) continue;
    const la = A.L[a] < 0, lb = B.L[b] < 0;
    if (la && lb){
      for (let i = A.S[a]; i < A.S[a]+A.C[a]; i++){
        const ta = A.idx[i]*9;
        const P = [[fa[ta],fa[ta+1],fa[ta+2]], [fa[ta+3],fa[ta+4],fa[ta+5]], [fa[ta+6],fa[ta+7],fa[ta+8]]];
        for (let j = B.S[b]; j < B.S[b]+B.C[b]; j++){
          const tb = B.idx[j]*9;
          const T = [0,1,2].map(k => MC.xf(M, [fb[tb+k*3], fb[tb+k*3+1], fb[tb+k*3+2]]));
          if (!MC.triTri(P[0],P[1],P[2], T[0],T[1],T[2])) continue;
          out.pairs++;
          const d = Math.min(reachBehind(P, T), reachBehind(T, P));
          if (d > PEN){ out.clash++; if (d > out.depth){ out.depth = d; out.at = [(P[0][0]+P[1][0]+P[2][0])/3, (P[0][1]+P[1][1]+P[2][1])/3, (P[0][2]+P[1][2]+P[2][2])/3]; } }
          else { out.contact++; if (!out.at) out.at = P[0]; }
          if (out.pairs >= cap) return out;
        }
      }
      continue;
    }
    const sizeOf = (bb, n) => (bb[n*6+3]-bb[n*6]) + (bb[n*6+4]-bb[n*6+1]) + (bb[n*6+5]-bb[n*6+2]);
    if (la || (!lb && sizeOf(B.bb, b) > sizeOf(A.bb, a))){ sa.push(a, a); sb.push(B.L[b], B.R[b]); }
    else { sa.push(A.L[a], A.R[a]); sb.push(b, b); }
  }
  return out;
}
function designedWhy(pa, pb){
  if (allowed.has(pk(pa.id, pb.id))) return "declared contact";
  for (const [x, y] of [[pa, pb], [pb, pa]]){
    if (x.kind === "screw" && x.screw && (x.screw.host === y.id || (x.screw.into || []).includes(y.id))) return "screw in its host";
    const t = (x.id + " " + x.label).toLowerCase();
    if (/insert|brass/.test(t)) return "heat-set insert";
    if (/bearing|608|6\d\dzz|bushing/.test(t)) return "press-fit bearing";
    if (x.kind === "screw" && x.screw) return "screw thread";
  }
  return null;
}
let CLASH = null;                                   // last scan
async function clashScan(onProgress){
  const sol = parts.filter(p => state(p) === "solid" && p.kind !== "wire");
  const mats = new Map(sol.map(p => [p.id, modelOf(p)]));
  const box = new Map(sol.map(p => [p.id, wbox(p, mats.get(p.id))]));
  const cand = [];
  for (let i = 0; i < sol.length; i++) for (let k = i+1; k < sol.length; k++)
    if (boxHit(box.get(sol[i].id), box.get(sol[k].id), 0.01)) cand.push([sol[i], sol[k]]);
  const res = [], t0 = performance.now();
  for (let i = 0; i < cand.length; i++){
    const [pa, pb] = cand[i];
    const A = mats.get(pa.id), B = mats.get(pb.id);
    const r = collideAll(bvhOf(pa), bvhOf(pb), MC.mul4(MC.inv4(A), B), 20000);
    if (r.pairs){
      const why = designedWhy(pa, pb);
      res.push({a: pa.id, b: pb.id, kind: why ? "design" : r.clash ? "clash" : "contact", why,
                tris: r.pairs, crossing: r.clash, depth: +r.depth.toFixed(2), at: r.at ? MC.xf(A, r.at) : null});
    }
    if (i % 6 === 5){ if (onProgress) onProgress(i+1, cand.length); await new Promise(r2 => setTimeout(r2, 0)); }
  }
  const rank = {clash: 0, design: 1, contact: 2};
  res.sort((x, y) => rank[x.kind] - rank[y.kind] || y.depth - x.depth);
  CLASH = {pairs: res, candidates: cand.length, parts: sol.length, ms: Math.round(performance.now() - t0),
           pose: explode.toFixed(3) + "|" + (motionMode ? "m" : "") + "|" + step + stepMode};
  return CLASH;
}
function showClashPair(c){
  const a = byId.get(c.a), b = byId.get(c.b); if (!a || !b) return;
  sel.clear(); sel.add(a.id); sel.add(b.id); isolate = true;
  moTint.clear();
  if (c.kind === "clash"){ const red = hex(cssVar("--bad") || "#e87466"); moTint.set(a.id, red); moTint.set(b.id, red); }
  V7.clashAt = c.at;
  syncUI(); fitParts([a, b]);
  flash2(a.label + "  ×  " + b.label, c.kind === "clash" ? `cuts in · up to ${c.depth} mm · ${c.crossing} crossing facets`
        : c.kind === "design" ? "by design · " + c.why : "touching · " + c.tris + " facets in contact");
}

/* ===========================================================================
   R27 — CENTRE OF GRAVITY, FOOTPRINT, TIP ANGLE
   Mass per part: its `mass` {g, com} when the config has one (Motion builds
   do), else printed `print.grams` at the mesh's volume centroid. The tip
   angle is the static one: atan(distance from the CoG's ground point to the
   nearest footprint edge / CoG height) — tilt the base past it and it falls.
   =========================================================================== */
const centroidCache = new Map();
function meshCentroid(p){
  let c = centroidCache.get(p.id); if (c) return c;
  const f = floatsOf(p); let V = 0, x = 0, y = 0, z = 0;
  for (let t = 0; t < f.length; t += 9){
    const v = (f[t]*(f[t+4]*f[t+8]-f[t+5]*f[t+7]) - f[t+1]*(f[t+3]*f[t+8]-f[t+5]*f[t+6]) + f[t+2]*(f[t+3]*f[t+7]-f[t+4]*f[t+6]))/6;
    V += v; x += v*(f[t]+f[t+3]+f[t+6])/4; y += v*(f[t+1]+f[t+4]+f[t+7])/4; z += v*(f[t+2]+f[t+5]+f[t+8])/4;
  }
  c = Math.abs(V) > 1e-9 ? [x/V, y/V, z/V] : [p.lo[0]+p.span[0]/2, p.lo[1]+p.span[1]/2, p.lo[2]+p.span[2]/2];
  centroidCache.set(p.id, c); return c;
}
function massOfPart(p){
  if (p.mass && p.mass.g) return {g: +p.mass.g, com: p.mass.com || meshCentroid(p), src: "config"};
  if (p.print && p.print.grams) return {g: +p.print.grams, com: meshCentroid(p), src: "print"};
  return null;
}
function hull2(pts){                                   // monotone chain, CCW
  pts = pts.slice().sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  if (pts.length < 3) return pts;
  const cr = (o, a, b) => (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0]);
  const lo = [], up = [];
  for (const p of pts){ while (lo.length >= 2 && cr(lo[lo.length-2], lo[lo.length-1], p) <= 0) lo.pop(); lo.push(p); }
  for (let i = pts.length-1; i >= 0; i--){ const p = pts[i]; while (up.length >= 2 && cr(up[up.length-2], up[up.length-1], p) <= 0) up.pop(); up.push(p); }
  up.pop(); lo.pop(); return lo.concat(up);
}
function cogNow(){
  const sol = parts.filter(p => state(p) !== "off" && p.kind !== "wire");
  let g = 0, x = 0, y = 0, z = 0, missing = 0;
  for (const p of sol){
    const m = massOfPart(p); if (!m){ if (p.kind !== "screw") missing++; continue; }
    const w = M.xform(modelOf(p), m.com);
    g += m.g; x += m.g*w[0]; y += m.g*w[1]; z += m.g*w[2];
  }
  if (!g) return null;
  const com = [x/g, y/g, z/g];
  // footprint: everything within 0.6 mm of the lowest point is standing on the ground
  let gz = 1e9; for (const p of sol){ const b = wbox(p, modelOf(p)); gz = Math.min(gz, b[2]); }
  const foot = [];
  for (const p of sol){
    const m = modelOf(p), b = wbox(p, m);
    if (b[2] > gz + 0.6) continue;
    const f = floatsOf(p);
    for (let i = 0; i < f.length; i += 3){
      const w = M.xform(m, [f[i], f[i+1], f[i+2]]);
      if (w[2] <= gz + 0.6) foot.push([w[0], w[1]]);
    }
  }
  const hull = hull2(foot);
  // signed distance from the CoG's ground point to the hull (+ inside)
  let dmin = Infinity, inside = hull.length >= 3;
  for (let i = 0; i < hull.length; i++){
    const a = hull[i], b = hull[(i+1) % hull.length];
    const ex = b[0]-a[0], ey = b[1]-a[1], L = Math.hypot(ex, ey) || 1;
    const s = (ex*(com[1]-a[1]) - ey*(com[0]-a[0])) / L;        // left of a CCW edge = inside
    if (s < 0) inside = false;
    const t = Math.max(0, Math.min(1, ((com[0]-a[0])*ex + (com[1]-a[1])*ey)/(L*L)));
    dmin = Math.min(dmin, Math.hypot(com[0]-(a[0]+t*ex), com[1]-(a[1]+t*ey)));
  }
  const margin = hull.length >= 3 ? (inside ? dmin : -dmin) : null;
  const h = com[2] - gz;
  return {g, com, ground: gz, hull, margin, h, tipDeg: margin != null && h > 0 ? Math.atan2(margin, h)*180/Math.PI : null, missing};
}
let cogOn = false, cogCache = null, cogKey = "";
const cogEl = document.createElement("div"); cogEl.className = "cog"; cogEl.innerHTML = "<span>CoG</span>"; marks.appendChild(cogEl);
let cogDrop = null, cogHull = null;
function drawCog(MVP, W, H){
  if (!cogDrop){
    cogDrop = document.createElementNS("http://www.w3.org/2000/svg", "line"); cogDrop.setAttribute("class", "cogdrop");
    cogHull = document.createElementNS("http://www.w3.org/2000/svg", "polygon"); cogHull.setAttribute("class", "coghull");
    leads.appendChild(cogHull); leads.appendChild(cogDrop);
  }
  const show = cogOn && !plateMode && !wireMode;
  if (!show && cogEl._on === false){ return; }
  if (show){
    const k = explode.toFixed(3) + "|" + step + stepMode + "|" + hidden.size + "|" + (motionMode && MS ? JSON.stringify(MS.q) : "");
    if (k !== cogKey){ cogKey = k; cogCache = cogNow(); }
  }
  const c = show ? cogCache : null;
  const s = c && project(MVP, c.com, W, H), s0 = c && project(MVP, [c.com[0], c.com[1], c.ground], W, H);
  showEl(cogEl, !!s); showEl(cogDrop, !!(s && s0)); showEl(cogHull, !!c);
  if (!s) return;
  cogEl.style.transform = `translate(${s[0].toFixed(1)}px,${s[1].toFixed(1)}px)`;
  cogEl.classList.toggle("bad", c.margin != null && c.margin < 0);
  if (s0){ cogDrop.setAttribute("x1", s[0]); cogDrop.setAttribute("y1", s[1]); cogDrop.setAttribute("x2", s0[0]); cogDrop.setAttribute("y2", s0[1]); }
  const hp = c.hull.map(q => project(MVP, [q[0], q[1], c.ground], W, H)).filter(Boolean);
  cogHull.setAttribute("points", hp.map(q => q[0].toFixed(1) + "," + q[1].toFixed(1)).join(" "));
}

/* ===========================================================================
   R28 — Ø TOOL: three taps on a hole's rim (each snaps to the nearest mesh
   corner, like Measure) -> the circle through them: diameter + centre
   =========================================================================== */
function circle3(a, b, c){
  const ab = sub(b, a), ac = sub(c, a), n = cross(ab, ac), n2 = dot(n, n);
  if (n2 < 1e-12) return null;                         // collinear
  const t = add(scl(cross(n, ab), dot(ac, ac)), scl(cross(ac, n), dot(ab, ab)));
  const ctr = add(a, scl(t, 1/(2*n2)));
  return {centre: ctr, r: Math.hypot(...sub(a, ctr)), normal: nrm(n)};
}
let diaOn = false; const diaPts = [];
function setDia(on){
  diaOn = !!on; diaPts.length = 0;
  const b = $("bDia"); if (b) b.setAttribute("aria-pressed", String(diaOn));
  if (diaOn && measOn) $("bMeas").click();
  cv.style.cursor = diaOn ? "crosshair" : "";
  if (diaOn) flash2("Ø · tap 3 points on the rim", "each tap snaps to the nearest corner of the mesh");
  draw();
}
$("bDia") && $("bDia").addEventListener("click", () => setDia(!diaOn));
navTap = (orig => function(cx, cy, hp){
  if (!diaOn || V7.lpFired) return orig(cx, cy, hp);
  const h = raycast(cx, cy);
  if (!h){ flash("No part under that tap"); return true; }
  if (diaPts.length >= 3) diaPts.length = 0;
  diaPts.push({part: h.part.id, local: h.local});
  if (diaPts.length < 3) flash2("Ø · " + diaPts.length + " / 3", "next point on the same rim");
  else {
    const w = diaPts.map(q => M.xform(modelOf(byId.get(q.part)), q.local));
    const c = circle3(w[0], w[1], w[2]);
    V7.dia = c ? {d: 2*c.r, centre: c.centre} : null;
    if (c) flash2("Ø " + (2*c.r).toFixed(2) + " mm", "centre " + c.centre.map(v => v.toFixed(2)).join(", ") + " mm");
    else flash("Those three points are in a line — tap around the rim");
  }
  buzz(); draw(); return true;
})(navTap);
const diaDots = [];
function drawDia(MVP, W, H){
  while (diaDots.length < 3){ const d = document.createElement("div"); d.className = "dot dia"; marks.appendChild(d); diaDots.push(d); }
  diaDots.forEach((d, i) => {
    const q = diaOn && diaPts[i];
    const s = q && project(MVP, M.xform(modelOf(byId.get(q.part)), q.local), W, H);
    showEl(d, !!s);
    if (s) d.style.transform = `translate(${s[0]}px,${s[1]}px)`;
  });
}
drawMotionOverlays = (orig => function(MVP, W, H){
  orig(MVP, W, H);
  drawCog(MVP, W, H);
  drawDia(MVP, W, H);
  const at = V7.clashAt && sel.size === 2 ? project(MVP, V7.clashAt, W, H) : null;
  showEl(clashDot, !!at);
  if (at) clashDot.style.transform = `translate(${at[0]}px,${at[1]}px)`;
})(drawMotionOverlays);
const clashDot = document.createElement("div"); clashDot.className = "dot clashp"; clashDot.style.display = "none"; marks.appendChild(clashDot);

/* ===========================================================================
   R25 — THE CHECKS TAB: the project's own gates (META.checks, from the v5.3
   line), then the three live tools above
   =========================================================================== */
function showChecks(){
  shTitle.textContent = "Checks";
  shBody.textContent = "";
  const C = META.checks || [];
  if (C.length){
    const n = s => C.filter(c => c.status === s).length;
    const k = el("div", "kpis"); k.style.gridTemplateColumns = "repeat(3,1fr)";
    const tile = (lab, v, cls) => { const t = el("div", "kpi" + (cls ? " " + cls : "")); t.appendChild(el("div", "k", lab));
      t.appendChild(el("div", "v", String(v))); return t; };
    k.appendChild(tile("Pass", n("pass"), n("pass") === C.length ? "accent" : ""));
    k.appendChild(tile("Warn", n("warn"), ""));
    k.appendChild(tile("Fail", n("fail"), n("fail") ? "bad" : ""));
    shBody.appendChild(k);
    for (const g of [...new Set(C.map(c => c.group || "Checks"))]){
      shBody.appendChild(el("div", "grp", g));
      const box = el("div", "lbars");
      for (const c of C.filter(c => (c.group || "Checks") === g)){
        const st = c.status || "pass";
        const r = el("div", "lbar" + (st === "fail" ? " bad" : st === "warn" ? " warn" : ""));
        r.appendChild(el("div", "lbl", (st === "fail" ? "✗ " : st === "warn" ? "! " : "✓ ") + c.label));
        const num = typeof c.value === "number";
        r.appendChild(el("div", "lval", num ? (c.value.toFixed(Math.abs(c.value) < 10 ? 2 : 0) + (c.unit ? " " + c.unit : "")
          + (c.limit != null ? "  / " + c.limit + (c.unit ? " " + c.unit : "") : "")) : String(c.value)));
        if (num && c.limit){ const tr = el("div", "ltrack"), f = el("div", "lfill");
          f.style.width = Math.max(1, Math.min(100, 100*c.value/c.limit)) + "%"; tr.appendChild(f); r.appendChild(tr); }
        box.appendChild(r);
      }
      shBody.appendChild(box);
    }
  }
  /* ---- centre of gravity ---- */
  shBody.appendChild(el("div", "sect", "Centre of gravity"));
  const cg = cogNow();
  const cc = el("div", "ckcard"); cc.id = "cogCard";
  if (!cg) cc.appendChild(el("div", "ckline", "No part masses in this config — add part mass {g, com} or print.grams"));
  else {
    const k = el("div", "kpis");
    const t = (lab, v, u, cls) => { const d = el("div", "kpi" + (cls ? " " + cls : "")); d.appendChild(el("div", "k", lab));
      const vv = el("div", "v", v); if (u){ const sm = document.createElement("small"); sm.textContent = " " + u; vv.appendChild(sm); }
      d.appendChild(vv); return d; };
    k.appendChild(t("Mass", cg.g.toFixed(0), "g"));
    k.appendChild(t("CoG height", cg.h.toFixed(1), "mm"));
    k.appendChild(t("Inside footprint", cg.margin == null ? "—" : cg.margin.toFixed(1), "mm", cg.margin != null && cg.margin < 0 ? "bad" : ""));
    k.appendChild(t("Tips at", cg.tipDeg == null ? "—" : cg.tipDeg.toFixed(1), "° tilt", cg.tipDeg != null && cg.tipDeg < 10 ? "bad" : "accent"));
    cc.appendChild(k);
    if (cg.missing) cc.appendChild(el("div", "ckline", cg.missing + " parts carry no mass and are left out"));
    const b = el("button", "btn", cogOn ? "Hide CoG" : "Show CoG in 3D"); b.id = "bCog";
    b.setAttribute("aria-pressed", String(cogOn));
    b.addEventListener("click", () => { cogOn = !cogOn; cogKey = ""; b.textContent = cogOn ? "Hide CoG" : "Show CoG in 3D";
      b.setAttribute("aria-pressed", String(cogOn)); draw(); });
    cc.appendChild(b);
  }
  shBody.appendChild(cc);
  /* ---- clash scan ---- */
  shBody.appendChild(el("div", "sect", "Clash scan · this pose"));
  const cl = el("div", "ckcard"); cl.id = "clashCard";
  const run = el("button", "btn pri", CLASH ? "Re-scan" : "Scan for clashes"); run.id = "bClash";
  const out = el("div"); out.id = "clashOut";
  run.addEventListener("click", async () => {
    run.disabled = true; run.textContent = "scanning…";
    await clashScan((i, n) => { run.textContent = "scanning " + i + " / " + n; });
    run.disabled = false; run.textContent = "Re-scan"; paintClash(out); buzz(12);
  });
  cl.append(run, out); shBody.appendChild(cl);
  if (CLASH) paintClash(out);
  /* ---- Ø tool ---- */
  shBody.appendChild(el("div", "sect", "Hole Ø"));
  const dc = el("div", "ckcard");
  const db = el("button", "btn", diaOn ? "Ø on — tap 3 rim points" : "Measure a hole Ø"); db.id = "bDiaSheet";
  db.addEventListener("click", () => { setDia(!diaOn); db.textContent = diaOn ? "Ø on — tap 3 rim points" : "Measure a hole Ø";
    if (diaOn && !wide()) closeSheet(); });
  dc.appendChild(db);
  if (V7.dia) dc.appendChild(el("div", "ckline", "last: Ø " + V7.dia.d.toFixed(2) + " mm"));
  shBody.appendChild(dc);
}
function paintClash(out){
  out.textContent = "";
  const n = k => CLASH.pairs.filter(c => c.kind === k).length;
  const k = el("div", "kpis"); k.style.gridTemplateColumns = "repeat(3,1fr)";
  const t = (lab, v, cls) => { const d = el("div", "kpi" + (cls ? " " + cls : "")); d.appendChild(el("div", "k", lab));
    d.appendChild(el("div", "v", String(v))); return d; };
  k.appendChild(t("Clash", n("clash"), n("clash") ? "bad" : "accent"));
  k.appendChild(t("By design", n("design")));
  k.appendChild(t("Contact", n("contact")));
  out.appendChild(k);
  out.appendChild(el("div", "ckline", `${CLASH.parts} parts · ${CLASH.candidates} close pairs walked · ${CLASH.ms} ms`));
  for (const c of CLASH.pairs){
    const a = byId.get(c.a), b = byId.get(c.b);
    const r = el("div", "ckrow " + c.kind); r.tabIndex = 0; r.setAttribute("role", "button");
    r.appendChild(el("span", "ckg", c.kind === "clash" ? "✗" : c.kind === "design" ? "◇" : "·"));
    r.appendChild(el("span", "ckp", (a ? a.label : c.a) + "  ×  " + (b ? b.label : c.b)));
    r.appendChild(el("span", "ckd", c.kind === "clash" ? "≤ " + c.depth + " mm" : c.kind === "design" ? c.why : "touch"));
    const go = () => showClashPair(c);
    r.addEventListener("click", go);
    r.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " "){ e.preventDefault(); go(); } });
    out.appendChild(r);
  }
}
/* leaving a clash view clears its red tint */
$("bShowAll").addEventListener("click", () => { moTint.clear(); V7.clashAt = null; draw(); });
$("bReset").addEventListener("click", () => { if (!motionMode) moTint.clear(); V7.clashAt = null; if (diaOn) setDia(false); });

/* ---------- verifier hooks ---------- */
Object.assign(window.__avV7, {
  clash: async () => { const r = await clashScan(); return {pairs: r.pairs.map(c => ({a: c.a, b: c.b, kind: c.kind, why: c.why, depth: c.depth, tris: c.tris})),
                                                         candidates: r.candidates, ms: r.ms}; },
  clashBrute: () => {                 // independent: the v5 brute-force sweep on every box-overlapping pair
    const sol = parts.filter(p => state(p) === "solid" && p.kind !== "wire"), out = [];
    for (let i = 0; i < sol.length; i++) for (let k = i+1; k < sol.length; k++){
      const pa = sol[i], pb = sol[k], A = modelOf(pa), B = modelOf(pb);
      if (!boxHit(wbox(pa, A), wbox(pb, B), 0.01)) continue;
      if (bruteHit(floatsOf(pa), floatsOf(pb), MC.mul4(MC.inv4(A), B))) out.push(pk(pa.id, pb.id));
    }
    return out.sort();
  },
  cog: () => { const c = cogNow(); return c && {g: c.g, com: c.com, margin: c.margin, h: c.h, tipDeg: c.tipDeg, hull: c.hull.length, missing: c.missing}; },
  circle3: (a, b, c) => circle3(a, b, c),
  dia: () => V7.dia || null,
  setDia,
});
