#!/usr/bin/env python3
"""
verify_av_v8.py — v7 (= v3 + v7 … v7.3) + the engine v7.4 gates.

    python3 verify_av_v8.py OUT.html [--shots DIR] [--floor-ref V6.html] [--skip-v7] [--dia …]
                            [--ang x,y,z:x,y,z:x,y,z:deg]

  ANGLE   angle-at-B is exact on known triangles; with --ang, three real taps near three
          mesh corners read the known angle (≤ 0.5°)
  HISTORY ◀ returns to the previous settled view and ▶ comes back (yaw / pitch / dist / pan)
  SWIPE   a 150 px left swipe on the step card goes to the next step, right goes back
  WIRE    "Wire to buy" = Σ (routed + 40 mm) × conductors per gauge, from the page's own runs
  KEYS    "?" opens the key map, Esc closes it
"""
from __future__ import annotations

import json
import math
import os
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import verify_av_v7 as V7  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

PHONE = V7.PHONE


def v74_gates(path, shots=None, ang=None, log=print):
    url = "file://" + str(pathlib.Path(path).absolute())
    errors, res = [], {}
    meta = V7.V6.meta_of(path)
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport=PHONE, device_scale_factor=2, has_touch=True, is_mobile=True)
        pg.on("pageerror", lambda e: errors.append("PAGEERROR " + str(e)))
        pg.on("console", lambda m: errors.append("CONSOLE " + m.text) if m.type == "error" else None)
        pg.goto(url)
        pg.wait_for_timeout(2600)
        js = lambda code: pg.evaluate(code)
        if js("() => !(window.__avV7 && __avV7.ver() >= '7.4')"):
            b.close()
            return {"errors": ["not a v7.4 engine page"], "ok": False}
        reset = lambda: (js("() => document.getElementById('bReset').click()"), pg.wait_for_timeout(500))
        reset()

        # ---------------- ANGLE ----------------
        a90 = js("() => __avV7.angleAt([10,0,0],[0,0,0],[0,7,0])")
        a60 = js("() => __avV7.angleAt([1,0,0],[0,0,0],[0.5,Math.sqrt(3)/2,0])")
        res["angleMath"] = [a90, a60]
        if abs(a90 - 90) > 1e-9 or abs(a60 - 60) > 1e-9:
            errors.append(f"angle maths wrong: {a90}, {a60}")
        if ang:
            ps = [[float(x) for x in t.split(",")] for t in ang.split(":")[:3]]
            want = float(ang.split(":")[3])
            js("() => document.getElementById('shClose').click()")
            pg.wait_for_timeout(300)
            js("() => __avV7.setAng(true)")
            box = pg.locator("#cv").bounding_box()
            ctr = [sum(p[i] for p in ps) / 3 for i in range(3)]
            for p in ps:
                q = [p[i] + (ctr[i] - p[i]) * 0.03 for i in range(3)]      # a hair inside the corner: lands on the face, snaps to the corner
                s = js(f"() => __avV7.project({json.dumps(q)})")
                pg.mouse.click(box["x"] + s[0], box["y"] + s[1])
                pg.wait_for_timeout(350)
            got = js("() => __avV7.angle()")
            res["angleTaps"] = {"want": want, "got": got}
            if got is None or abs(got - want) > 0.5:
                errors.append(f"∠ tool read {got} for a known {want}°")
            if shots:
                pg.screenshot(path=os.path.join(shots, "v74_angle.png"))
            js("() => __avV7.setAng(false)")
            reset()

        # ---------------- HISTORY ----------------
        reset()
        pg.wait_for_timeout(700)
        c0 = js("() => __avV7.history().now")
        pt = js("() => __avV7.cubePoint('FRONT',1,1)")
        pg.mouse.click(pt[0], pt[1])
        pg.wait_for_timeout(1100)
        c1 = js("() => __avV7.history().now")
        js("() => __avV7.back()")
        pg.wait_for_timeout(800)
        cb = js("() => __avV7.history().now")
        js("() => __avV7.fwd()")
        pg.wait_for_timeout(800)
        cf = js("() => __avV7.history().now")
        same = lambda a, b: abs(a["yaw"] - b["yaw"]) < 2e-3 and abs(a["pitch"] - b["pitch"]) < 2e-3 and abs(a["dist"] - b["dist"]) < 0.05
        res["history"] = {"backOk": same(cb, c0), "fwdOk": same(cf, c1), "n": js("() => __avV7.history().n")}
        if not (same(cb, c0) and same(cf, c1)):
            errors.append(f"view history did not step back / forward: {res['history']}")

        # ---------------- SWIPE ----------------
        reset()
        st = js("() => __avState()")
        if st["steps"] >= 3:
            js("() => document.getElementById('dBuild').click()")
            pg.wait_for_timeout(500)
            js("() => document.querySelector(\"#tlTrack .tick[data-n='2']\").click()")
            pg.wait_for_timeout(300)
            h2 = pg.locator("#tl h2").bounding_box()
            y = h2["y"] + h2["height"] / 2
            def swipe(x0, x1):
                pg.mouse.move(x0, y); pg.mouse.down(); pg.mouse.move(x1, y, steps=6); pg.mouse.up(); pg.wait_for_timeout(400)
                return js("() => document.querySelector('#tl .no').textContent")
            nl = swipe(320, 140)
            nr = swipe(140, 320)
            res["swipe"] = {"left": nl, "right": nr}
            if not nl.startswith("Step 03") or not nr.startswith("Step 02"):
                errors.append(f"swipe did not change step: {res['swipe']}")
            reset()

        # ---------------- WIRE TO BUY ----------------
        runs = (meta.get("wiring") or {}).get("runs") or []
        if runs:
            want = {}
            for r in runs:
                g = r.get("gauge") or f"{r.get('awg')} AWG"
                want[g] = want.get(g, 0) + ((r.get("length_mm") or 0) + 40) * (r.get("conductors") or 1)
            got = {w["gauge"]: w["mm"] for w in js("() => __avV7.wireToBuy()")}
            res["wireToBuy"] = {"got_mm": got, "want_mm": {k: round(v) for k, v in want.items()}}
            if set(got) != set(want) or any(abs(got[k] - want[k]) > 1 for k in want):
                errors.append(f"wire to buy wrong: {res['wireToBuy']}")
            js("() => document.getElementById('dWire').click()")
            pg.wait_for_timeout(500)
            if not js("() => !!document.getElementById('wireBuy')"):
                errors.append("no 'Wire to buy' card on the Wiring tab")
            reset()

        # ---------------- KEYS ----------------
        pg.keyboard.press("?")
        pg.wait_for_timeout(150)
        k1 = js("() => __avV7.keys()")
        if shots:
            pg.screenshot(path=os.path.join(shots, "v74_keys.png"))
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(150)
        k2 = js("() => __avV7.keys()")
        res["keys"] = {"open": k1, "afterEsc": k2}
        if not k1 or k2:
            errors.append(f"key map did not open / close: {res['keys']}")
        b.close()

    res["errors"], res["ok"] = errors, not errors
    log(f"\n=== verify v7.4 gates {os.path.basename(path)} ===")
    for k, v in res.items():
        if k not in ("errors", "ok"):
            log(f"  v74.{k:<12}: {json.dumps(v)[:420]}")
    for e in errors:
        log("  ERROR " + e)
    log(f"  => {'PASS' if res['ok'] else 'FAIL'}")
    return res


def verify(path, shots=None, floor_ref=None, skip_v7=False, dia=None, ang=None):
    if shots:
        os.makedirs(shots, exist_ok=True)
    r7 = {"ok": True} if skip_v7 else V7.verify(path, shots=shots, floor_ref=floor_ref, dia=dia)
    r74 = v74_gates(path, shots=shots, ang=ang)
    ok = r7["ok"] and r74["ok"]
    print(f"\n=== verify_av_v8 {os.path.basename(path)}: v7 {'PASS' if r7['ok'] else 'FAIL'} · "
          f"v7.4 {'PASS' if r74['ok'] else 'FAIL'} => {'PASS' if ok else 'FAIL'}")
    if shots:
        with open(os.path.join(shots, "v8_report.json"), "w") as f:
            json.dump({"ok": ok, "v74": r74, "v7_ok": r7["ok"]}, f, indent=1, default=str)
    return {"ok": ok, "v7": r7, "v74": r74}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    arg = lambda k: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else None
    r = verify(sys.argv[1], shots=arg("--shots"), floor_ref=arg("--floor-ref"), skip_v7="--skip-v7" in sys.argv,
               dia=arg("--dia"), ang=arg("--ang"))
    sys.exit(0 if r["ok"] else 1)
