#!/usr/bin/env python3
"""
verify_av_v4.py — v3 + the engine v7 gates. Drives the real page in Chromium.

    python3 verify_av_v4.py OUT.html [--shots DIR] [--floor-ref V6.html]

Runs every verify_av_v3 gate first (unchanged, imported — not copied), then:

  NAV    view-cube clicks (face, edge, corner) land the view the cube names
         right-drag and shift-drag pan: the TARGET moves, every model matrix is untouched
         wheel zoom-to-cursor keeps the picked surface point under the cursor (≤ 2 px),
           in perspective AND orthographic
         two-finger pinch (real touch events through CDP) keeps the pinch point put (≤ 2 px)
         double-click a part: it is selected and its whole bbox lands inside the canvas
         orbit pivots on the picked point: that point does not move on screen (≤ 2 px)
  BUILD  every step animates (something is off its pose mid-way), ends with every
         matrix EXACTLY at the assembled pose, scrub 0.5 is mid-way, play-whole-build
         advances; zero console errors throughout
  WIRE   one connector card per node, pins numbered in order, every conductor has a
         colour swatch (and its source), a power budget with a common-ground verdict,
         a gauge/current/drop chip row on every run, and tracing shows flow in 2D + 3D
  3MF    the plate panel shows the real path on the Mac (…/av/plates/…); inside an
         artifact (window.claude stub) the button says it is zipped, and saving hands
         the platform a .zip
  LOOK   materials resolve (screw = steel …), edge lines change pixels, no GL errors
  FPS    orbit fps ≥ 30 and ≥ 0.9 × the v6 page's fps on this same machine (--floor-ref)

Chromium: Playwright's own build if installed, else the container's /opt/pw-browsers.
"""
from __future__ import annotations

import glob
import json
import math
import os
import pathlib
import sys

from playwright.sync_api import sync_playwright
from playwright.sync_api._generated import BrowserType

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# --- use the container's Chromium when Playwright's pinned build is absent ------------
_launch = BrowserType.launch


def _launch_any(self, *a, **k):
    try:
        return _launch(self, *a, **k)
    except Exception as e:  # noqa: BLE001 — only the "executable doesn't exist" case is retried
        if "Executable doesn't exist" not in str(e) or "executable_path" in k:
            raise
        exe = os.environ.get("AV_CHROMIUM") or (sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux*/chrome")) or [None])[-1]
        if not exe:
            raise
        k["executable_path"] = exe
        return _launch(self, *a, **k)


BrowserType.launch = _launch_any

import verify_av_v3 as V3  # noqa: E402

PHONE = {"width": 390, "height": 844}
DESK = {"width": 1280, "height": 860}


def ang(a, b):
    d = (a - b + math.pi) % (2 * math.pi) - math.pi
    return abs(d)


def bench_fps(b, url, ms=3000):
    pg = b.new_page(viewport=PHONE, device_scale_factor=2, has_touch=True, is_mobile=True)
    pg.goto(url)
    pg.wait_for_timeout(2600)
    pg.evaluate("() => document.getElementById('bReset').click()")
    pg.wait_for_timeout(300)
    r = pg.evaluate(f"async () => await __avBench({ms})")
    pg.close()
    return r


def v7_gates(path, shots=None, floor_ref=None, log=print):
    url = "file://" + str(pathlib.Path(path).absolute())
    errors, warnings, res = [], [], {}
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport=PHONE, device_scale_factor=2, has_touch=True, is_mobile=True)
        pg.on("pageerror", lambda e: errors.append("PAGEERROR " + str(e)))
        pg.on("console", lambda m: (errors if m.type == "error" else warnings).append(f"{m.type.upper()} {m.text}"))
        pg.goto(url)
        pg.wait_for_timeout(2600)
        if not pg.evaluate("() => !!window.__avV7"):
            errors.append("__avV7 missing — not a v7 engine page")
            b.close()
            return {"errors": errors, "warnings": warnings, "ok": False}
        st = pg.evaluate("() => __avState()")
        box = pg.locator("#cv").bounding_box()
        X0, Y0, W, H = box["x"], box["y"], box["width"], box["height"]
        reset = lambda: (pg.evaluate("() => document.getElementById('bReset').click()"), pg.wait_for_timeout(520))
        cam = lambda: pg.evaluate("() => __avV7.cam()")

        def home():
            # back to the plain assembly: Parts tab, phone sheet closed, camera reset
            pg.evaluate("() => document.getElementById('dParts').click()")
            pg.wait_for_timeout(250)
            pg.evaluate("() => { if (!matchMedia('(min-width:900px)').matches) document.getElementById('shClose').click(); }")
            pg.wait_for_timeout(250)
            reset()

        def find_hit(dxs=(0, -40, 40, -80, 80, -20, 20), dys=(0, -40, 40, -80, 80, 20)):
            for dy in dys:
                for dx in dxs:
                    x, y = W / 2 + dx, H * 0.42 + dy
                    w = pg.evaluate(f"() => __avV7.worldAt({x},{y})")
                    if w["hit"]:
                        return x, y, w
            return None

        # ---------------- NAV: view cube ----------------
        cube = []
        # (face, zone i, zone j, expected outward normal, reset first?) — TOP is clicked from the
        # corner view, where it faces the camera; a face seen edge-on is not a target on a phone
        for face, i, j, N, rs in (("FRONT", 1, 1, [1, -1, 1], True), ("TOP", 0, 0, [0, 0, 1], False),
                                  ("FRONT", 0, 1, [0, -1, 1], True), ("RIGHT", 0, 0, [1, 0, 0], True),
                                  ("FRONT", 0, 0, [0, -1, 0], True), ("RIGHT", -1, -1, [1, -1, -1], True)):
            if rs:
                reset()
            pt = pg.evaluate(f"() => __avV7.cubePoint('{face}',{i},{j})")
            pg.mouse.click(pt[0], pt[1])
            pg.wait_for_timeout(650)
            want = pg.evaluate(f"() => __avV7.viewOfNormal({json.dumps(N)})")
            got = cam()
            ok = ang(got["yaw"], want["yaw"]) < 0.02 and abs(got["pitch"] - want["pitch"]) < 0.02
            cube.append({"face": face, "zone": [i, j], "want": [round(want["yaw"], 3), round(want["pitch"], 3)],
                         "got": [round(got["yaw"], 3), round(got["pitch"], 3)], "ok": ok})
            if face == "FRONT" and i == 1 and shots:
                pg.screenshot(path=os.path.join(shots, "v7_cube_corner.png"))
        res["cube"] = cube
        for c in cube:
            if not c["ok"]:
                errors.append(f"view cube {c['face']} zone {c['zone']} landed {c['got']}, want {c['want']}")

        # ---------------- NAV: pan moves the target, not the model ----------------
        reset()
        pans = {}
        for how in ("right", "shift"):
            m0 = pg.evaluate("() => JSON.stringify(__avV7.models())")
            c0 = cam()
            cx, cy = X0 + W / 2, Y0 + H * 0.42
            pg.mouse.move(cx, cy)
            if how == "shift":
                pg.keyboard.down("Shift")
            pg.mouse.down(button="right" if how == "right" else "left")
            pg.mouse.move(cx + 70, cy - 40, steps=8)
            pg.mouse.up(button="right" if how == "right" else "left")
            if how == "shift":
                pg.keyboard.up("Shift")
            pg.wait_for_timeout(150)
            m1 = pg.evaluate("() => JSON.stringify(__avV7.models())")
            c1 = cam()
            moved = math.dist(c0["target"], c1["target"])
            pans[how] = {"targetMoved_mm": round(moved, 2), "modelsSame": m0 == m1,
                         "yawSame": abs(c0["yaw"] - c1["yaw"]) < 1e-9, "distSame": abs(c0["dist"] - c1["dist"]) < 1e-9}
            if not (moved > 1 and m0 == m1 and pans[how]["yawSame"] and pans[how]["distSame"]):
                errors.append(f"pan ({how}-drag) did not move only the target: {pans[how]}")
        res["pan"] = pans

        # ---------------- NAV: zoom to cursor (persp + ortho) ----------------
        zooms = {}
        for proj in ("persp", "ortho"):
            reset()
            pg.evaluate(f"() => __avV7.setOrtho({'true' if proj == 'ortho' else 'false'})")
            pg.wait_for_timeout(100)
            h = find_hit(dxs=(60, -60, 30, -30, 0), dys=(-50, 50, -20, 20, 0))
            if not h:
                errors.append(f"zoom-to-cursor ({proj}): no surface found to aim at")
                continue
            x, y, w = h
            P = w["p"]
            pg.mouse.move(X0 + x, Y0 + y)
            for _ in range(4):
                pg.mouse.wheel(0, -240)
                pg.wait_for_timeout(60)
            pg.wait_for_timeout(150)
            s = pg.evaluate(f"() => __avV7.project({json.dumps(P)})")
            err = math.dist(s, [x, y]) if s else 1e9
            d0 = w
            zooms[proj] = {"cursor": [round(x, 1), round(y, 1)], "after": [round(s[0], 2), round(s[1], 2)] if s else None,
                           "err_px": round(err, 3), "dist": round(cam()["dist"], 1)}
            if err > 2.0:
                errors.append(f"zoom-to-cursor ({proj}) drifted {err:.2f} px > 2 px")
        pg.evaluate("() => __avV7.setOrtho(false)")
        res["zoom"] = zooms

        # ---------------- NAV: orbit pivots on the picked point ----------------
        reset()
        h = find_hit(dxs=(50, -50, 25, -25, 0), dys=(-40, 40, 0))
        if h:
            x, y, w = h
            pg.mouse.move(X0 + x, Y0 + y)
            pg.mouse.down()
            pg.mouse.move(X0 + x + 60, Y0 + y + 25, steps=6)
            pg.mouse.up()
            pg.wait_for_timeout(120)
            s = pg.evaluate(f"() => __avV7.project({json.dumps(w['p'])})")
            err = math.dist(s, [x, y]) if s else 1e9
            res["orbitPivot"] = {"err_px": round(err, 3)}
            if err > 2.0:
                errors.append(f"orbit did not pivot on the picked point ({err:.2f} px)")

        # ---------------- NAV: two-finger pinch about its centre (CDP touch) ----------------
        reset()
        cdp = pg.context.new_cdp_session(pg)
        h = find_hit(dxs=(0, 30, -30), dys=(0, 30, -30))
        if h:
            x, y, w = h
            c = [X0 + x, Y0 + y]

            def touch(kind, d):
                pts = [{"x": c[0] - d, "y": c[1], "id": 1}, {"x": c[0] + d, "y": c[1], "id": 2}] if kind != "touchEnd" else []
                cdp.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": pts})

            touch("touchStart", 30)
            for d in range(32, 92, 6):
                touch("touchMove", d)
                pg.wait_for_timeout(16)
            touch("touchEnd", 0)
            pg.wait_for_timeout(150)
            s = pg.evaluate(f"() => __avV7.project({json.dumps(w['p'])})")
            # the point that started under the pinch centre stays under it
            err = math.dist(s, [x, y]) if s else 1e9
            res["pinch"] = {"err_px": round(err, 3), "dist": round(cam()["dist"], 1)}
            if err > 2.0:
                errors.append(f"pinch-zoom drifted {err:.2f} px from the pinch centre")

        # ---------------- NAV: double-click a part = fit it ----------------
        reset()
        h = find_hit()
        if h:
            x, y, w = h
            pid = w["part"]
            before = pg.evaluate(f"() => __avV7.bboxScreen('{pid}')")
            pg.mouse.dblclick(X0 + x, Y0 + y)
            pg.wait_for_timeout(700)
            sb = pg.evaluate(f"() => __avV7.bboxScreen('{pid}')")
            sel = pg.evaluate("() => __avState().sel")
            pts = [p for p in sb["pts"] if p]
            inside = len(pts) == 8 and all(-1 <= p[0] <= sb["W"] + 1 and -1 <= p[1] <= sb["H"] + 1 for p in pts)
            span = lambda q: max(p[0] for p in q if p) - min(p[0] for p in q if p)
            res["dblFit"] = {"part": pid, "sel": sel, "inside": inside,
                             "spanBefore": round(span(before["pts"]), 1), "spanAfter": round(span(pts), 1)}
            if not inside:
                errors.append(f"double-tap fit left part {pid} partly off the canvas: {sb}")
            if sel != [pid]:
                errors.append(f"double-tap fit did not select the part ({sel})")
            if shots:
                pg.screenshot(path=os.path.join(shots, "v7_dblfit.png"))

        # ---------------- BUILD: every step animates and lands exactly ----------------
        reset()
        steps = []
        if st["steps"]:
            pg.locator("#dBuild").click()
            pg.wait_for_timeout(500)
            for n in range(1, st["steps"] + 1):
                pg.locator(f"#tlTrack .tick[data-n='{n}']").click()
                pg.wait_for_timeout(60)
                a0 = pg.evaluate("() => __avV7.anim()")
                mid = 0.0
                if a0 and a0["keys"]:
                    pg.wait_for_timeout(int(a0["dur"] * 0.35))
                    mid = max([q["d"] for q in pg.evaluate("() => __avV7.midPose()")] or [0])
                    if n == 2 and shots:
                        pg.screenshot(path=os.path.join(shots, "v7_build_mid.png"))
                for _ in range(60):
                    a = pg.evaluate("() => __avV7.anim()")
                    if not a or a["u"] >= 1:
                        break
                    pg.wait_for_timeout(100)
                a = pg.evaluate("() => __avV7.anim()")
                pose = pg.evaluate("() => __avV7.stepPose()")
                worst = max([q["d"] for q in pose] or [0])
                steps.append({"n": n, "keys": (a0 or {}).get("keys"), "dur": (a0 or {}).get("dur"),
                              "midOff": round(mid, 2), "endU": a and a["u"], "endErr": worst})
                if a and a["u"] < 1:
                    errors.append(f"step {n} animation never finished")
                if worst != 0:
                    errors.append(f"step {n} ended {worst} off the assembled pose")
                if a0 and a0["keys"] and mid <= 0.01:
                    errors.append(f"step {n} has {a0['keys']} entering parts but nothing moved mid-animation")
            # scrub: half-way is mid-flight, full is exact
            pg.evaluate("() => { const r=document.getElementById('saScrub'); r.value=500; r.dispatchEvent(new Event('input')); }")
            pg.wait_for_timeout(100)
            sc = pg.evaluate("() => __avV7.anim()")
            pg.evaluate("() => { const r=document.getElementById('saScrub'); r.value=1000; r.dispatchEvent(new Event('input')); }")
            pg.wait_for_timeout(100)
            scEnd = max([q["d"] for q in pg.evaluate("() => __avV7.stepPose()")] or [0])
            res["scrub"] = {"at500": sc, "endErr": scEnd}
            if not sc or abs(sc["u"] - 0.5) > 1e-6 or not sc["paused"]:
                errors.append(f"scrub did not hold the step at 0.5: {sc}")
            if scEnd != 0:
                errors.append(f"scrub to the end left parts {scEnd} off pose")
            # play whole build
            pg.locator("#tlTrack .tick[data-n='1']").click()
            pg.wait_for_timeout(100)
            pg.locator("#tl .tlbar .btn.pri").click()
            pg.wait_for_timeout(5600)
            no = pg.locator("#tl .no").inner_text()
            pg.locator("#tl .tlbar .btn.pri").click()
            res["playWhole"] = no
            if no.startswith("STEP 01"):
                errors.append(f"play whole build did not advance: {no}")
        res["steps"] = steps
        reset()

        # ---------------- WIRE ----------------
        if pg.locator("#dWire").is_visible():
            pg.locator("#dWire").click()
            pg.wait_for_timeout(700)
            wr = pg.evaluate("""() => {
              const cards=[...document.querySelectorAll('#pinouts .pcard')];
              return {nodes: __avV7.pinouts().length, cards: cards.length,
                cardInfo: cards.map(c=>({node:c.dataset.node,
                  orders:[...c.querySelectorAll('.pco')].map(e=>+e.textContent),
                  swatches:c.querySelectorAll('.pcw').length, rows:c.querySelectorAll('.pcr').length,
                  src:[...c.querySelectorAll('.pcr')].map(r=>r.dataset.src),
                  connector:c.querySelector('.pcc').textContent})),
                budget: __avV7.budget(), budgetCard: !!document.getElementById('pBudget'),
                chips: [...document.querySelectorAll('.wrow')].map(r=>r.querySelectorAll('.wchip').length),
                runs: __avState().runs};
            }""")
            res["wire"] = wr
            if wr["cards"] != wr["nodes"]:
                errors.append(f"wiring: {wr['cards']} connector cards for {wr['nodes']} nodes")
            for c in wr["cardInfo"]:
                if not c["rows"] or c["orders"] != list(range(1, len(c["orders"]) + 1)) or c["swatches"] != c["rows"]:
                    errors.append(f"wiring: node {c['node']} pin order/colours incomplete: {c}")
            unset = sum(s == "unset" for c in wr["cardInfo"] for s in c["src"])
            if unset:
                warnings.append(f"wiring: {unset} conductors have no colour in the config (shown as unset — add pin.color)")
            if not wr["budgetCard"]:
                errors.append("wiring: no power budget card")
            if wr["budget"]["rating"] is None:
                warnings.append("wiring: supply rating not found — add node.supply.amps")
            if not wr["budget"]["ground"]["ok"]:
                errors.append(f"wiring: no common ground: {wr['budget']['ground']}")
            if wr["budget"]["status"] == "fail":
                errors.append(f"wiring: power budget over the supply rating: {wr['budget']}")
            if any(n < 3 for n in wr["chips"]) or len(wr["chips"]) != wr["runs"]:
                errors.append(f"wiring: a run is missing its gauge/current/drop chips: {wr['chips']}")
            if shots:
                pg.locator("#pinouts").scroll_into_view_if_needed()
                pg.screenshot(path=os.path.join(shots, "v7_pinouts.png"))
            pg.locator(".wrow").nth(0).click()
            pg.wait_for_timeout(500)
            fl = pg.evaluate("""() => ({eflow: document.querySelectorAll('#shBody .eflow').length,
                flow3: [...document.querySelectorAll('#leads .flow3')].filter(e=>(e.getAttribute('points')||'').split(' ').length>1).length,
                anim: getComputedStyle(document.querySelector('#shBody .eflow')||document.body).animationName})""")
            res["flow"] = fl
            if fl["eflow"] != 1 or fl["flow3"] != 1:
                errors.append(f"wiring: tracing a run did not show current flow in 2D + 3D: {fl}")
            if shots:
                pg.screenshot(path=os.path.join(shots, "v7_wire_trace.png"))
            reset()

        # ---------------- 3MF: local path ----------------
        if pg.locator("#dPlate").is_visible():
            pg.locator("#dPlate").click()
            pg.wait_for_timeout(600)
            lp = pg.evaluate("() => { const c=document.getElementById('localPath'); return c ? [...c.querySelectorAll('.lpv')].map(e=>e.textContent) : null; }")
            res["platePath"] = lp
            if not lp or not any("/av/plates/" in x or x.endswith(".3mf") for x in lp):
                errors.append(f"plate panel does not show the Mac path of the 3MF: {lp}")
            btn = pg.evaluate("() => [...document.querySelectorAll('#plBody button')].map(b=>b.textContent).find(t=>/3MF/.test(t))")
            res["plateBtnLocal"] = btn
            if shots:
                pg.screenshot(path=os.path.join(shots, "v7_plate.png"))
            reset()

        # ---------------- LOOK ----------------
        look = pg.evaluate("""() => { const ps=__avParts(); const out={};
            for (const p of ps){ const k=__avV7.mat(p.id); out[k]=(out[k]||0)+1; } return out; }""")
        res["materials"] = look
        scr = [p for p in pg.evaluate("() => __avParts()") if p["kind"] == "screw"]
        if scr and pg.evaluate(f"() => __avV7.mat('{scr[0]['id']}')") != "steel":
            errors.append("a screw did not shade as steel")
        a = pg.locator("#stage").screenshot()
        pg.evaluate("() => document.getElementById('bEdge').click()")
        pg.wait_for_timeout(150)
        bimg = pg.locator("#stage").screenshot()
        pg.evaluate("() => document.getElementById('bEdge').click()")
        res["edgesChangePixels"] = a != bimg
        if a == bimg:
            errors.append("edge lines toggle changed no pixels")
        glerr = pg.evaluate("() => { const c=document.getElementById('cv'); const g=c.getContext('webgl2'); return g ? g.getError() : -1; }")
        res["glError"] = glerr
        if glerr not in (0, -1):
            errors.append(f"WebGL error after drawing: {glerr}")

        # ---------------- screenshots: 390 + 1280, light + dark ----------------
        if shots:
            for theme in ("dark", "light"):
                for vp, tag in ((PHONE, "390"), (DESK, "1280")):
                    pg.set_viewport_size(vp)
                    pg.evaluate(f"() => {{ document.documentElement.setAttribute('data-theme','{theme}'); }}")
                    pg.wait_for_timeout(250)
                    home()
                    pg.screenshot(path=os.path.join(shots, f"v7_home_{tag}_{theme}.png"))
                    if st["steps"]:
                        pg.locator("#dBuild").click()
                        pg.wait_for_timeout(400)
                        pg.locator("#tlTrack .tick[data-n='2']").click()
                        pg.wait_for_timeout(450)
                        pg.screenshot(path=os.path.join(shots, f"v7_build_{tag}_{theme}.png"))
                        pg.wait_for_timeout(2200)
                    if pg.locator("#dWire").is_visible():
                        pg.locator("#dWire").click()
                        pg.wait_for_timeout(500)
                        pg.locator(".wrow").nth(0).click()
                        pg.wait_for_timeout(400)
                        pg.screenshot(path=os.path.join(shots, f"v7_wire_{tag}_{theme}.png"), full_page=False)
                    home()
                    pg.evaluate("() => __avV7.setOrtho(true)")
                    pg.evaluate("() => document.querySelector(\"#views .chip[data-view='front']\").click()")
                    pg.wait_for_timeout(500)
                    pg.screenshot(path=os.path.join(shots, f"v7_ortho_front_{tag}_{theme}.png"))
                    pg.evaluate("() => __avV7.setOrtho(false)")
            pg.set_viewport_size(PHONE)
            pg.evaluate("() => document.documentElement.removeAttribute('data-theme')")

        # ---------------- artifact: honest zip label + the platform gets a .zip ----------------
        pa = b.new_page(viewport=PHONE, device_scale_factor=2)
        pa.add_init_script("""window.__saved=[]; window.claude={use: async (n)=> n==='downloads' ?
            {save: async (o)=>{ window.__saved.push({name:o.filename, size:o.data.size, type:o.data.type}); }} : null};""")
        pa.on("pageerror", lambda e: errors.append("PAGEERROR(artifact) " + str(e)))
        pa.goto(url + "#tab=plate")
        pa.wait_for_timeout(1800)
        if pa.locator("#dPlate").is_visible():
            pa.locator("#dPlate").click()
            pa.wait_for_timeout(500)
            lab = pa.evaluate("() => [...document.querySelectorAll('#plBody button')].map(b=>b.textContent).find(t=>/3MF/.test(t))")
            pa.evaluate("() => [...document.querySelectorAll('#plBody button')].find(b=>/3MF/.test(b.textContent)).click()")
            pa.wait_for_timeout(2500)
            saved = pa.evaluate("() => window.__saved")
            res["artifact"] = {"label": lab, "saved": saved}
            if not lab or "zipped by the viewer" not in lab:
                errors.append(f"artifact 3MF button is not labelled honestly: {lab!r}")
            if not saved or not saved[0]["name"].endswith(".zip"):
                errors.append(f"artifact 3MF did not go to the platform as a .zip: {saved}")
        pa.close()

        # ---------------- FPS vs the v6 floor ----------------
        # best of two, interleaved with the v6 page: software-WebGL timing swings ±20 % run to run
        ref = "file://" + str(pathlib.Path(floor_ref).absolute()) if floor_ref else None
        r7, r6 = [], []
        for _ in range(2):
            r7.append(bench_fps(b, url))
            if ref:
                r6.append(bench_fps(b, ref))
        f7 = max(r7, key=lambda r: r["fps"])
        res["fps"] = {"v7": round(f7["fps"], 1), "medianMs": round(f7["medianMs"], 1), "runs7": [round(r["fps"], 1) for r in r7]}
        if ref:
            f6 = max(r6, key=lambda r: r["fps"])
            res["fps"]["v6"] = round(f6["fps"], 1)
            res["fps"]["runs6"] = [round(r["fps"], 1) for r in r6]
            if f7["fps"] < 0.9 * f6["fps"]:
                errors.append(f"fps {f7['fps']:.1f} below the v6 floor {f6['fps']:.1f} on this machine")
        if f7["fps"] < 30:
            errors.append(f"fps {f7['fps']:.1f} below the 30 fps floor")
        b.close()

    res["errors"], res["warnings"], res["ok"] = errors, warnings, not errors
    log(f"\n=== verify v7 gates {os.path.basename(path)} ===")
    for k, v in res.items():
        if k not in ("errors", "warnings", "ok"):
            log(f"  v7.{k:<16}: {json.dumps(v)[:600]}")
    for w in warnings:
        if "GPU stall" not in w and "GL Driver" not in w:
            log("  WARN  " + w)
    for e in errors:
        log("  ERROR " + e)
    log(f"  => {'PASS' if res['ok'] else 'FAIL'}")
    return res


def verify(path, shots=None, floor_ref=None, skip_v3=False):
    if shots:
        os.makedirs(shots, exist_ok=True)
    r3 = {"ok": True} if skip_v3 else V3.verify(path, shots=shots)
    r7 = v7_gates(path, shots=shots, floor_ref=floor_ref)
    ok = r3["ok"] and r7["ok"]
    print(f"\n=== verify_av_v4 {os.path.basename(path)}: v3 {'PASS' if r3['ok'] else 'FAIL'} · "
          f"v7 {'PASS' if r7['ok'] else 'FAIL'} => {'PASS' if ok else 'FAIL'}")
    return {"ok": ok, "v3": r3, "v7": r7}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    arg = lambda k: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else None
    r = verify(sys.argv[1], shots=arg("--shots"), floor_ref=arg("--floor-ref"), skip_v3="--skip-v3" in sys.argv)
    sys.exit(0 if r["ok"] else 1)
