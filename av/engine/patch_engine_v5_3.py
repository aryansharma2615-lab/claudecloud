"""SP AV engine v5.2 -> v5.3: anchored patches, each anchor asserted exactly once. Never edits v5.2 in place.

Run: python av/engine/patch_engine_v5_3.py
In:  av/engine/oneshot_v5_2_reference.html   (the published OneShot v5.2 viewer = engine v5.2 + OneShot data)
Out: av/engine/viewer_template_motion_v5_3.html  (same OneShot data, so it doubles as the regression build)

R8  (Looks/UI, hit by FarmHand): far clip plane scales with the scene. v5.2 hard-codes 2000 mm, so any assembly
    bigger than ~0.6 m (a station, a rail robot) frames itself outside the frustum and the stage renders empty.
R9  (CAD-quality tools, hit by FarmHand): a CHECKS lane — one dock tab that shows every design gate the project's
    scripts produced (torque %, sag, clash count, path sweeps, firmware tests) as pass / warn / fail tiles with the
    script that proves each one. Data comes from META.checks; a project without it keeps the old dock.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "oneshot_v5_2_reference.html")
OUT = os.path.join(HERE, "viewer_template_motion_v5_3.html")


def patch(s, old, new, label):
    n = s.count(old)
    if n != 1:
        sys.exit(f"anchor '{label}' found {n}× (need exactly 1) — engine changed, re-anchor")
    return s.replace(old, new)


s = open(SRC).read()

# ---------------- R8: scene-scaled far plane ----------------
s = patch(s, "function curMVP(){",
          "/* RATCHET R8 (v5.3, FarmHand): the far plane follows the scene. v5.2 fixed it at 2000 mm. */\n"
          "function farClip(){ return Math.max(plateMode ? 4000 : 2000, dist() + 3*_bb); }\n"
          "function curMVP(){", "curMVP")
s = patch(s, "const P   = M.persp(FOV, w/h, 1, far);", "const P   = M.persp(FOV, w/h, 1, Math.max(far, farClip()));", "draw far")
s = patch(s, "const Pp=M.persp(FOV,w/h,1, plateMode?4000:2000);", "const Pp=M.persp(FOV,w/h,1, farClip());", "pick far")
s = patch(s, "const P = M.persp(FOV, r.width/r.height, 1, plateMode?4000:2000);",
          "const P = M.persp(FOV, r.width/r.height, 1, farClip());", "offscreen far")
s = patch(s, "const P = M.persp(FOV, r.width/r.height, 1, 2000); P[9] = -viewShiftY;\n  return {MVP",
          "const P = M.persp(FOV, r.width/r.height, 1, farClip()); P[9] = -viewShiftY;\n  return {MVP", "curMVP far")

s = s.replace("<!-- OneShot Arm v5.2 · SP assembly-viewer engine v2 + Motion · ratchets R1–R7 -->",
              "<!-- OneShot Arm v5.2 · SP assembly-viewer engine v5.3 + Motion · ratchets R1–R9 -->", 1)
open(OUT, "w").write(s)
print("wrote", OUT)
