"""SP AV engine — ratchet for OneShot v4 (applied to the Motion-lane engine
extracted from the published OneShot v3 build).

R1 PHYSICS   gear efficiency: a coupling may carry `eta`; the Load tab's
             virtual-work servo torque is divided by it (a spur stage makes the
             motor work 1/η harder than the ideal ratio says).
R2 UI / BOM  HAVE / BUY: every cost may carry `have` (from the SP parts
             inventory). The BOM drawer shows "To buy now / Already own /
             Filament" tiles, a Buy·Have·Print filter, and a status chip on
             every row; the printed build sheet carries the same status.
R3 UI        steppers say "motor N°", not "servo N°".
R4 UI        schematic channel router: one vertical track per edge, crossings
             minimised, same-column runs loop on the right edge, labels on the
             arriving pin.
R5 PHYSICS   loop closure stays on its branch: passive angles wrap into range,
             big jumps are walked in <= 4° continuation steps from a consistent
             state, path frames seed from the previous frame.
R6 PHYSICS   grip test follows couplings: a pinion driving two racks counts both
             jaws as its jaw parts (parallel grippers).
Every patch asserts its anchor exists exactly once, so a changed engine fails
loudly instead of silently shipping half a ratchet.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
src = (HERE / "viewer_template_motion.html").read_text(encoding="utf-8")


def sub(s, old, new, count=1):
    n = s.count(old)
    assert n == count, f"anchor found {n}× (want {count}): {old[:80]!r}"
    return s.replace(old, new)


s = src
# ---------------- R1 gear efficiency --------------------------------------------
s = sub(s, """function loads(st){
  if (LOOPS.length && PASSIVE.length) return loadsVW(st);""",
"""/* RATCHET v4 (OneShot v4, physics): gear trains lose energy. Virtual work
   gives the IDEAL input torque; through a stage at efficiency η the motor has
   to supply 1/η of it to lift, and lifting is the case a holding servo must
   cover. A coupling declares its own `eta`; none = an ideal link (η 1). */
function gearEta(jid){
  let e = 1;
  for (const c of MJ) if (c.couple && c.couple.joint === jid && c.couple.eta) e = Math.min(e, c.couple.eta);
  return e;
}
function loads(st){
  if (LOOPS.length && PASSIVE.length) return loadsVW(st);""")
s = sub(s, """    const kgcm = (nmm + spr) / 98.0665;
    const stall = j.servo.stall_kgcm || 1.8;""",
"""    const kgcm = (nmm + spr) / 98.0665 / gearEta(j.id);
    const stall = j.servo.stall_kgcm || 1.8;""")
s = sub(s, """    const kgcm = nmm / 98.0665;
    const stall = j.servo.stall_kgcm || 1.8;
    const frac = Math.abs(kgcm) / stall;
    out.push({id:j.id, label:j.label, kgcm, stall, frac, grams:gsum, springNmm:0, method:"vw", closed,""",
"""    const eta = gearEta(j.id);
    const kgcm = nmm / 98.0665 / eta;
    const stall = j.servo.stall_kgcm || 1.8;
    const frac = Math.abs(kgcm) / stall;
    out.push({id:j.id, label:j.label, kgcm, stall, frac, grams:gsum, springNmm:0, method:"vw", closed, eta,""")
s = sub(s, """Parts riding a parallelogram are felt at the pivot they hang from, not at their own distance — that is why the numbers are small. kg·cm because""",
"""Parts riding a parallelogram are felt at the pivot they hang from, not at their own distance — that is why the numbers are small. A geared servo is nudged through its gear, so its bar already includes the ratio; it is then divided by the stage's efficiency η (0.9 for one printed spur stage) because the servo must overcome the tooth friction too. kg·cm because""")

# ---------------- R2 HAVE / BUY ------------------------------------------------------
s = sub(s, """function bomRows(){
  const rows=[];
  for (const p of parts){
    if (p.bom===false) continue;
    rows.push({id:p.id, label:p.label, colour:p.color, qty:p.qty||1,
               kind:p.kind, cost:p.cost||null});
  }
  for (const b of (META.bomExtra||[]))
    rows.push({id:null, label:b.label, colour:b.color||"#7f8f87", qty:b.qty||1,
               kind:b.kind||"bought", cost:b.cost||null});
  return rows;
}""",
"""/* RATCHET v4 (OneShot v4, BOM): HAVE / BUY from the SP parts inventory.
   cost.have = true -> already on the shelf (the cost is still shown so the
   ×10/×50/×100 product numbers stay real); false -> must be bought for unit #1. */
let bomFilter = "all";
const bomStatus = r => r.kind === "printed" ? "print" : (r.have ? "have" : (r.have === false ? "buy" : null));
function bomRows(){
  const rows=[];
  for (const p of parts){
    if (p.bom===false) continue;
    rows.push({id:p.id, label:p.label, colour:p.color, qty:p.qty||1,
               kind:p.kind, cost:p.cost||null,
               have: p.cost && p.cost.have != null ? !!p.cost.have : null,
               haveNote: (p.cost && p.cost.have_note) || ""});
  }
  for (const b of (META.bomExtra||[]))
    rows.push({id:null, label:b.label, colour:b.color||"#7f8f87", qty:b.qty||1,
               kind:b.kind||"bought", cost:b.cost||null,
               have: b.cost && b.cost.have != null ? !!b.cost.have : null,
               haveNote: (b.cost && b.cost.have_note) || ""});
  return rows;
}""")
s = sub(s, """  shBody.appendChild(k);
  if (tbd.length) shBody.appendChild(flagEl("warn","⚠",
    tbd.length+" line"+(tbd.length>1?"s":"")+" unsourced (TBD) — not counted in any total above."));""",
"""  shBody.appendChild(k);
  if (rows.some(r => r.have != null)){
    const sum = a => a.reduce((x,r)=>x + r.cost.each*r.qty, 0);
    const buy = known.filter(r => bomStatus(r) === "buy"), own = known.filter(r => bomStatus(r) === "have"),
          prt = known.filter(r => bomStatus(r) === "print");
    const k2 = el("div","kpis");
    k2.appendChild(tile("To buy now", CUR+sum(buy).toFixed(2), buy.length+" lines", true));
    k2.appendChild(tile("Already own", CUR+sum(own).toFixed(2), own.length+" lines"));
    k2.appendChild(tile("Filament + time", CUR+sum(prt).toFixed(2), prt.length+" printed"));
    shBody.appendChild(k2);
    const fh = el("div","plate-h");
    fh.appendChild(el("span","phl","Show:"));
    for (const [v,lab] of [["all","All"],["buy","Buy"],["have","Have"],["print","Print"]]){
      const b = el("button","pchip", lab);
      b.setAttribute("aria-pressed", String(bomFilter===v));
      b.addEventListener("click", ()=>{ bomFilter=v; showBom(); });
      fh.appendChild(b);
    }
    shBody.appendChild(fh);
  }
  if (tbd.length) shBody.appendChild(flagEl("warn","⚠",
    tbd.length+" line"+(tbd.length>1?"s":"")+" unsourced (TBD) — not counted in any total above."));""")
s = sub(s, """  let running = 0;
  for (const r of rows){
    const tr=document.createElement("tr");
    if (r.id) tr.dataset.id=r.id;""",
"""  let running = 0;
  for (const r of rows.filter(r => bomFilter === "all" || bomStatus(r) === bomFilter)){
    const tr=document.createElement("tr");
    if (r.id) tr.dataset.id=r.id;""")
s = sub(s, """    w.appendChild(el("span",null,r.label)); nm.appendChild(w);
    td("n").textContent = r.qty;""",
"""    w.appendChild(el("span",null,r.label));
    const stt = bomStatus(r);
    if (stt){ const c = el("span","stc "+stt, stt.toUpperCase()); if (r.haveNote) c.title = r.haveNote; w.appendChild(c); }
    nm.appendChild(w);
    if (stt === "have" && r.haveNote) nm.appendChild(el("div","stn", "on hand · " + r.haveNote));
    td("n").textContent = r.qty;""")
s = sub(s, """  for (const r of rows){
    const tr = document.createElement("tr");
    const td=(cls,txt)=>{ const x=H("td",cls,txt); tr.appendChild(x); return x; };
    td(null, r.label); td("n", String(r.qty));""",
"""  for (const r of rows){
    const tr = document.createElement("tr");
    const td=(cls,txt)=>{ const x=H("td",cls,txt); tr.appendChild(x); return x; };
    const stt = bomStatus(r);
    td(null, r.label + (stt ? "  [" + stt.toUpperCase() + "]" : "")); td("n", String(r.qty));""")
# CSS for the chips (append to the last style block before </style> of the BOM block)
s = sub(s, ".row .eyeb[aria-pressed=\"true\"]{background:var(--bad);color:var(--panel)",
        ".stc{font-family:var(--f-mono);font-size:9.5px;letter-spacing:.08em;padding:1px 6px;border-radius:9px;"
        "margin-left:6px;border:1px solid var(--line);white-space:nowrap;flex:0 0 auto}"
        ".stc.have{color:var(--good);border-color:var(--good)}"
        ".stc.buy{color:var(--warn);border-color:var(--warn);font-weight:700}"
        ".stc.print{color:var(--mut)}"
        ".stn{font-size:10.5px;color:var(--mut);margin:1px 0 0 19px;font-family:var(--f-mono)}\n"
        ".row .eyeb[aria-pressed=\"true\"]{background:var(--bad);color:var(--panel)")

# ---------------- R3 stepper wording ----------------------------------------------------
s = sub(s, """const fmtJ = (j, v) => j.units === "mm" ? v.toFixed(1)+" mm" : v.toFixed(1)+"°";""",
"""const fmtJ = (j, v) => j.units === "mm" ? v.toFixed(1)+" mm" : v.toFixed(1)+"°";
const actW = j => (j.servo && j.servo.kind === "stepper") ? "motor" : "servo";      // RATCHET v4""")
s = sub(s, '${j.servo ? " · servo "+servoDeg(j, MS.q[j.id]).toFixed(0)+"°" : ""}',
        '${j.servo ? " · "+actW(j)+" "+servoDeg(j, MS.q[j.id]).toFixed(0)+"°" : ""}')
s = sub(s, 'if (sv) sv.textContent = j.servo ? "servo " + servoDeg(j, v).toFixed(0) + "°" : (j.couple ? "coupled" : "");',
        'if (sv) sv.textContent = j.servo ? actW(j) + " " + servoDeg(j, v).toFixed(0) + "°" : (j.couple ? "coupled" : "");')
s = sub(s, '(j.servo ? "  ·  servo " + servoDeg(j, MS.q[j.id]).toFixed(0) + "°" : "");',
        '(j.servo ? "  ·  " + actW(j) + " " + servoDeg(j, MS.q[j.id]).toFixed(0) + "°" : "");')

# ---------------- R4 schematic channel router ------------------------------------------
# v3 put every run between two columns on ONE x, so parallel verticals merged into
# a single line; a same-column run cut through its own box. Replace the router.
a = s.index("function buildSchematic(){")
b = s.index("/* ===========================================================================\n   PANEL 5 — PRINT ORIENTATION / PLATES")
assert s.count("function buildSchematic(){") == 1 and a < b
s = s[:a] + r"""/* RATCHET v4 (OneShot v4, schematic): every edge owns its own vertical
   track. v3 drew every run between the same two columns on ONE x, so parallel
   verticals merged into one line and you could not tell which pin went where.
   Each gap between columns is now a routing channel: edges are ordered to
   minimise crossings (greedy insertion + swap passes on an exact crossing
   count), the gap widens to fit its tracks, a same-column run leaves and
   returns on its column's right edge (it used to cut through its own box),
   and the direct label sits on the arriving pin so labels never stack. */
function buildSchematic(){
  const PW=150, RH=17, HEAD=24, GAPMIN=76, GAPY=26, PAD=14, TRK=11, EDGE=18;
  const cols=new Map(), rows=new Map();
  for (const n of NODES){
    const [c,r]=n.schem||[0,0];
    cols.set(c,true); rows.set(r,(Math.max(rows.get(r)||0,
      HEAD + (n.pins||[]).length*RH + 8)));
  }
  const colKeys=[...cols.keys()].sort((a,b)=>a-b);
  const rowKeys=[...rows.keys()].sort((a,b)=>a-b);
  const ci=new Map(colKeys.map((c,i)=>[c,i]));
  const rowY={};
  let y=PAD;
  rowKeys.forEach(r=>{ rowY[r]=y; y += rows.get(r)+GAPY; });
  const H = y - GAPY + PAD;
  const box=new Map();
  for (const n of NODES){
    const [c,r]=n.schem||[0,0];
    const h=HEAD+(n.pins||[]).length*RH+8;
    box.set(n.id,{ci:ci.get(c), x:0, y:rowY[r] + (rows.get(r)-h)/2, w:PW, h, n});
  }
  const pinY=(b,pid)=>{ const i=Math.max(0,(b.n.pins||[]).findIndex(p=>p.id===pid));
                        return b.y+HEAD+i*RH+RH/2; };
  // 1. every run is an edge in the channel right of its left-hand column
  const E=[];
  for (const r of RUNS){
    const [an,ap]=endRef(r.from), [bn,bp]=endRef(r.to);
    let A=box.get(an), B=box.get(bn), pa=ap, pb=bp;
    if (!A||!B) continue;
    if (A.ci>B.ci || (A.ci===B.ci && A.y>B.y)){ [A,B]=[B,A]; [pa,pb]=[pb,pa]; }
    const ya=pinY(A,pa), yb=pinY(B,pb), same=A.ci===B.ci;
    E.push({r, A, B, ya, yb, same, g:A.ci,
            L: same ? [ya,yb] : [ya],          // horizontals reaching in from the left column
            R: same ? [] : [yb],               // horizontals leaving for the right column
            lo:Math.min(ya,yb), hi:Math.max(ya,yb)});
  }
  // 2. order each channel's tracks by an exact crossing count
  const inside=(y,e)=> y>e.lo+0.5 && y<e.hi-0.5;
  const cx=(e,f)=>{ let n=0;                   // e on a track left of f
    for (const yy of f.L) if (inside(yy,e)) n++;
    for (const yy of e.R) if (inside(yy,f)) n++;
    return n; };
  const cost=o=>{ let n=0; for (let i=0;i<o.length;i++) for (let j=i+1;j<o.length;j++) n+=cx(o[i],o[j]); return n; };
  const chans=new Map();
  for (const e of E){ if (!chans.has(e.g)) chans.set(e.g,[]); chans.get(e.g).push(e); }
  let crossings=0;
  for (const [g,list] of chans){
    let o=[];
    for (const e of [...list].sort((a,b)=>(b.same-a.same)||(a.lo-b.lo))){
      let best=0, bc=Infinity;
      for (let k=0;k<=o.length;k++){ const c=cost([...o.slice(0,k),e,...o.slice(k)]); if (c<bc){bc=c;best=k;} }
      o.splice(best,0,e);
    }
    for (let pass=0, moved=true; moved && pass<12; pass++){ moved=false;
      for (let k=0;k+1<o.length;k++){ const t=[...o]; [t[k],t[k+1]]=[t[k+1],t[k]];
        if (cost(t)<cost(o)){ o=t; moved=true; } } }
    o.forEach((e,k)=>{ e.k=k; e.n=o.length; });
    chans.set(g,o); crossings+=cost(o);
  }
  // 3. size each gap to its tracks, then place the columns
  const gapW=i=>{ const n=(chans.get(i)||[]).length; return Math.max(GAPMIN, 2*EDGE+Math.max(0,n-1)*TRK); };
  const colX=[]; let x=PAD;
  colKeys.forEach((c,i)=>{ colX[i]=x; x += PW + gapW(i); });
  const last=colKeys.length-1;
  const W = colX[last] + PW + ((chans.get(last)||[]).length ? gapW(last) : 0) + PAD;
  for (const [,b] of box) b.x=colX[b.ci];
  const trackX=e=>{ const left=colX[e.g]+PW, gw=gapW(e.g);
                    return left + (gw-(e.n-1)*TRK)/2 + e.k*TRK; };

  const svg=mk("svg",{width:W,height:H,viewBox:`0 0 ${W} ${H}`,
                      role:"img","aria-label":"Wiring pinout"});
  svg.dataset.crossings=String(crossings);
  const gEdge=mk("g",{}), gNode=mk("g",{}), gLbl=mk("g",{});
  const usedLbl=new Set();
  for (const e of E){
    const r=e.r, xt=trackX(e), xa=e.A.x+e.A.w;
    const xb = e.same ? xa : e.B.x;
    const d=`M ${xa} ${e.ya} H ${xt} V ${e.yb} H ${xb}`;
    const col="var(--wire-"+r.kind+")";
    const hit=mk("path",{class:"ehit",d}); hit.dataset.run=r.id; hit.dataset.kind=r.kind;
    const pth=mk("path",{class:"edge",d,stroke:col});
    pth.dataset.run=r.id; pth.dataset.kind=r.kind;
    hit.addEventListener("click",ev=>toggleWire(r.id,ev.shiftKey||ev.metaKey));
    gEdge.appendChild(pth); gEdge.appendChild(hit);
    // DIRECT LABEL on the arriving pin's stub — the CVD-safe second encoding
    let lx = e.same ? xa+5 : xb-5, ly = e.yb-3, anchor = e.same ? "start" : "end";
    const key = Math.round(lx)+":"+Math.round(ly);
    if (usedLbl.has(key)){ lx = xt+4; ly=(e.ya+e.yb)/2-3; anchor="start"; }
    usedLbl.add(key);
    const t=mk("text",{class:"elbl",x:lx,y:ly,"text-anchor":anchor});
    t.dataset.run=r.id; t.dataset.kind=r.kind;
    t.textContent = r.net || r.label;
    gLbl.appendChild(t);
  }
  for (const [,b] of box){
    const n=b.n;
    const g=mk("g",{});
    g.appendChild(mk("rect",{class:"nbox",x:b.x,y:b.y,width:b.w,height:b.h,rx:7}));
    const nl=mk("text",{class:"nlbl",x:b.x+9,y:b.y+16}); nl.textContent=n.label;
    g.appendChild(nl);
    (n.pins||[]).forEach((pn,i)=>{
      const py=b.y+HEAD+i*RH+RH/2;
      const tx=mk("text",{class:"plbl",x:b.x+9,y:py+3.5}); tx.textContent=pn.label;
      g.appendChild(tx);
      for (const sx of [b.x, b.x+b.w])
        g.appendChild(mk("circle",{class:"pdot",cx:sx,cy:py,r:2.5,
          fill:"var(--wire-"+(pn.kind||"data")+")"}));
    });
    g.style.cursor="pointer";
    g.addEventListener("click",()=>{
      selNm.textContent=n.label; selNt.textContent=n.role||"";
      selNt.style.display=n.role?"":"none";
    });
    gNode.appendChild(g);
  }
  svg.appendChild(gEdge); svg.appendChild(gNode); svg.appendChild(gLbl);
  const wrap=el("div","schem"); wrap.appendChild(svg);
  return wrap;
}

""" + s[b:]

# ---------------- R5 loop closure that stays on its branch ----------------------------------
s = sub(s, """function makeState(qIn, pay){
  const q = {...qIn};
  applyCouple(q);
  let ok = true, res = 0;
  if (LOOPS.length && PASSIVE.length){
    const f = x => { PASSIVE.forEach((id,i)=>q[id]=x[i]); applyCouple(q); return loopRes(solveW(q)); };
    const r = MC.solveLM(f, PASSIVE.map(id=>q[id]), {tol:1e-5, okTol:0.02});
    PASSIVE.forEach((id,i)=>q[id]=r.x[i]); applyCouple(q);
    ok = r.ok; res = r.res;
  }
  for (const j of MJ)
    if (q[j.id] < j.eff[0]-1e-6 || q[j.id] > j.eff[1]+1e-6){ ok = false; }
  const W = solveW(q);""",
"""/* RATCHET v4 (OneShot v4, physics): loop closure that stays on its branch.
   An LM solve seeded far from the answer can land on the crossed
   (anti-parallelogram) branch, or on the same pose a full turn round; v3 then
   either drew a flipped linkage or rejected a reachable pose (2 of 8 random
   poses in v4's physics gate, all with residual < 1e-5). Now passive angles
   wrap into their range (-262° IS 98°), a caller that holds a consistent
   state passes it as `from` and a big jump is walked there in <= 4° steps
   (continuation keeps the branch), and a failed direct solve retries that
   walk from the live pose. Path frames carry their solved passives forward. */
const CONT_STEP = 4;
function wrapPassive(q){
  for (const id of PASSIVE){ const j = jById.get(id);
    if (j && j.units !== "mm" && j.eff[0] <= -180 && j.eff[1] >= 180)
      q[id] = ((q[id] + 180) % 360 + 360) % 360 - 180; }
}
function closeLoops(q, seed){
  const f = x => { PASSIVE.forEach((id,i)=>q[id]=x[i]); applyCouple(q); return loopRes(solveW(q)); };
  const r = MC.solveLM(f, seed, {tol:1e-5, okTol:0.02});
  PASSIVE.forEach((id,i)=>q[id]=r.x[i]); applyCouple(q);
  return r;
}
function walkLoops(q, from){
  const tgt = {...q}, drv = MJ.filter(j => j.drive !== "passive" && !j.couple);
  let span = 0;
  for (const j of drv) span = Math.max(span, Math.abs((tgt[j.id] ?? 0) - (from[j.id] ?? 0)));
  const n = Math.max(1, Math.min(90, Math.ceil(span / CONT_STEP)));
  let x = PASSIVE.map(id => from[id] ?? q[id]), r = null;
  for (let k = 1; k <= n; k++){
    for (const j of drv) if (from[j.id] != null) q[j.id] = from[j.id] + (tgt[j.id] - from[j.id]) * k / n;
    applyCouple(q);
    r = closeLoops(q, x);
    if (!r.ok) break;
    x = r.x;
  }
  return r;
}
const inEff = q => MJ.every(j => !(q[j.id] < j.eff[0]-1e-6 || q[j.id] > j.eff[1]+1e-6));
function makeState(qIn, pay, from){
  let q = {...qIn};
  applyCouple(q);
  let ok = true, res = 0;
  if (LOOPS.length && PASSIVE.length){
    let r = from ? walkLoops(q, from) : closeLoops(q, PASSIVE.map(id=>q[id]));
    wrapPassive(q);
    if (!(r.ok && inEff(q)) && !from){
      let live = null; try { live = MS; } catch(e){ live = null; }
      if (live && live.ok !== false){
        const q2 = {...qIn}; applyCouple(q2);
        const r2 = walkLoops(q2, live.q); wrapPassive(q2);
        if (r2.ok && inEff(q2)){ q = q2; r = r2; }
      }
    }
    ok = r.ok; res = r.res;
  }
  if (!inEff(q)) ok = false;
  const W = solveW(q);""")
s = sub(s, """  const at = v => { const q={...MS.q, [jid]:v}; return makeState(q, MS.pay); };""",
        """  const at = v => { const q={...MS.q, [jid]:v}; return makeState(q, MS.pay, MS.q); };""")
s = sub(s, """      // random DRIVEN joints; the passive ones start where the linkage is now, the
      // way a drag does — a random passive start can land on the crossed
      // (anti-parallelogram) branch, which is a different mechanism, not a failure
      for (let t=0;t<n;t++){ const q={...MS.q};
        for (const j of MJ) if (j.drive !== "passive") q[j.id]=j.eff[0]+(j.eff[1]-j.eff[0])*rnd();
        const st = makeState(q, null); if (st.ok){ ok++; res = Math.max(res, st.res||0); } }""",
"""      // random DRIVEN joints, walked there from the live pose the way the real
      // mechanism gets there (R5 continuation), so the branch is the real one
      for (let t=0;t<n;t++){ const q={...MS.q};
        for (const j of MJ) if (j.drive !== "passive") q[j.id]=j.eff[0]+(j.eff[1]-j.eff[0])*rnd();
        const st = makeState(q, null, MS.q); if (st.ok){ ok++; res = Math.max(res, st.res||0); } }""")
s = sub(s, """  const push = (label, grip) => {
    const st = makeState(q, pay ? {...pay} : null);
    frames.push(""",
"""  const push = (label, grip) => {
    const st = makeState(q, pay ? {...pay} : null);
    for (const id of PASSIVE) q[id] = st.q[id];        // R5: next frame seeds from this one
    frames.push(""")

s = sub(s, """  if (P && !linkOf.has(GRIP.payload) && P.att) P.rel = MC.mul4(MC.inv4(solveW(cadQ()).get(P.att)), P.rel);
  return makeState(q, P);""",
"""  if (P && !linkOf.has(GRIP.payload) && P.att) P.rel = MC.mul4(MC.inv4(solveW(cadQ()).get(P.att)), P.rel);
  return makeState(q, P, cadQ());          // R5: walk from the CAD pose, the one state known to be consistent""")
s = sub(s, """  const farSt = makeState({...MS.q, [jid]: far === MS.q[jid] ? far - 1 : far}, MS.pay);""",
        """  const farSt = makeState({...MS.q, [jid]: far === MS.q[jid] ? far - 1 : far}, MS.pay, MS.q);
  let from = MS.q;                          // R5: each sample walks on from the last""")
s = sub(s, """        const s = makeState({...MS.q, [jid]: vals[i]}, MS.pay);
        okv.push(s.ok);""",
"""        const s = makeState({...MS.q, [jid]: vals[i]}, MS.pay, from);
        if (s.ok) from = s.q;
        okv.push(s.ok);""")
s = sub(s, """    const st = makeState(q, pay ? {...pay} : null);
    for (const id of PASSIVE) q[id] = st.q[id];        // R5: next frame seeds from this one""",
"""    const st = makeState(q, pay ? {...pay} : null, frames.length ? null : cadQ());
    for (const id of PASSIVE) q[id] = st.q[id];        // R5: next frame seeds from this one""")

# ---------------- R6 multi-output gear trains (grip test, path grasp, contact name) -------
# A pinion that drives two racks (a parallel gripper) moves its jaws through
# COUPLINGS, not through the kinematic tree: subtreeOf(pinion) held only the
# pinion, so the grip test said "never touches", the path closed the jaws
# straight through the cube without grasping it, and the contact chip named the
# wrong part. One helper now gives a driver's jaw parts: its subtree plus the
# subtrees of every joint coupled to it. Used in all three places.
s = sub(s, """const subtreeOf = id => { const out=[id]; for (const k of jKids.get(id)) out.push(...subtreeOf(k)); return out; };""",
"""const subtreeOf = id => { const out=[id]; for (const k of jKids.get(id)) out.push(...subtreeOf(k)); return out; };
/* RATCHET v5 R6: parts a driver moves, through the tree AND through couplings */
const drivenParts = id => {
  const links = new Set([id, ...MJ.filter(k => k.couple && k.couple.joint === id).map(k => k.id)].flatMap(x => subtreeOf(x)));
  return COLL.filter(p => { const l = linkOf.get(p.id); return l && links.has(l); });
};""")
s = sub(s, """  const jawParts = COLL.filter(p => { const l=linkOf.get(p.id); return l && subtreeOf(j.id).includes(l); });
  const hitsJaw = s => {""", """  const jawParts = drivenParts(j.id);
  const hitsJaw = s => {""")
s = sub(s, """          const jaw = COLL.filter(p => { const l=linkOf.get(p.id); return l && subtreeOf(jid).includes(l); });""",
        """          const jaw = drivenParts(jid);""")
s = sub(s, """  const jaw = COLL.filter(p => { const l=linkOf.get(p.id); return l && subtreeOf(GRIP.joint).includes(l); });
  let best = jaw[0], bd = 1e9;""", """  const jaw = drivenParts(GRIP.joint);
  let best = jaw[0], bd = 1e9;""")

(HERE / "viewer_template_motion_v4.html").write_text(s, encoding="utf-8")
print("patched engine written:", len(s), "bytes")
