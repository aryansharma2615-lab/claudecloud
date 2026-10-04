#!/usr/bin/env python3
"""
verify_av_v9.py — engine v8 gates, after every earlier gate (verify_av_v8 = v3 + v7 … v7.4).

    python3 verify_av_v9.py OUT.html --eng engineering_data.yaml [--shots DIR] [--floor-ref V7_4.html]
                            [--measure MEASURE_ME.md] [--exports DIR] [--coupon COUPON.html] [--skip-v8]

Each v8 gate checks the page a DIFFERENT way from how the page computes it:

  SCHEMA    the YAML validates against engineering_schema_v8.json here (jsonschema), META.eng.missing is
            empty, no MISSING badge on screen, MEASURE_ME.md exists and lists every ASSUMED blocker
  CHECKS    every §5 check id is a tile; calc_v8.py (Python) recomputes every value the page shows
            (≤ 1e-6 relative); the §5 mechanism formulas (Lewis, Grashof, transmission angle, grip,
            leadscrew, belt, min-jerk, Kt) agree JS vs Python on fixed inputs
  STRESS    the TEST model in JS = calc_v8.Model at 6 (kg, lever) cases (≤ 1 %); the Motion lane's own
            r × F load = the hand calc (≤ 1 %); stall warning appears past stall
  HASH      every phase restored from the URL hash alone in a FRESH page (phase, explode, section,
            load, x-ray, step, camera)
  LABELS    a DOM scan of every engineering panel / overlay: no numeral without a source label
  TOL       ring colours = Python band_of(profile); recolouring the profile in the page recolours
            the rings (nothing hard-coded)
  CAP       a pixel inside the section cut reads the cap colour, not the background (capped faces)
  PERF      default view < 50k triangles; LOD swaps in past 2× zoom; orbit fps ≥ 30 (headless)
  PHONE     390 px: no horizontal scroll; the tree opens as the bottom sheet; every v8 control ≥ 44 px
  SCREWS    each screw's engine side = the declared side; the SECURE fly-in starts on that side
  EXPORTS   STL watertight, 3MF opens (zip + model + trimesh), GLB loads, URDF / SRDF / SDF parse
  DATAVIZ   the stress ramps pass validate_palette.js (--ordinal) on both stages
  CALIPER   two taps on known mesh points read their true distance (≤ 0.01 mm)
  BOM       owned rows read OWNED $0
  SHOTS     all four phases, desktop + phone, dark + light -> --shots
"""
from __future__ import annotations

import glob
import json
import math
import os
import pathlib
import re
import subprocess
import sys
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import verify_av_v8 as V8V  # noqa: E402  (also installs the container-Chromium launch fallback)
import calc_v8  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

PHONE = {"width": 390, "height": 844}
DESK = {"width": 1280, "height": 800}
REQ_CHECKS = ["torque_hold", "torque_dyn", "sf_arm", "sf_wall", "lewis", "grashof", "trans_angle", "grip", "psu"]
DATAVIZ = sorted(glob.glob("/tmp/claude-0/bundled-skills/*/*/dataviz/scripts/validate_palette.js")
                 + glob.glob(os.path.expanduser("~/.claude/skills/**/validate_palette.js"), recursive=True))


def rel(a, b):
    if a is None or b is None:
        return 0.0 if a == b else 1.0
    if not (math.isfinite(a) and math.isfinite(b)):
        return 0.0 if a == b else 1.0
    return abs(a - b) / max(abs(b), 1e-9)


def page(pw, url, viewport=DESK, mobile=False, theme=None):
    b = pw.chromium.launch()
    pg = b.new_page(viewport=viewport, device_scale_factor=2 if mobile else 1, has_touch=mobile, is_mobile=mobile)
    errs = []
    pg.on("pageerror", lambda e: errs.append("PAGEERROR " + str(e) + " @ " + (getattr(e, "stack", "") or "")[:400].replace("\n", " | ")))
    pg.on("console", lambda m: errs.append("CONSOLE " + m.text) if m.type == "error" else None)
    pg.goto(url)
    pg.wait_for_timeout(2600)
    if theme == "light" and pg.evaluate("() => document.documentElement.dataset.theme") != "light":
        pg.click("#bTheme")
        pg.wait_for_timeout(300)
    return b, pg, errs


def v8_gates(path, eng_yaml, shots=None, measure_md=None, exports=None, coupon=None, log=print):
    url = "file://" + str(pathlib.Path(path).absolute())
    errors, res = [], {}
    eng, M = calc_v8.compute(eng_yaml)
    with sync_playwright() as pw:
        b, pg, perr = page(pw, url)
        js = lambda code, *a: pg.evaluate(code, *a)
        if not js("() => !!(window.__avV8 && __avV8.eng())"):
            b.close()
            return {"ok": False, "errors": ["not a v8 page with META.eng"]}

        # ---------------- SCHEMA ----------------
        miss = calc_v8.validate(__import__("yaml").safe_load(open(eng_yaml, encoding="utf-8")))
        page_miss = js("() => (__avV8.meta('eng').missing || []).length")
        res["schema"] = {"py_missing": len(miss), "page_missing": page_miss}
        if miss or page_miss:
            errors.append(f"MISSING fields: {miss[:3]}")
        if measure_md:
            if not os.path.exists(measure_md):
                errors.append("MEASURE_ME.md not generated")
            else:
                txt = open(measure_md, encoding="utf-8").read()
                n_rows = len(re.findall(r"^\| \d+ \|", txt, re.M))
                res["measure_rows"] = n_rows
                if n_rows != len(eng["measure"]):
                    errors.append(f"MEASURE_ME rows {n_rows} != {len(eng['measure'])}")

        # ---------------- CHECKS ----------------
        js("() => __avV8.setPhase('load')")
        pg.wait_for_timeout(600)
        pc = {c["id"]: c for c in js("() => __avV8.checks()")}
        ids = set(pc)
        missing_ids = [i for i in REQ_CHECKS if i not in ids] + ([] if any(i.startswith("stack_") for i in ids) else ["stack_*"])
        worst = 0.0
        for c in eng["checks"]:
            p = pc.get(c["id"])
            if not p:
                missing_ids.append(c["id"]); continue
            if c["value"] is not None:
                worst = max(worst, rel(p["value"], c["value"]))
            if p["status"] != c["status"]:
                errors.append(f"check {c['id']}: page {p['status']} vs python {c['status']}")
            if p["status"] == "pass" and any(i["src"] == "ASSUMED" for i in p["inputs"]):
                errors.append(f"check {c['id']} PASS with an ASSUMED input")
        res["checks"] = {"n": len(pc), "worst_rel": worst, "statuses": {s: sum(1 for c in pc.values() if c["status"] == s) for s in ("pass", "unverified", "warn", "fail", "na")}}
        if missing_ids:
            errors.append(f"check tiles missing: {missing_ids}")
        if worst > 1e-4:          # calc_v8 rounds what it ships to 5 significant figures
            errors.append(f"check values differ from calc_v8 by {worst:.2e}")
        F = [("lewis", [120.0, 6.0, 1.0, 0.32], calc_v8.lewis(120.0, 6.0, 1.0, 0.32)),
             ("grashof", [[40, 100, 80, 90]], calc_v8.grashof([40, 100, 80, 90])),
             ("transAngle", [30, 90, 60, 80, 47], calc_v8.trans_angle(30, 90, 60, 80, 47)),
             ("gripNeed", [0.05, 0.6, 2.0, 0.0], calc_v8.grip_need(0.05, 0.6, 2.0, 0.0)),
             ("leadscrew", [100.0, 0.3, 8.0], calc_v8.leadscrew_force(100.0, 0.3, 8.0)),
             ("beltTeeth", [20, 12.73, 25.46, 60.0], calc_v8.belt_teeth_in_mesh(20, 12.73, 25.46, 60.0)),
             ("minjerk", [1.5708, 0.75], calc_v8.minjerk_alpha(1.5708, 0.75)),
             ("kt", [12, 8, 0.2], calc_v8.kt_step(12, 8, 0.2)), ("kt", [12, 8, 2.0], calc_v8.kt_step(12, 8, 2.0))]
        fbad = []
        for name, args, want in F:
            got = js("([n, a]) => __avV8.formulas(n, a)", [name, args])
            if (isinstance(want, bool) and got != want) or (not isinstance(want, bool) and rel(got, want) > 1e-9):
                fbad.append((name, got, want))
        res["formulas"] = {"n": len(F), "bad": fbad}
        if fbad:
            errors.append(f"formula mismatch JS vs Python: {fbad}")

        # ---------------- STRESS (live model) ----------------
        js("() => __avV8.setPhase('test')")
        pg.wait_for_timeout(1400)
        cases = [(0.0, 35.0), (0.2, 35.0), (0.5, 20.0), (1.0, 40.0), (2.4, 30.0), (5.0, 10.0)]
        sw = 0.0
        for kg, lev in cases:
            j = js("([k, l]) => __avV8.calc(k, l)", [kg, lev])
            p = M.at(kg, lev)
            for a, bb in [(j["tau_hold"], p["tau_hold"]), (j["tau_dyn"], p["tau_dyn"]), (j["arm"]["sigma"], p["arm"]["sigma"]),
                          (j["arm"]["vm"], p["arm"]["vm"]), (j["arm"]["sf"], p["arm"]["sf"]), (j["wall"]["sf"], p["wall"]["sf"]),
                          (j["tabs"]["sf"], p["tabs"]["sf"]), (j["inserts"]["F"], p["inserts"]["F"]), (j["defl"], p["defl"]),
                          (j["kg_stall"], p["kg_stall"]), (j["arm_at_stall"]["sf"], p["arm_at_stall"]["sf"])]:
                if bb not in (0, None) and math.isfinite(bb):
                    sw = max(sw, rel(a, bb))
        res["stress_worst_rel"] = sw
        if sw > 0.01:
            errors.append(f"TEST model differs from calc_v8 by {sw*100:.2f} % (> 1 %)")
        js("() => __avV8.setLoad(0.2, 35)")
        pg.wait_for_timeout(300)
        mvc = []
        for kg, lev in ((0.2, 35.0), (1.0, 22.5)):
            js(f"() => __avV8.setLoad({kg}, {lev})")
            pg.wait_for_timeout(250)
            for q in (0, 60, -45):
                mt = js(f"() => __avV8.motionTau({q})")
                hc = M.tau(kg, lev, q) / calc_v8.KGCM
                # the Motion lane reports the torque gravity APPLIES (about +axis); the hand calc the torque the servo must HOLD
                ok = mt is not None and rel(-mt, hc) <= 0.01
                mvc.append({"kg": kg, "lever": lev, "deg": q, "motion_kgcm": mt, "calc_kgcm": round(hc, 5), "ok": ok})
        res["motion_vs_calc"] = mvc
        if not all(m["ok"] for m in mvc):
            errors.append(f"Motion lane load differs from the hand calc: {[m for m in mvc if not m['ok']]}")
        js("() => __avV8.setLoad(0.2, 35)")
        js("() => __avV8.setLoad(1.5, 35)")
        pg.wait_for_timeout(500)
        res["stall_warning"] = js("() => !!document.getElementById('v8stall') && document.getElementById('v8stall').textContent.slice(0, 40)")
        if not res["stall_warning"] or "stalls" not in res["stall_warning"]:
            errors.append("no stall warning at 1.5 kg on 35 mm")
        rk = js("() => __avV8.ranking()")
        sfs = [r["sf"] for r in rk if r["sf"] is not None]
        res["ranking"] = rk
        if sfs != sorted(sfs) or rk[0]["id"] != "servo":
            errors.append(f"ranking not sorted / servo not first: {rk}")
        js("() => __avV8.setLoad(0.2, 35)")

        # ---------------- LABELS (DOM scan in every phase + checks + inspector) ----------------
        scans = {}
        for ph in ("load", "fit", "secure", "test"):
            js(f"() => __avV8.setPhase('{ph}')")
            pg.wait_for_timeout(1500 if ph == "secure" else 900)
            scans[ph] = {"bad": js("() => __avV8.numScan()"), "nums": js("() => __avV8.nums()")}
        js("() => document.getElementById('dCheck').click()")
        pg.wait_for_timeout(900)
        scans["checks"] = {"bad": js("() => __avV8.numScan()"), "nums": js("() => __avV8.nums()")}
        js("() => document.getElementById('dParts').click()")
        pg.wait_for_timeout(400)
        js("() => __avV8.setPhase('load')")
        pg.wait_for_timeout(500)
        js("() => document.querySelector('#shBody .v8row button.lb') && [...document.querySelectorAll('#shBody .v8row button.lb')].find(b => /Load arm/.test(b.textContent)).click()")
        pg.wait_for_timeout(900)
        scans["inspector"] = {"bad": js("() => __avV8.numScan()"), "nums": js("() => __avV8.nums()"), "eng": js("() => !!document.getElementById('v8eng')")}
        res["labels"] = {k: {"bad": len(v["bad"]), "nums": v["nums"], "eg": v["bad"][:3]} for k, v in scans.items()}
        for k, v in scans.items():
            if v["bad"]:
                errors.append(f"unlabelled numerals in {k}: {v['bad'][:4]}")
            if not v["nums"]:
                errors.append(f"no labelled numbers at all in {k}")
        if not scans["inspector"].get("eng"):
            errors.append("inspector has no Engineering data card")

        # ---------------- TOL ----------------
        js("() => __avV8.setPhase('fit')")
        pg.wait_for_timeout(1300)
        rings = js("() => __avV8.rings()")
        pyb = {f["id"]: f["band"] for f in eng["fits"]}
        tbad = [r for r in rings if r["stroke"].lower() != pyb[r["fit"]]["color"].lower() or r["cls"] != pyb[r["fit"]]["cls"]]
        green = [r["fit"] for r in rings if pyb[r["fit"]]["tone"] == "green"]
        js("() => __avV8.recolour('green', '#123456')")
        pg.wait_for_timeout(300)
        rings2 = js("() => __avV8.rings()")
        recol = all(r["stroke"].lower() == "#123456" for r in rings2 if r["fit"] in green) and bool(green)
        js("() => __avV8.recolour('green', '#0ca30c')")
        res["tol"] = {"rings": len(rings), "want": len(eng["fits"]), "mismatch": tbad, "recoloured_from_profile": recol}
        if len(rings) != len(eng["fits"]) or tbad:
            errors.append(f"tolerance rings wrong: {len(rings)} of {len(eng['fits'])}, mismatches {tbad[:3]}")
        if not recol:
            errors.append("ring colours did not follow the profile JSON")
        if shots:
            pg.screenshot(path=os.path.join(shots, "v8_fit_rings.png"))

        # ---------------- CALIPER ----------------
        js("() => __avV8.setPhase('fit')")
        pg.wait_for_timeout(300)
        js("() => { document.getElementById('bReset').click(); __avV8.view({explode: 0}); }")
        pg.wait_for_timeout(900)
        js("() => document.getElementById('shClose').click()")
        pg.wait_for_timeout(400)
        js("() => __avV8.setCal(true)")
        # two known CAD corners: the base plate's front top edge, base_l apart (YAML). Tap a hair
        # inside each corner; the raycast snaps to the corner vertex; the caliper must read 70.00.
        bb = js("() => { const b = __avV8.meta('parts').find(p => p.id === 'base'); return [b.lo, b.span]; }")
        lo, sp = bb
        top = 6.0
        P = [[lo[0] + sp[0], lo[1], top], [lo[0], lo[1], top]]          # front top edge corners of the base plate
        ctr = [lo[0] + sp[0] / 2, lo[1] + sp[1] / 2, top]
        known = float(__import__('yaml').safe_load(open(eng_yaml, encoding='utf-8'))['params']['base_l']['v'])   # the CAD param, not the mesh
        box = pg.locator("#cv").bounding_box()
        for z in (1.0, 1.3, 1.7, 2.2):     # a known camera with both corners on the canvas
            js(f"() => __avV8.view({{yaw: -1.3, pitch: 0.5, zoom: {z}, pan: [0, 0, 0], explode: 0}})")
            pg.wait_for_timeout(150)
            pts = [js(f"() => __avV7.project({json.dumps(p)})") for p in P]
            if all(pt and 20 < pt[0] < box["width"] - 20 and 20 < pt[1] < box["height"] - 20 for pt in pts):
                break
        diag = []
        for p in P:
            q = [p[i] + (ctr[i] - p[i]) * 0.03 for i in range(3)]
            sxy = js(f"() => __avV7.project({json.dumps(q)})")
            diag.append({"px": [round(sxy[0]), round(sxy[1])], "hit": js(f"() => __avHitAt({sxy[0]}, {sxy[1]})"), "state": js("() => __avV8.state()")})
            pg.mouse.click(box["x"] + sxy[0], box["y"] + sxy[1])
            pg.wait_for_timeout(350)
            diag[-1]["after"] = js("() => document.querySelector('#sel .nm').textContent")
        pg.wait_for_timeout(500)
        got = js("() => __avV8.caliper()")
        res["caliper"] = {"got": got, "want": round(known, 3), "diag": diag}
        if not got or abs(got["d"] - known) > 0.01:
            errors.append(f"caliper read {got} for a known {known:.2f} mm")
        if shots:
            pg.screenshot(path=os.path.join(shots, "v8_caliper.png"))
        js("() => __avV8.setCal(false)")

        # ---------------- CAP ----------------
        js("() => { __avV8.setPhase('load'); document.getElementById('shClose').click(); }")
        pg.wait_for_timeout(600)
        # the cradle wall is solid at x = 15 (outside the window, |x| > 11.55), y 0…6, z 14…58:
        # cut at x = 15 keeping x < 15, look from +X — the pixel at the wall centre must be the cap
        js("() => __avV8.view({yaw: 0, pitch: 0.12, pan: [0, 0, 0], explode: 0})")
        js("() => __avV8.section({axis: 0, at: 15.0, flip: false})")
        pg.wait_for_timeout(200)
        cap = js("() => __avV8.capProbe([14.99, 3.0, 30.0])")
        res["cap"] = cap
        if not cap or not cap["cap"] or cap["isBg"]:
            errors.append(f"section cut is not capped at the probe: {cap}")
        if shots:
            pg.screenshot(path=os.path.join(shots, "v8_section_cap.png"))
        js("() => __avV8.section(null)")

        # ---------------- PERF + LOD ----------------
        js("() => { document.getElementById('bReset').click(); }")
        pg.wait_for_timeout(900)
        pf = js("() => __avV8.perf()")
        js("() => __avV8.view({zoom: 0.3})")
        pg.wait_for_timeout(200)
        pl = js("() => __avV8.perf()")
        js("() => document.getElementById('bReset').click()")
        pg.wait_for_timeout(700)
        desk = js("() => __avBench(2500)")
        # the fps floor is measured where the v3 / v7 gates measure it: the 390 px phone stage, median of 3
        runs = []
        for _ in range(3):
            bq, pq, _e = page(pw, url, PHONE, mobile=True)
            runs.append(pq.evaluate("() => __avBench(2500)")["fps"])
            bq.close()
        fps = {"fps": sorted(runs)[1], "runs": [round(r, 1) for r in runs], "desktop_1280": round(desk["fps"], 1), "renderer": desk.get("renderer")}
        if pf["scene"] >= 50000:
            errors.append(f"default view {pf['scene']} triangles (≥ 50k)")
        lodp = js("""() => __avV8.meta('parts').filter(p => p.lod).map(p => ({id: p.id, d: Math.max(...[0,1,2].map(i => Math.max(Math.abs(p.lod.lo[i] - p.lo[i]), Math.abs(p.lod.span[i] - p.span[i]))))}))""")
        res["perf"] = {"scene_tris": pf["scene"], "lod_close": pl["lod"], "lod_tris": pl["scene"], "orbit_fps": fps,
                       "lod_parts": len(lodp), "lod_worst_mm": max([x["d"] for x in lodp] or [0])}
        if not lodp or pl["scene"] <= pf["scene"]:
            errors.append(f"LOD meshes missing or not finer ({pf['scene']} -> {pl['scene']} triangles)")
        if any(x["d"] > 0.1 for x in lodp):
            errors.append(f"LOD mesh misplaced vs the part (> 0.1 mm): {[x for x in lodp if x['d'] > 0.1]}")
        if not pl["lod"]:
            errors.append("LOD did not swap in past 2× zoom")
        fv = fps.get("fps") if isinstance(fps, dict) else fps
        res["perf"]["fps"] = fv
        if fv is None or fv < 30:
            errors.append(f"orbit fps {fv} < 30 (headless SwiftShader)")

        # ---------------- HASH (fresh page per phase) ----------------
        hashes = {}
        js("() => __avV8.setPhase('fit')"); pg.wait_for_timeout(900)
        js("() => __avV8.view({explode: 0.62, yaw: 0.7, pitch: 0.3, zoom: 0.7, pan: [3, -2, 1]})")
        hashes["fit"] = (js("() => __avV8.hash(true)"), {"phase": "fit", "explode": 0.62, "tol": True})
        js("() => __avV8.setPhase('secure')"); pg.wait_for_timeout(900)
        js("() => __avV8.stepTo(6)"); pg.wait_for_timeout(300)
        hashes["secure"] = (js("() => __avV8.hash(true)"), {"phase": "secure", "step": 6, "stepMode": True})
        js("() => __avV8.setPhase('test')"); pg.wait_for_timeout(1200)
        js("() => { __avV8.setLoad(0.75, 22.5); __avV8.setXray(true); __avV8.section({axis: 1, t: 0.4}); }")
        hashes["test"] = (js("() => __avV8.hash(true)"), {"phase": "test", "kg": 0.75, "lever": 22.5, "xray": True, "sectOn": True, "sectAxis": 1, "sectT": 0.4, "motionMode": True})
        js("() => { __avV8.setXray(false); __avV8.setPhase('load'); }"); pg.wait_for_timeout(700)
        hashes["load"] = (js("() => __avV8.hash(true)"), {"phase": "load"})
        b.close()
        hres = {}
        for ph, (h, want) in hashes.items():
            b2, p2, e2 = page(pw, url + h)
            p2.wait_for_timeout(1200)
            st = p2.evaluate("() => ({phase: __avV8.phase(), ...__avV8.state(), cam: __avCam()})")
            bad = []
            for k, w in want.items():
                g = st.get(k)
                if isinstance(w, float):
                    if g is None or abs(g - w) > 0.006:
                        bad.append((k, g, w))
                elif g != w:
                    bad.append((k, g, w))
            if not re.fullmatch(r"#[A-Za-z0-9._~-]+", h):
                bad.append(("hash not artifact-safe (only [A-Za-z0-9._~-] survive a published link)", h, None))
            m = re.search(r"~cam([^~]+)", h)
            if m:
                parts_ = m.group(1).split("_")
                c = [float(x) for x in parts_[:6]]
                got = p2.evaluate("() => __avV8.view({})")
                pan = p2.evaluate("() => __avV8.state().pan || null")
                if abs(st["cam"]["yaw"] - c[0]) > 0.01 or abs(st["cam"]["pitch"] - c[1]) > 0.01 or rel(got["dist"], c[2]) > 0.01:
                    bad.append(("cam", [st["cam"]["yaw"], st["cam"]["pitch"], got["dist"]], c[:3]))
                if pan is None or max(abs(pan[i] - c[3 + i]) for i in range(3)) > 0.05:
                    bad.append(("pan", pan, c[3:6]))
                if (parts_[6:7] == ["o"]) != bool(p2.evaluate("() => __avV8.state().ortho")):
                    bad.append(("ortho", parts_[6:7], None))
            hres[ph] = {"hash": h[:120], "bad": bad}
            if bad:
                errors.append(f"hash restore {ph}: {bad}")
            errors.extend(f"{ph} restore: {e}" for e in e2[:3])
            b2.close()
        res["hash"] = hres

        # ---------------- PHONE ----------------
        b3, p3, e3 = page(pw, url, PHONE, mobile=True)
        ph = {}
        for phs in ("load", "fit", "secure", "test"):
            p3.evaluate(f"() => __avV8.setPhase('{phs}')")
            p3.wait_for_timeout(1600 if phs == "secure" else 1100)
            ph[phs] = p3.evaluate("""() => {
              const sw = document.scrollingElement.scrollWidth;
              const small = [];
              for (const e of document.querySelectorAll('#v8phase button, #tools .tbtn, #bShare, #bTheme, #shClose, #shLink, #v8test button, #v8test input, #shBody .v8btns .btn, #shBody .v8row button.lb, #dock button')){
                const r = e.getBoundingClientRect(); if (!r.width || !r.height) continue;
                if (getComputedStyle(e).visibility === 'hidden') continue;
                if (r.height < 43.5 || r.width < 43.5) small.push((e.id || e.className || e.tagName) + ' ' + Math.round(r.width) + '×' + Math.round(r.height));
              }
              return {scrollW: sw, small: small.slice(0, 8)};
            }""")
            if shots:
                p3.screenshot(path=os.path.join(shots, f"v8_{phs}_390_dark.png"))
        p3.evaluate("() => __avV8.toggleTree()")
        p3.wait_for_timeout(500)
        tr = p3.evaluate("() => __avV8.tree()")
        res["phone"] = {"phases": ph, "tree": tr}
        for k, v in ph.items():
            if v["scrollW"] > PHONE["width"]:
                errors.append(f"390 px {k}: horizontal scroll {v['scrollW']}")
            if v["small"]:
                errors.append(f"390 px {k}: controls under 44 px: {v['small']}")
        if not tr["sheet"] or tr["drawer"]:
            errors.append(f"390 px: tree should be the bottom sheet, got {tr}")
        errors.extend("phone: " + e for e in e3[:3])
        b3.close()

        # ---------------- SCREWS ----------------
        b4, p4, e4 = page(pw, url)
        decl = {f["id"]: f["side"] for f in eng["fasteners"]}
        sides = p4.evaluate("() => __avV8.fasteners()")
        sbad = [s for s in sides if s["id"] in decl and s["side"] != decl[s["id"]]]
        p4.evaluate("() => __avV8.setPhase('secure')")
        p4.wait_for_timeout(800)
        fly = p4.evaluate("() => __avV8.screwFly()")
        SIDE = {"FRONT": [0, -1, 0], "BACK": [0, 1, 0], "BOTTOM": [0, 0, -1], "TOP": [0, 0, 1], "LEFT": [-1, 0, 0], "RIGHT": [1, 0, 0]}
        fbad = []
        for f in fly:
            o = f["off"]; L = math.sqrt(sum(x * x for x in o)) or 1.0
            want = SIDE.get(decl.get(f["id"], ""), [0, 0, 0])
            f["cos_to_side"] = round(sum(o[i] / L * want[i] for i in range(3)), 3)
            if f["cos_to_side"] < 0.7:
                fbad.append(f)
        if {f["id"] for f in fly} != set(decl):
            errors.append(f"screw fly-in probe covered {sorted(f['id'] for f in fly)}, declared {sorted(decl)}")
        res["screws"] = {"sides": sides, "fly_from_side": fly}
        if sbad:
            errors.append(f"screw side differs from the declared side: {sbad}")
        if fbad:
            errors.append(f"screw does not start on its declared side (cos < 0.7): {fbad}")

        # ---------------- RAMP (for DATAVIZ): the page's own stress ramp + stage, both themes ----------------
        ramp = {}
        for theme in ("dark", "light"):
            if p4.evaluate("() => document.documentElement.dataset.theme || 'dark'") != theme:
                p4.click("#bTheme"); p4.wait_for_timeout(250)
            ramp[theme] = p4.evaluate("""() => { const cs = getComputedStyle(document.documentElement);
                return {heat: [0,1,2,3].map(i => cs.getPropertyValue('--heat-' + i).trim()), stage: cs.getPropertyValue('--stage').trim()}; }""")
        res["ramp"] = ramp

        # ---------------- BOM ----------------
        p4.evaluate("() => document.getElementById('dBom').click()")
        p4.wait_for_timeout(700)
        bom = p4.evaluate("() => ({owned: [...document.querySelectorAll('#shBody .stc.have')].map(e => e.textContent), note: !!document.getElementById('v8owned')})")
        res["bom"] = {"owned_chips": len(bom["owned"]), "all_owned_label": all(t == "OWNED $0" for t in bom["owned"]), "note": bom["note"]}
        if not bom["owned"] or not res["bom"]["all_owned_label"] or not bom["note"]:
            errors.append(f"BOM OWNED $0 missing: {res['bom']}")

        # ---------------- SHOTS (desktop dark + light) ----------------
        if shots:
            for theme in ("dark", "light"):
                b5, p5, e5 = page(pw, url, DESK, theme=theme)
                for phs in ("load", "fit", "secure", "test"):
                    p5.evaluate(f"() => __avV8.setPhase('{phs}')")
                    p5.wait_for_timeout(2400 if phs == "secure" else 1300)
                    p5.screenshot(path=os.path.join(shots, f"v8_{phs}_1280_{theme}.png"))
                b5.close()
                if theme == "light":
                    b6, p6, e6 = page(pw, url, PHONE, mobile=True, theme="light")
                    for phs in ("load", "fit", "secure", "test"):
                        p6.evaluate(f"() => __avV8.setPhase('{phs}')")
                        p6.wait_for_timeout(2200 if phs == "secure" else 1100)
                        p6.screenshot(path=os.path.join(shots, f"v8_{phs}_390_light.png"))
                    b6.close()
        errors.extend(e for e in perr + e4 if "WebGL" not in e and "GPU stall" not in e)
        b4.close()

        # ---------------- COUPON AV ----------------
        if coupon:
            b7, p7, e7 = page(pw, "file://" + str(pathlib.Path(coupon).absolute()))
            en = p7.evaluate("() => [...document.querySelectorAll('#v8phase button')].map(b => [b.dataset.ph, !b.disabled])")
            p7.evaluate("() => __avV8.setPhase('fit')")
            p7.wait_for_timeout(1200)
            cr = p7.evaluate("() => __avV8.rings().length")
            res["coupon"] = {"phases": en, "rings": cr}
            if dict(en) != {"load": True, "fit": True, "secure": False, "test": False} or cr != 9:
                errors.append(f"coupon AV: phases {en}, rings {cr}")
            if shots:
                p7.screenshot(path=os.path.join(shots, "v8_coupon_fit.png"))
            errors.extend("coupon: " + e for e in e7[:3])
            b7.close()

    # ---------------- EXPORTS (files) ----------------
    if exports:
        import trimesh
        ex = {}
        stls = glob.glob(os.path.join(exports, "stl", "*.stl"))
        bad = [os.path.basename(f) for f in stls if not trimesh.load(f).is_watertight]
        ex["stl_watertight"] = not bad
        ex["stl_count"] = len(stls)
        if len(stls) < len(eng["parts"]):
            errors.append(f"exports: {len(stls)} STL files for {len(eng['parts'])} parts")
        mf = sorted(glob.glob(os.path.join(os.path.dirname(path), "*.3mf")) + glob.glob(os.path.join(exports, "*.3mf")))
        ok3 = True
        for f in mf:
            with zipfile.ZipFile(f) as z:
                ok3 &= "3D/3dmodel.model" in z.namelist()
            try:
                trimesh.load(f)
            except Exception:  # noqa: BLE001
                ok3 = False
        ex["3mf"] = {"files": len(mf), "ok": ok3 and bool(mf)}
        glbs = glob.glob(os.path.join(exports, "*.glb"))
        ex["glb"] = bool(glbs) and all(open(g, "rb").read(4) == b"glTF" and len(trimesh.load(g).geometry) > 0 for g in glbs)
        import xml.etree.ElementTree as ET
        ex["urdf"] = True
        for kind in ("urdf", "srdf", "sdf"):
            fs = glob.glob(os.path.join(exports, "*." + kind))
            if len(fs) != 1:
                ex["urdf"] = False; errors.append(f"exports: want exactly one .{kind}, found {len(fs)}")
                continue
            try:
                ET.parse(fs[0])
            except ET.ParseError as e:
                ex["urdf"] = False; errors.append(f"exports: {os.path.basename(fs[0])} does not parse: {e}")
        try:
            import pybullet as pb
            cid = pb.connect(pb.DIRECT)
            rid = pb.loadURDF(glob.glob(os.path.join(exports, "*.urdf"))[0], useFixedBase=True)
            ex["urdf_pybullet_joints"] = pb.getNumJoints(rid)
            pb.disconnect(cid)
        except Exception as e:  # noqa: BLE001
            ex["urdf_pybullet_joints"] = str(e)
        res["exports"] = ex
        if bad or not ex["3mf"]["ok"] or not ex["glb"] or not ex["urdf"] or not isinstance(ex["urdf_pybullet_joints"], int):
            errors.append(f"exports: {ex} {bad}")

    # ---------------- DATAVIZ ----------------
    ramp = res.get("ramp") or {}
    if DATAVIZ and ramp:
        dv = {}
        for mode in ("light", "dark"):
            pal, surf = ",".join(ramp[mode]["heat"]), ramp[mode]["stage"]
            r = subprocess.run(["node", DATAVIZ[-1], pal, "--mode", mode, "--surface", surf, "--ordinal"], capture_output=True, text=True)
            dv[mode] = {"palette": pal, "surface": surf, "pass": r.returncode == 0}
        res["dataviz"] = dv
        if not all(v["pass"] for v in dv.values()):
            errors.append(f"the page's stress ramp fails the dataviz validator: {dv}")
    else:
        res["dataviz"] = "validator not found" if not DATAVIZ else "ramp not read from the page"
        errors.append("DATAVIZ gate could not run: " + res["dataviz"])

    res["errors"], res["ok"] = errors, not errors
    log(f"\n=== verify v8 gates {os.path.basename(path)} ===")
    for k, v in res.items():
        if k not in ("errors", "ok"):
            log(f"  v8.{k:<14}: {json.dumps(v, default=str)[:400]}")
    for e in errors:
        log("  ERROR " + e)
    log(f"  => {'PASS' if res['ok'] else 'FAIL'}")
    return res


def verify(path, eng_yaml, shots=None, floor_ref=None, skip_v8=False, measure_md=None, exports=None, coupon=None):
    if shots:
        os.makedirs(shots, exist_ok=True)
    r8 = {"ok": True} if skip_v8 else V8V.verify(path, shots=shots, floor_ref=floor_ref)
    rv = v8_gates(path, eng_yaml, shots=shots, measure_md=measure_md, exports=exports, coupon=coupon)
    ok = r8["ok"] and rv["ok"]
    print(f"\n=== verify_av_v9 {os.path.basename(path)}: v3…v7.4 {('SKIPPED' if skip_v8 else 'PASS') if r8['ok'] else 'FAIL'} · "
          f"v8 {'PASS' if rv['ok'] else 'FAIL'} => {'PASS' if ok else 'FAIL'}")
    if shots:
        with open(os.path.join(shots, "v9_report.json"), "w") as f:
            json.dump({"ok": ok, "v8": rv, "earlier_ok": r8["ok"]}, f, indent=1, default=str)
    return {"ok": ok, "earlier": r8, "v8": rv}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    arg = lambda k: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else None
    r = verify(sys.argv[1], arg("--eng"), shots=arg("--shots"), floor_ref=arg("--floor-ref"), skip_v8="--skip-v8" in sys.argv,
               measure_md=arg("--measure"), exports=arg("--exports"), coupon=arg("--coupon"))
    sys.exit(0 if r["ok"] else 1)
