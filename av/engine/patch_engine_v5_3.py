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

# ---------------- R9: CHECKS lane (design gates as tiles) ----------------
s = patch(s, '<button id="dPlate" aria-pressed="false"><span class="ic">▤</span>Plate</button>',
          '<button id="dPlate" aria-pressed="false"><span class="ic">▤</span>Plate</button>\n'
          '    <button id="dCheck" aria-pressed="false"><span class="ic">✓</span>Checks</button>', "dock button")
s = patch(s, 'for (const id of ["dParts","dBuild","dMotion","dBom","dWire","dPlate"])\n    $(id).setAttribute("aria-pressed","false");\n  viewShiftY = 0;',
          'for (const id of ["dParts","dBuild","dMotion","dBom","dWire","dPlate","dCheck"])\n    $(id).setAttribute("aria-pressed","false");\n  viewShiftY = 0;', "closeSheet list")
s = patch(s, 'function setDock(tab){\n  for (const id of ["dParts","dBuild","dMotion","dBom","dWire","dPlate"])',
          'function setDock(tab){\n  for (const id of ["dParts","dBuild","dMotion","dBom","dWire","dPlate","dCheck"])', "setDock list")
s = patch(s, 'wire:"dWire",plate:"dPlate",motion:"dMotion"}[tab])', 'wire:"dWire",plate:"dPlate",motion:"dMotion",check:"dCheck"}[tab])', "setDock map")
s = patch(s, '["build","dBuild"],["bom","dBom"],["plate","dPlate"]]){', '["build","dBuild"],["bom","dBom"],["plate","dPlate"],["check","dCheck"]]){', "openSheet list")
s = patch(s, 'wire:showWire, plate:showPlate, motion:showMotion}[tab] || showParts)();',
          'wire:showWire, plate:showPlate, motion:showMotion, check:showChecks}[tab] || showParts)();', "goTab map")
s = patch(s, '["dBom","bom"],["dWire","wire"],["dPlate","plate"]]){', '["dBom","bom"],["dWire","wire"],["dPlate","plate"],["dCheck","check"]]){', "tab registration")
s = patch(s, 'if (!MO){ $("dMotion").style.display="none"; }',
          'if (!MO){ $("dMotion").style.display="none"; }\nif (!(META.checks||[]).length){ $("dCheck").style.display="none"; }', "hide checks")
s = patch(s, "function showPlate(){", r"""/* RATCHET R9 (v5.3, FarmHand): CHECKS lane. Every gate the project's scripts computed, as one
   screen of tiles: status first (colour + glyph, never colour alone), the number against its limit
   as a meter, and the script that proves it. META.checks = [{group,label,value,limit,unit,
   status:"pass"|"warn"|"fail",lower_is_better,source,note}]. */
function showChecks(){
  const C = META.checks || [];
  shTitle.textContent = "Checks · " + C.length + " gates";
  shBody.textContent = "";
  const n = s => C.filter(c => c.status === s).length;
  const k = el("div","kpis"); k.style.gridTemplateColumns = "repeat(3,1fr)";
  const tile = (lab, v, cls) => { const t = el("div","kpi"+(cls?" "+cls:"")); t.appendChild(el("div","k",lab));
    t.appendChild(el("div","v",String(v))); return t; };
  k.appendChild(tile("Pass", n("pass"), n("pass")===C.length ? "accent" : ""));
  k.appendChild(tile("Warn", n("warn"), ""));
  k.appendChild(tile("Fail", n("fail"), n("fail") ? "bad" : ""));
  shBody.appendChild(k);
  const groups = [...new Set(C.map(c => c.group || "Checks"))];
  for (const g of groups){
    shBody.appendChild(el("div","grp",g));
    const box = el("div","lbars");
    for (const c of C.filter(c => (c.group||"Checks") === g)){
      const st = c.status || "pass";
      const r = el("div","lbar" + (st==="fail" ? " bad" : st==="warn" ? " warn" : ""));
      const glyph = st==="fail" ? "✗ " : st==="warn" ? "! " : "✓ ";
      r.appendChild(el("div","lbl", glyph + c.label));
      const num = typeof c.value === "number";
      r.appendChild(el("div","lval", num ? (c.value.toFixed(Math.abs(c.value) < 10 ? 2 : 0) + (c.unit ? " " + c.unit : "")
                                            + (c.limit != null ? "  / " + c.limit + (c.unit ? " " + c.unit : "") : "")) : String(c.value)));
      if (num && c.limit){
        const tr = el("div","ltrack"), f = el("div","lfill");
        f.style.width = Math.max(1, Math.min(100, 100 * c.value / c.limit)) + "%";
        tr.appendChild(f);
        const lt = el("div","lt m"); lt.style.left = "calc(100% - 1px)"; tr.appendChild(lt);
        r.appendChild(tr);
      }
      box.appendChild(r);
      if (c.source || c.note){
        const s2 = el("div","formula", (c.note ? c.note + " · " : "") + (c.source || ""));
        s2.style.padding = "0 0 6px"; box.appendChild(s2);
      }
    }
    shBody.appendChild(box);
  }
}
function showPlate(){""", "showChecks")

s = s.replace("<!-- OneShot Arm v5.2 · SP assembly-viewer engine v2 + Motion · ratchets R1–R7 -->",
              "<!-- OneShot Arm v5.2 · SP assembly-viewer engine v5.3 + Motion · ratchets R1–R9 -->", 1)
open(OUT, "w").write(s)
print("wrote", OUT)
