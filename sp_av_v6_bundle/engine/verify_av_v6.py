#!/usr/bin/env python3
"""
verify_av_v6.py — v5 (= v3 + v7 + v7.1) + the engine v7.2 gates.

    python3 verify_av_v6.py OUT.html [--shots DIR] [--floor-ref V6.html] [--skip-v5] [--dia part:cx,cy,cz,r[,nx,ny,nz]]

  CHECKS  the Checks dock tab exists and opens; META.checks tiles render when present
  CLASH   the BVH clash scan finds exactly the part pairs an independent brute-force
          triangle sweep finds (same set), sorts them, and a tapped row isolates the pair
  COG     total mass and CoG equal an independent Σ m·x over META (≤ 0.01 g, ≤ 0.01 mm)
          wherever every massed part carries {g, com}; the CoG sits inside its footprint
          at the home pose (margin > 0) and the tip angle = atan(margin / height)
  DIA     circle through 3 points is exact on a known circle; three real taps on a
          cylinder's rim read its diameter (≤ 2 %)
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

import verify_av_v5 as V5  # noqa: E402  (pulls v4 / v3 and the Chromium fallback)
from playwright.sync_api import sync_playwright  # noqa: E402

PHONE = V5.PHONE


def meta_of(path):
    s = pathlib.Path(path).read_text(encoding="utf-8")
    m = re.search(r'<script id="meta" type="application/json">(.*?)</script>', s, re.S)
    return json.loads(m.group(1))


def v72_gates(path, shots=None, dia=None, log=print):
    url = "file://" + str(pathlib.Path(path).absolute())
    errors, res = [], {}
    meta = meta_of(path)
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport=PHONE, device_scale_factor=2, has_touch=True, is_mobile=True)
        pg.on("pageerror", lambda e: errors.append("PAGEERROR " + str(e)))
        pg.on("console", lambda m: errors.append("CONSOLE " + m.text) if m.type == "error" else None)
        pg.goto(url)
        pg.wait_for_timeout(2600)
        js = lambda code: pg.evaluate(code)
        if js("() => !(window.__avV7 && __avV7.ver() >= '7.2')"):
            b.close()
            return {"errors": ["not a v7.2 engine page"], "ok": False}
        js("() => document.getElementById('bReset').click()")
        pg.wait_for_timeout(500)

        # ---------------- CHECKS tab ----------------
        vis = pg.locator("#dCheck").is_visible()
        js("() => document.getElementById('dCheck').click()")
        pg.wait_for_timeout(500)
        title = js("() => document.getElementById('shTitle').textContent")
        tiles = js("() => document.querySelectorAll('#shBody .lbar').length")
        res["checksTab"] = {"visible": vis, "title": title, "metaChecks": len(meta.get("checks") or []), "tiles": tiles}
        if not vis or title != "Checks" or tiles != len(meta.get("checks") or []):
            errors.append(f"Checks tab wrong: {res['checksTab']}")

        # ---------------- CLASH: BVH scan == brute force ----------------
        cl = js("async () => await __avV7.clash()")
        bf = js("() => __avV7.clashBrute()")
        got = sorted("|".join(sorted([c["a"], c["b"]])) for c in cl["pairs"])
        kinds = {}
        for c in cl["pairs"]:
            kinds[c["kind"]] = kinds.get(c["kind"], 0) + 1
        res["clash"] = {"pairs": len(got), "brute": len(bf), "kinds": kinds, "candidates": cl["candidates"], "ms": cl["ms"],
                        "clashes": [(c["a"], c["b"], c["depth"]) for c in cl["pairs"] if c["kind"] == "clash"][:8]}
        if got != bf:
            errors.append(f"clash scan disagrees with brute force: only BVH {sorted(set(got) - set(bf))[:5]}, "
                          f"only brute {sorted(set(bf) - set(got))[:5]}")
        js("() => document.getElementById('bClash').click()")
        pg.wait_for_timeout(300)
        for _ in range(100):
            if js("() => !document.getElementById('bClash').disabled"):
                break
            pg.wait_for_timeout(200)
        rows = js("() => document.querySelectorAll('#clashOut .ckrow').length")
        if rows:
            js("() => document.querySelector('#clashOut .ckrow').click()")
            pg.wait_for_timeout(600)
            sel = js("() => __avState().sel")
            res["clash"]["rowSel"] = sel
            if len(sel) != 2:
                errors.append(f"tapping a clash row did not isolate the pair: {sel}")
        if rows != len(got):
            errors.append(f"clash list shows {rows} rows for {len(got)} pairs")
        if shots:
            pg.screenshot(path=os.path.join(shots, "v72_clash.png"))
        js("() => document.getElementById('bReset').click()")
        js("() => document.getElementById('bShowAll').click()")
        pg.wait_for_timeout(500)

        # ---------------- COG vs an independent sum ----------------
        cg = js("() => __avV7.cog()")
        res["cog"] = cg and {k: (round(v, 3) if isinstance(v, float) else v) for k, v in cg.items() if k != "com"}
        if cg:
            res["cog"]["com"] = [round(v, 3) for v in cg["com"]]
            solid = [p for p in meta["parts"] if p.get("kind") != "wire"]
            massed = [p for p in solid if p.get("mass") and p["mass"].get("g")]
            if massed and all(p["mass"].get("com") for p in massed) and len(massed) == sum(
                    1 for p in solid if (p.get("mass") and p["mass"].get("g")) or (p.get("print") or {}).get("grams")):
                g = sum(p["mass"]["g"] for p in massed)
                com = [sum(p["mass"]["g"] * p["mass"]["com"][i] for p in massed) / g for i in range(3)]
                d = math.dist(com, cg["com"])
                res["cog"]["independent"] = {"g": round(g, 3), "com": [round(v, 3) for v in com], "err_mm": round(d, 5)}
                if abs(g - cg["g"]) > 0.01 or d > 0.01:
                    errors.append(f"CoG disagrees with Σ m·x over META: {res['cog']}")
            if cg["margin"] is None or cg["margin"] <= 0:
                errors.append(f"CoG not inside its footprint at the home pose: {res['cog']}")
            if cg["tipDeg"] is not None and abs(math.degrees(math.atan2(cg["margin"], cg["h"])) - cg["tipDeg"]) > 1e-6:
                errors.append("tip angle is not atan(margin / height)")
            js("() => document.getElementById('dCheck').click()")
            pg.wait_for_timeout(400)
            js("() => { const b=document.getElementById('bCog'); if (b) b.click(); }")
            js("() => document.getElementById('shClose').click()")
            pg.wait_for_timeout(400)
            mk = js("() => { const e=document.querySelector('#marks .cog'); return e && e.style.display!=='none'; }")
            res["cog"]["markerShown"] = mk
            if not mk:
                errors.append("CoG marker not drawn when turned on")
            if shots:
                pg.screenshot(path=os.path.join(shots, "v72_cog.png"))
        else:
            res["cog"] = "no masses in this config"

        # ---------------- DIA: maths, then three real taps on a rim ----------------
        c3 = js("() => { const r=7.5, c=[3,-2,11]; const P=a=>[c[0]+r*Math.cos(a), c[1]+r*Math.sin(a)*Math.cos(0.4), c[2]+r*Math.sin(a)*Math.sin(0.4)];"
                " const o=__avV7.circle3(P(0.3),P(2.2),P(4.4)); return {d:2*o.r, c:o.centre}; }")
        res["circle3"] = c3
        if abs(c3["d"] - 15) > 1e-9 or math.dist(c3["c"], [3, -2, 11]) > 1e-9:
            errors.append(f"circle through 3 points is wrong: {c3}")
        rim = None
        if dia:                                # --dia part:cx,cy,cz,r[,nx,ny,nz] — a real rim on this build
            pid, nums = dia.split(":")
            v = [float(x) for x in nums.split(",")]
            rim = (pid, {"centre": v[:3], "r": v[3], "normal": v[4:7] if len(v) >= 7 else [0, 0, 1]})
        if rim:
            pid, pr = rim
            js("() => document.getElementById('bReset').click()")
            pg.wait_for_timeout(500)
            js("() => __avV7.setDia(true)")
            box = pg.locator("#cv").bounding_box()
            n = pr.get("normal", [0, 0, 1])
            u = [1, 0, 0] if abs(n[0]) < 0.9 else [0, 1, 0]
            # u ⟂ n, v = n × u
            dt = sum(a * b for a, b in zip(u, n))
            u = [a - dt * b for a, b in zip(u, n)]
            L = math.hypot(*u)
            u = [a / L for a in u]
            v = [n[1] * u[2] - n[2] * u[1], n[2] * u[0] - n[0] * u[2], n[0] * u[1] - n[1] * u[0]]
            rr = pr["r"] * 0.92                 # just inside the rim: the tap lands on the face, then snaps out to the rim
            for a in (0.5, 2.6, 4.6):
                w = [pr["centre"][i] + rr * (math.cos(a) * u[i] + math.sin(a) * v[i]) for i in range(3)]
                s = js(f"() => __avV7.project({json.dumps(w)})")
                pg.mouse.click(box["x"] + s[0], box["y"] + s[1])
                pg.wait_for_timeout(350)
            dia = js("() => __avV7.dia()")
            res["dia"] = {"part": pid, "want": 2 * pr["r"], "got": dia and round(dia["d"], 3)}
            if not dia or abs(dia["d"] - 2 * pr["r"]) / (2 * pr["r"]) > 0.02:
                errors.append(f"Ø tool misread the rim: {res['dia']}")
            if shots:
                pg.screenshot(path=os.path.join(shots, "v72_dia.png"))
            js("() => __avV7.setDia(false)")
        b.close()

    res["errors"], res["ok"] = errors, not errors
    log(f"\n=== verify v7.2 gates {os.path.basename(path)} ===")
    for k, v in res.items():
        if k not in ("errors", "ok"):
            log(f"  v72.{k:<12}: {json.dumps(v)[:420]}")
    for e in errors:
        log("  ERROR " + e)
    log(f"  => {'PASS' if res['ok'] else 'FAIL'}")
    return res


def verify(path, shots=None, floor_ref=None, skip_v5=False, dia=None):
    if shots:
        os.makedirs(shots, exist_ok=True)
    r5 = {"ok": True} if skip_v5 else V5.verify(path, shots=shots, floor_ref=floor_ref)
    r72 = v72_gates(path, shots=shots, dia=dia)
    ok = r5["ok"] and r72["ok"]
    print(f"\n=== verify_av_v6 {os.path.basename(path)}: v5 {'PASS' if r5['ok'] else 'FAIL'} · "
          f"v7.2 {'PASS' if r72['ok'] else 'FAIL'} => {'PASS' if ok else 'FAIL'}")
    if shots:
        with open(os.path.join(shots, "v6_report.json"), "w") as f:
            json.dump({"ok": ok, "v72": r72, "v5_ok": r5["ok"]}, f, indent=1, default=str)
    return {"ok": ok, "v5": r5, "v72": r72}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    arg = lambda k: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else None
    r = verify(sys.argv[1], shots=arg("--shots"), floor_ref=arg("--floor-ref"), skip_v5="--skip-v5" in sys.argv, dia=arg("--dia"))
    sys.exit(0 if r["ok"] else 1)
