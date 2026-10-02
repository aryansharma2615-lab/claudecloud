"""SP AV engine — ratchet for OneShot v5.2 (applied to viewer_template_motion_v5.html,
the engine OneShot v5 shipped with: v3 Motion template + R1–R6).

R7a MOTION   through-moves: a path key `{through: [q1, q2, ...], param?, dur?}` is ONE
             move through its via points — one minimum-jerk time-scaling over the
             whole polyline, so the robot never stops at a via. `param: "even"`
             gives every via the same share of the path parameter (a straight-line
             executor's IK points are evenly spaced in mm); otherwise vias are
             spaced by joint travel. `dur` (s) overrides the speed-cap timing.
R7b LINT     dead stops: consecutive q-keys with the SAME label are one intended move
             cut into hops, and each hop is rest-to-rest — the arm stops dead
             between them. OneShot v5's lift was 3 hops with 2 dead stops and read
             as a servo "struggling to go up". Logged per path, shown as a
             "Mid-move stops" tile, returned by __avMotion.path(), gated by
             verify_av_v3.py. Every through-move also logs its slowest interior
             speed vs its peak (minRatio) so "smooth" is measured, not assumed.
Every patch asserts its anchor exists exactly once.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
# the v5 engine: ~/Claude/AV/viewer_template_motion_v5.html; inside the project it is the
# file av/engine/patch_engine.py writes (viewer_template_motion_v4.html — same bytes)
SRC = HERE / "viewer_template_motion_v5.html"
if not SRC.exists():
    SRC = HERE / "viewer_template_motion_v4.html"
src = SRC.read_text(encoding="utf-8")


def sub(s, old, new, count=1):
    n = s.count(old)
    assert n == count, f"anchor found {n}x (want {count}): {old[:80]!r}"
    return s.replace(old, new)


s = src
# ---------------- R7a + R7b in buildPath ----------------------------------------------
s = sub(s, """  push("start");
  const keys = P.keys || [];
  for (const k of keys){
    if (k.q){""", """  push("start");
  const keys = P.keys || [];
  /* RATCHET v5.2 R7b (motion lint): consecutive q-keys with the same label are ONE
     intended move cut into hops, and every hop is rest-to-rest — the arm stops dead
     between them (OneShot v5's lift: 3 hops, 2 stops; it read as a struggling servo). */
  const deadStops = [], throughLog = [];
  let prevKey = null;
  for (const k of keys){
    if (k.q && prevKey && prevKey.q && (prevKey.label||"") === (k.label||""))
      deadStops.push({label: k.label || "", t: +(frames.length*dt).toFixed(2)});
    prevKey = k;
    if (k.through && k.through.length){
      /* RATCHET v5.2 R7a (motion): a move THROUGH via points is one move — one
         minimum-jerk time-scaling over the whole polyline, so it never stops at a
         via. param "even": every via gets the same share of the path parameter (a
         straight-line executor's IK points are evenly spaced in mm); otherwise the
         vias are spaced by joint travel. dur overrides the speed-cap timing. */
      const ids = [...new Set(k.through.flatMap(v => Object.keys(v)))];
      const nodes = [Object.fromEntries(ids.map(id => [id, q[id]]))];
      for (const v of k.through) nodes.push({...nodes.at(-1), ...v});
      const len = (a, b) => { let m = 0; for (const id of ids) m = Math.max(m, Math.abs(b[id]-a[id])); return m; };
      const seg = [];
      let span = 0;
      for (let i=1;i<nodes.length;i++){ const m = len(nodes[i-1], nodes[i]); span += m; seg.push(k.param === "even" ? 1 : m); }
      const total = seg.reduce((a, b) => a + b, 0) || 1;
      const T = k.dur || Math.max(span/spd*1.875, dt);
      const n = Math.max(1, Math.ceil(T/dt));
      const sp = [];
      let last = ids.map(id => q[id]);
      for (let i=1;i<=n;i++){
        let x = MC.minJerk(i/n)*total, j = 0;
        while (j < seg.length-1 && x > seg[j]){ x -= seg[j]; j++; }
        const u = seg[j] > 0 ? Math.min(1, x/seg[j]) : 1;
        for (const id of ids) q[id] = nodes[j][id] + (nodes[j+1][id]-nodes[j][id])*u;
        push(k.label||"");
        const cur = ids.map(id => frames.at(-1).q[id]);
        let m = 0; for (let c=0;c<ids.length;c++) m = Math.max(m, Math.abs(cur[c]-last[c]));
        sp.push(m); last = cur;
      }
      const pk = Math.max(...sp, 1e-9), a = Math.floor(n*0.15), b = Math.ceil(n*0.85);
      let mn = 1; for (let i=a;i<b;i++) mn = Math.min(mn, sp[i]/pk);
      throughLog.push({label: k.label || "", vias: k.through.length, frames: n, dur: +(n*dt).toFixed(2), minRatio: +mn.toFixed(3)});
    }
    if (k.q){""")
s = sub(s, """      const out = {id:P.id, frames, events:merged, loads:loadS, dt};""",
        """      const out = {id:P.id, frames, events:merged, loads:loadS, dt, deadStops, through:throughLog};""")
# ---------------- R7b tile + caption ---------------------------------------------------
s = sub(s, """    k.appendChild(tile("Collisions", String(data.events.length), "", data.events.length ? "bad" : "accent"));""",
        """    k.appendChild(tile("Collisions", String(data.events.length), "", data.events.length ? "bad" : "accent"));
    const ds = data.deadStops || [];
    k.appendChild(tile("Mid-move stops", String(ds.length), ds.length ? "· " + ds[0].label : "", ds.length ? "bad" : "accent"));""")
s = sub(s, """minimum-jerk blends at ${P.speed_dps||90} °/s — the same profile the robot's executor runs.""",
        """minimum-jerk blends at ${P.speed_dps||90} °/s — the same profile the robot's executor runs; a straight-line move is ONE blend through its via points, so it never stops mid-move.""")
# ---------------- R7b in the test API ---------------------------------------------------
s = sub(s, """                             peak: Math.max(...d.loads.flat().map(l => l.frac))})),""",
        """                             peak: Math.max(...d.loads.flat().map(l => l.frac)),
                             deadStops: d.deadStops || [], through: d.through || []})),""")

(HERE / "viewer_template_motion_v5_2.html").write_text(s, encoding="utf-8")
print("patched engine written:", len(s), "bytes")
