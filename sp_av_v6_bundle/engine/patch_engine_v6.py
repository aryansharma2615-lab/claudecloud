"""SP AV engine — ratchet for OneShot v6 (applied to viewer_template_motion_v5_2.html).

R8a PHYSICS  gear trains are felt by the servo. v5.2's loads() only used virtual work
             when the mechanism had closed LOOPS; otherwise it summed r × F over the
             servo's kinematic SUBTREE. A servo that drives its load through a gear
             COUPLING (a planetary: sun -> carrier -> lever) has nothing in its subtree,
             so the Load tab read ~0 kg·cm with 150 g hanging off the lever. Now any
             servo that drives a coupling is loaded by virtual work (nudge the servo,
             every coupled joint follows, τ = −dU/dθ ÷ η) — exact for any gear train,
             with or without loops. Proved on the OneShot v6 planetary bench: 0.000 ->
             the hand calc within 1 %, and physicsCheck (panel = −dU/dθ) now has cases.
R8b PHYSICS  the Load-tab formula line says WHY virtual work was used (loops and/or a
             gear train) and quotes the actual η of the stage instead of "0.9".
Every patch asserts its anchor exists exactly once.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "viewer_template_motion_v5_2.html"


def sub(s, old, new, count=1):
    n = s.count(old)
    assert n == count, f"anchor found {n}x (want {count}): {old[:80]!r}"
    return s.replace(old, new)


def patch(s):
    s = sub(s, """function loads(st){
  if (LOOPS.length && PASSIVE.length) return loadsVW(st);""", """/* RATCHET v6 R8a (physics): a servo that drives its load through a gear COUPLING
   (planetary: sun -> carrier -> lever) carries nothing in its kinematic subtree, so
   summing r × F over the subtree read ~0. Virtual work follows every coupling. */
const GEARED = MJ.some(j => j.couple && jById.get(j.couple.joint) && jById.get(j.couple.joint).servo);
const USE_VW = (LOOPS.length && PASSIVE.length) || GEARED;
function loads(st){
  if (USE_VW) return loadsVW(st);""")
    s = sub(s, """  body.appendChild(el("div","formula", (LOOPS.length && PASSIVE.length) ?
    "Gravity only, held still — by virtual work, because this mechanism has closed loops: each servo is nudged 0.05°, the loop solver re-closes every pin,""",
            """  const etaTxt = [...new Set(MJ.filter(j => j.couple && j.couple.eta).map(j => j.couple.eta))].join(" / ") || "1";
  body.appendChild(el("div","formula", USE_VW && !(LOOPS.length && PASSIVE.length) ?
    `Gravity only, held still — by virtual work, because the servo drives its load through a gear train: the servo is nudged 0.05°, every geared part follows its ratio, and the change in gravity energy per radian is the servo's torque (τ = −dU/dθ). Then ÷ η ${etaTxt} — the printed gears' efficiency, so the bar includes the ratio AND the tooth friction. kg·cm because every hobby-servo datasheet uses it.` :
    (LOOPS.length && PASSIVE.length) ?
    "Gravity only, held still — by virtual work, because this mechanism has closed loops: each servo is nudged 0.05°, the loop solver re-closes every pin,""")
    return s


if __name__ == "__main__":
    out = patch(SRC.read_text(encoding="utf-8"))
    (HERE / "viewer_template_motion_v6.html").write_text(out, encoding="utf-8")
    print("patched engine written:", len(out), "bytes")
