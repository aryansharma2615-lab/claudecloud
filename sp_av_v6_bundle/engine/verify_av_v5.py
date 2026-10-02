#!/usr/bin/env python3
"""
verify_av_v5.py — v4 (= v3 + v7) + the engine v7.1 gates.

    python3 verify_av_v5.py OUT.html [--shots DIR] [--floor-ref V6.html] [--skip-v4]

  WIRES   no conductor left "unset"; every conductor resolves to config / factory lead /
          carried-along-a-run / convention / "any colour"
  TRACES  at explode 0.6 one trace per exploded part; none at explode 0
  SEARCH  typing filters the Parts list to matching rows; Enter selects + opens the first hit
  BENCH   "Mark done" survives a reload (device-local), the timeline tick shows it
  FILES   Snap downloads a PNG, the wire cut list a CSV with one row per run; inside an
          artifact both go to the platform as-is (.png / .csv, no zip)
  PEEK    a 0.7 s press on a part selects it and opens its card, and the release does not
          toggle it back off
  SCALE   the bar's pixels × mm-per-pixel = its label (≤ 1 %), and in ortho a projected
          segment of that length matches the bar (≤ 2 %)
  LINK    the copied link restores yaw / pitch / dist / pan / ortho in a fresh page
  FOCUS   hides the header and presets, the stage grows, and it comes back
"""
from __future__ import annotations

import json
import math
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import verify_av_v4 as V4  # noqa: E402  (also installs the Chromium fallback)
from playwright.sync_api import sync_playwright  # noqa: E402

PHONE = V4.PHONE


def v71_gates(path, shots=None, log=print):
    url = "file://" + str(pathlib.Path(path).absolute())
    errors, warnings, res = [], [], {}
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        ctx = b.new_context(viewport=PHONE, device_scale_factor=2, has_touch=True, is_mobile=True, accept_downloads=True)
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append("PAGEERROR " + str(e)))
        pg.on("console", lambda m: errors.append("CONSOLE " + m.text) if m.type == "error" else None)
        pg.goto(url)
        pg.wait_for_timeout(2600)
        if pg.evaluate("() => !(window.__avV7 && __avV7.ver && __avV7.ver() >= '7.1')"):
            errors.append("not a v7.1 engine page")
            b.close()
            return {"errors": errors, "warnings": warnings, "ok": False}
        js = lambda code: pg.evaluate(code)
        click = lambda sel: js(f"() => document.querySelector({json.dumps(sel)}).click()")
        reset = lambda: (js("() => document.getElementById('bReset').click()"), pg.wait_for_timeout(500))
        st = js("() => __avState()")
        box = pg.locator("#cv").bounding_box()
        X0, Y0, W, H = box["x"], box["y"], box["width"], box["height"]

        # ---------------- WIRES ----------------
        if st["runs"]:
            po = js("() => __avV7.pinouts()")
            srcs = {}
            for n in po:
                for p in n["pins"]:
                    for w in p["wires"]:
                        srcs[w["src"]] = srcs.get(w["src"], 0) + 1
            res["wireSources"] = srcs
            if srcs.get("unset"):
                errors.append(f"wiring: {srcs['unset']} conductors still unset")

        # ---------------- TRACES ----------------
        reset()
        js("() => { const e=document.getElementById('ex'); e.value=60; e.dispatchEvent(new Event('input')); }")
        pg.wait_for_timeout(250)
        want = js("""() => { let n=0; for (const p of __avParts()) { if (p.kind==='wire') continue;
                     const b=__avV7.models().find(m=>m.id===p.id); if (!b) continue;
                     const m=b.m; if (Math.hypot(m[12],m[13],m[14])>=1) n++; } return n; }""")
        got = js("() => __avV7.traces()")
        shown = js("() => [...document.querySelectorAll('#leads .trace')].filter(e=>e.style.display!=='none').length")
        if shots:
            pg.screenshot(path=os.path.join(shots, "v71_traces.png"))
        js("() => { const e=document.getElementById('ex'); e.value=0; e.dispatchEvent(new Event('input')); }")
        pg.wait_for_timeout(200)
        shown0 = js("() => [...document.querySelectorAll('#leads .trace')].filter(e=>e.style.display!=='none').length")
        res["traces"] = {"exploded": want, "traces": got, "shown": shown, "shownAt0": shown0}
        if got != want or shown != want or want == 0 or shown0:
            errors.append(f"explode traces wrong: {res['traces']}")

        # ---------------- SEARCH ----------------
        reset()
        click("#dParts")
        pg.wait_for_timeout(400)
        parts = [p for p in js("() => __avParts()") if p["kind"] not in ("wire", "screw")]
        target = parts[min(2, len(parts) - 1)]
        q = target["label"].split(" ")[0][:6]
        pg.fill("#partQ", q)
        pg.wait_for_timeout(150)
        vis = js("() => [...document.querySelectorAll('#shBody .row[data-id]')].filter(r=>r.style.display!=='none').map(r=>r.querySelector('.lb').textContent)")
        allrows = js("() => document.querySelectorAll('#shBody .row[data-id]').length")
        pg.press("#partQ", "Enter")
        pg.wait_for_timeout(600)
        sel = js("() => __avState().sel")
        title = js("() => document.getElementById('shTitle').textContent")
        res["search"] = {"q": q, "visible": len(vis), "of": allrows, "sel": sel, "title": title}
        if not vis or len(vis) >= allrows and allrows > 3:
            errors.append(f"search did not filter: {res['search']}")
        if any(q.lower() not in v.lower() for v in vis) and not any(q.lower() in v.lower() for v in vis):
            errors.append(f"search shows rows that do not match: {vis[:4]}")
        if len(sel) != 1 or title not in [p["label"] for p in parts if p["id"] == sel[0]]:
            errors.append(f"search Enter did not select + open the first hit: {res['search']}")
        if shots:
            pg.screenshot(path=os.path.join(shots, "v71_search.png"))

        # ---------------- BENCH checklist (persists across reload) ----------------
        reset()
        if st["steps"] >= 2:
            click("#dBuild")
            pg.wait_for_timeout(400)
            click("#tlTrack .tick[data-n='2']")
            pg.wait_for_timeout(300)
            if 2 not in js("() => __avV7.done()"):
                click("#stDone")
            pg.wait_for_timeout(150)
            d1 = js("() => __avV7.done()")
            pg.reload()
            pg.wait_for_timeout(2600)
            d2 = js("() => __avV7.done()")
            click("#dBuild")
            pg.wait_for_timeout(500)
            tick = js("() => document.querySelector(\"#tlTrack .tick[data-n='2']\").classList.contains('ok')")
            prog = js("() => document.getElementById('stProg').textContent")
            if shots:
                pg.screenshot(path=os.path.join(shots, "v71_bench.png"))
            click("#tlTrack .tick[data-n='2']")
            pg.wait_for_timeout(300)
            click("#stDone")                       # leave the device as we found it
            d3 = js("() => __avV7.done()")
            res["bench"] = {"afterTick": d1, "afterReload": d2, "tickOk": tick, "progress": prog, "afterClear": d3}
            if 2 not in d1 or 2 not in d2 or not tick or 2 in d3:
                errors.append(f"bench checklist did not persist / show: {res['bench']}")
            reset()

        # ---------------- FILES (local: real downloads) ----------------
        with pg.expect_download() as dl:
            click("#bSnap")
        d = dl.value
        p = d.path()
        res["snap"] = {"name": d.suggested_filename, "bytes": os.path.getsize(p) if p else 0}
        if not d.suggested_filename.endswith(".png") or res["snap"]["bytes"] < 2000:
            errors.append(f"snapshot is not a real PNG: {res['snap']}")
        if st["runs"]:
            click("#dWire")
            pg.wait_for_timeout(600)
            with pg.expect_download() as dl:
                click("#bCutList")
            d = dl.value
            txt = pathlib.Path(d.path()).read_text(encoding="utf-8")
            lines = [x for x in txt.splitlines() if x.strip()]
            res["cutList"] = {"name": d.suggested_filename, "rows": len(lines) - 1, "header": lines[0][:120]}
            if not d.suggested_filename.endswith(".csv") or len(lines) - 1 != st["runs"] or "cut_mm" not in lines[0]:
                errors.append(f"wire cut list wrong: {res['cutList']}")
            reset()

        # ---------------- PEEK: long-press ----------------
        reset()
        click("#dParts")                           # out of the wiring view: ghosts cannot be picked
        pg.wait_for_timeout(300)
        js("() => document.getElementById('shClose').click()")
        pg.wait_for_timeout(300)
        hit = None
        for fy in (0.42, 0.5, 0.36, 0.58, 0.3, 0.64):
            for dx in (0, -30, 30, -60, 60):
                w = js(f"() => __avV7.worldAt({W/2+dx},{H*fy})")
                if w["hit"]:
                    hit = (W / 2 + dx, H * fy, w["part"])
                    break
            if hit:
                break
        if not hit:
            errors.append("long-press: no part found under the probe grid")
        if hit:
            x, y, pid = hit
            pg.mouse.move(X0 + x, Y0 + y)
            pg.mouse.down()
            pg.wait_for_timeout(750)
            pg.mouse.up()
            pg.wait_for_timeout(400)
            sel = js("() => __avState().sel")
            title = js("() => document.getElementById('shTitle').textContent")
            lab = next((p["label"] for p in js("() => __avParts()") if p["id"] == pid), None)
            res["peek"] = {"part": pid, "sel": sel, "title": title}
            sheet = js("() => document.getElementById('sheet').classList.contains('open')")
            res["peek"]["sheetOpen"] = sheet
            if sel != [pid] or not sheet or not title:
                errors.append(f"long-press did not select + open the part: {res['peek']}")
            if shots:
                pg.screenshot(path=os.path.join(shots, "v71_peek.png"))
        reset()

        # ---------------- SCALE ----------------
        js("() => document.getElementById('shClose').click()")
        pg.wait_for_timeout(300)
        sc = js("() => __avV7.scale()")
        e1 = abs(sc["px"] * sc["mmPerPx"] - sc["mm"]) / sc["mm"]
        js("() => __avV7.setOrtho(true)")
        pg.wait_for_timeout(100)
        sc2 = js("() => __avV7.scale()")
        seg = js(f"""() => {{ const c=__avV7.cam(), t=c.target, y=c.yaw;
            const rt=[Math.sin(y),-Math.cos(y),0];             // camera right, horizontal
            const a=__avV7.project(t), b=__avV7.project([t[0]+rt[0]*{sc2['mm']}, t[1]+rt[1]*{sc2['mm']}, t[2]]);
            return Math.hypot(a[0]-b[0], a[1]-b[1]); }}""")
        e2 = abs(seg - sc2["px"]) / sc2["px"]
        js("() => __avV7.setOrtho(false)")
        res["scale"] = {"persp": sc, "relErr": round(e1, 5), "ortho": sc2, "orthoSegPx": round(seg, 2), "orthoErr": round(e2, 5)}
        if e1 > 0.01 or e2 > 0.02:
            errors.append(f"scale bar does not match the view: {res['scale']}")

        # ---------------- LINK: camera in the copied link ----------------
        reset()
        pt = js("() => __avV7.cubePoint('FRONT',1,1)")
        pg.mouse.click(pt[0], pt[1])
        pg.wait_for_timeout(600)
        pg.mouse.move(X0 + W / 2, Y0 + H * 0.4)
        pg.mouse.down(button="right")
        pg.mouse.move(X0 + W / 2 + 30, Y0 + H * 0.4 + 20, steps=4)
        pg.mouse.up(button="right")
        js("() => __avV7.setOrtho(true)")
        c0 = js("() => __avV7.cam()")
        h = js("() => __avV7.camHash()")
        p2 = ctx.new_page()
        p2.goto(url + h)
        p2.wait_for_timeout(2200)
        c1 = p2.evaluate("() => __avV7.cam()")
        p2.close()
        js("() => __avV7.setOrtho(false)")
        ok = (abs(c0["yaw"] - c1["yaw"]) < 2e-3 and abs(c0["pitch"] - c1["pitch"]) < 2e-3
              and abs(c0["dist"] - c1["dist"]) < 2e-2 and max(abs(a - b) for a, b in zip(c0["pan"], c1["pan"])) < 2e-2
              and c1["ortho"] == c0["ortho"])
        res["link"] = {"hash": h, "ok": ok}
        if not ok:
            errors.append(f"copied link did not restore the camera: {c0} -> {c1}")

        # ---------------- FOCUS ----------------
        reset()
        h0 = pg.locator("#stage").bounding_box()["height"]
        click("#bFocus")
        pg.wait_for_timeout(250)
        h1 = pg.locator("#stage").bounding_box()["height"]
        hdr = js("() => getComputedStyle(document.querySelector('header')).display")
        if shots:
            pg.screenshot(path=os.path.join(shots, "v71_focus.png"))
        click("#bFocus")
        pg.wait_for_timeout(250)
        h2 = pg.locator("#stage").bounding_box()["height"]
        res["focus"] = {"stageBefore": round(h0), "stageFocus": round(h1), "header": hdr, "stageAfter": round(h2)}
        if not (h1 > h0 + 40 and hdr == "none" and abs(h2 - h0) < 2):
            errors.append(f"focus mode did not give the model the screen and back: {res['focus']}")

        # ---------------- artifact: PNG + CSV go out as-is ----------------
        pa = ctx.new_page()
        pa.add_init_script("""window.__saved=[]; window.claude={use: async (n)=> n==='downloads' ?
            {save: async (o)=>{ window.__saved.push({name:o.filename, size:o.data.size}); }} : null};""")
        pa.on("pageerror", lambda e: errors.append("PAGEERROR(artifact) " + str(e)))
        pa.goto(url)
        pa.wait_for_timeout(2200)
        pa.evaluate("() => document.getElementById('bSnap').click()")
        pa.wait_for_timeout(800)
        if st["runs"]:
            pa.evaluate("() => document.getElementById('dWire').click()")
            pa.wait_for_timeout(600)
            pa.evaluate("() => document.getElementById('bCutList').click()")
            pa.wait_for_timeout(600)
        saved = pa.evaluate("() => window.__saved")
        pa.close()
        res["artifactFiles"] = saved
        names = [s["name"] for s in saved]
        if not any(n.endswith(".png") for n in names) or (st["runs"] and not any(n.endswith(".csv") for n in names)) \
                or any(n.endswith(".zip") for n in names):
            errors.append(f"inside an artifact PNG/CSV did not go out as-is: {saved}")
        b.close()

    res["errors"], res["warnings"], res["ok"] = errors, warnings, not errors
    log(f"\n=== verify v7.1 gates {os.path.basename(path)} ===")
    for k, v in res.items():
        if k not in ("errors", "warnings", "ok"):
            log(f"  v71.{k:<14}: {json.dumps(v)[:400]}")
    for e in errors:
        log("  ERROR " + e)
    log(f"  => {'PASS' if res['ok'] else 'FAIL'}")
    return res


def verify(path, shots=None, floor_ref=None, skip_v4=False):
    if shots:
        os.makedirs(shots, exist_ok=True)
    r4 = {"ok": True} if skip_v4 else V4.verify(path, shots=shots, floor_ref=floor_ref)
    r71 = v71_gates(path, shots=shots)
    ok = r4["ok"] and r71["ok"]
    print(f"\n=== verify_av_v5 {os.path.basename(path)}: v4 {'PASS' if r4['ok'] else 'FAIL'} · "
          f"v7.1 {'PASS' if r71['ok'] else 'FAIL'} => {'PASS' if ok else 'FAIL'}")
    if shots:
        with open(os.path.join(shots, "v5_report.json"), "w") as f:
            json.dump({"ok": ok, "v71": r71, "v4_ok": r4["ok"],
                       "v7": (r4.get("v7") or {})}, f, indent=1, default=str)
    return {"ok": ok, "v4": r4, "v71": r71}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    arg = lambda k: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else None
    r = verify(sys.argv[1], shots=arg("--shots"), floor_ref=arg("--floor-ref"), skip_v4="--skip-v4" in sys.argv)
    sys.exit(0 if r["ok"] else 1)
