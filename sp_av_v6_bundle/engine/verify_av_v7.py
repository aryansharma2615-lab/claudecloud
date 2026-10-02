#!/usr/bin/env python3
"""
verify_av_v7.py — v6 (= v3 + v7 + v7.1 + v7.2) + the engine v7.3 gates.

    python3 verify_av_v7.py OUT.html [--shots DIR] [--floor-ref V6.html] [--skip-v6] [--dia ...]

  GAP     the BVH gap between two parts = a brute-force every-triangle distance (≤ 1e-6 mm);
          two real taps in Gap mode draw the dimension and report it
  TIGHT   every listed gap is real (re-measured brute force for the three tightest), > 0,
          < 2 mm, sorted ascending
  BOM     the CSV has one row per BOM line, and its line totals sum to the tab's own
          "Unit cost ×1" tile (≤ 0.01)
  SECTION in ortho, dragging the handle 40 px moves the cut by 40 / (px per mm) (≤ 2 %); in
          both projections the handle ends under the pointer (≤ 3 px)
"""
from __future__ import annotations

import csv
import io
import json
import math
import os
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import verify_av_v6 as V6  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

PHONE = V6.PHONE


def v73_gates(path, shots=None, log=print):
    url = "file://" + str(pathlib.Path(path).absolute())
    errors, res = [], {}
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport=PHONE, device_scale_factor=2, has_touch=True, is_mobile=True)
        pg.on("pageerror", lambda e: errors.append("PAGEERROR " + str(e)))
        pg.on("console", lambda m: errors.append("CONSOLE " + m.text) if m.type == "error" else None)
        pg.goto(url)
        pg.wait_for_timeout(2600)
        js = lambda code: pg.evaluate(code)
        if js("() => !(window.__avV7 && __avV7.ver() >= '7.3')"):
            b.close()
            return {"errors": ["not a v7.3 engine page"], "ok": False}
        reset = lambda: (js("() => document.getElementById('bReset').click()"), pg.wait_for_timeout(500))
        reset()
        parts = {p["id"]: p for p in js("() => __avParts()")}

        # ---------------- TIGHT + GAP vs brute force ----------------
        t = js("async () => await __avV7.tight()")
        res["tight"] = t
        ds = [g["d"] for g in t["first"]]
        if ds != sorted(ds) or any(not (0.005 <= d < 2) for d in ds):
            errors.append(f"tight gaps not real / not sorted: {t['first']}")
        checks = []
        for g in t["first"][:3]:
            bvh = js(f"() => __avV7.gap('{g['a']}','{g['b']}').d")
            bru = js(f"() => __avV7.gapBrute('{g['a']}','{g['b']}')")
            checks.append({"a": g["a"], "b": g["b"], "bvh": round(bvh, 6), "brute": round(bru, 6)})
            if abs(bvh - bru) > 1e-6:
                errors.append(f"gap BVH {bvh} != brute force {bru} for {g['a']}↔{g['b']}")
        res["gapVsBrute"] = checks

        # ---------------- GAP tool: two real taps ----------------
        js("() => document.getElementById('shClose').click()")
        pg.wait_for_timeout(300)
        box = pg.locator("#cv").bounding_box()
        hits = {}
        for fy in (0.3, 0.36, 0.42, 0.48, 0.54, 0.6, 0.66):
            for fx in (0.3, 0.4, 0.5, 0.6, 0.7):
                w = js(f"() => __avV7.worldAt({box['width']*fx},{box['height']*fy})")
                if w["hit"] and w["part"] not in hits and parts.get(w["part"], {}).get("kind") != "screw":
                    hits[w["part"]] = (box["width"] * fx, box["height"] * fy)
            if len(hits) >= 2:
                break
        if len(hits) >= 2:
            (a, pa), (bb, pb) = list(hits.items())[:2]
            js("() => __avV7.setGap(true)")
            pg.mouse.click(box["x"] + pa[0], box["y"] + pa[1])
            pg.wait_for_timeout(350)
            pg.mouse.click(box["x"] + pb[0], box["y"] + pb[1])
            pg.wait_for_timeout(500)
            cap = js("() => document.querySelector('#sel .nm').textContent")
            want = js(f"() => __avV7.gap('{a}','{bb}').d")
            shown = js("() => { const l=document.querySelector('#leads .gapln'); return l && l.style.display!=='none'; }")
            res["gapTool"] = {"a": a, "b": bb, "caption": cap, "d": round(want, 3), "lineShown": shown}
            if f"{want:.2f} mm" not in cap:
                errors.append(f"Gap tool caption {cap!r} != measured {want:.2f} mm")
            if want > 0 and not shown:
                errors.append("Gap tool did not draw its dimension line")
            if shots:
                pg.screenshot(path=os.path.join(shots, "v73_gap.png"))
            js("() => __avV7.setGap(false)")
        else:
            errors.append("Gap tool: could not find two parts on screen")
        reset()

        # ---------------- BOM CSV sums to the tab's total ----------------
        js("() => document.getElementById('dBom').click()")
        pg.wait_for_timeout(500)
        tile = js("() => { const k=[...document.querySelectorAll('.kpi')].find(k=>/Unit cost/.test(k.querySelector('.k').textContent)); return k ? k.querySelector('.v').textContent : null; }")
        rows = list(csv.DictReader(io.StringIO(js("() => __avV7.bomCSV()"))))
        nlines = js("() => document.querySelectorAll('table.bom tbody tr').length")
        total = sum(float(r["line"]) for r in rows if r["line"] not in ("", "TBD"))
        tv = float(re.sub(r"[^0-9.]", "", tile)) if tile else None
        res["bomCsv"] = {"rows": len(rows), "tableRows": nlines, "csvTotal": round(total, 2), "tile": tile}
        if len(rows) != nlines:
            errors.append(f"BOM CSV has {len(rows)} rows, the table {nlines}")
        if tv is None or abs(total - tv) > 0.011:
            errors.append(f"BOM CSV lines sum to {total:.2f}, the tab says {tile}")
        btn = js("() => !!document.getElementById('bBomCsv')")
        if not btn:
            errors.append("no BOM CSV button on the BOM tab")
        reset()

        # ---------------- SECTION handle ----------------
        # ortho: px per mm along the axis is constant, so the drag must move the cut exactly px / (px per mm);
        # persp: it is not, so the test is that the handle stays under the finger
        js("() => document.getElementById('shClose').click()")
        js("() => document.getElementById('bSect').click()")
        pg.wait_for_timeout(300)
        sb = pg.locator("#stage").bounding_box()
        sec = {}
        for proj in ("ortho", "persp"):
            js(f"() => __avV7.setOrtho({'true' if proj == 'ortho' else 'false'})")
            js("() => { const e=document.getElementById('sec'); e.value=500; e.dispatchEvent(new Event('input')); }")
            pg.wait_for_timeout(200)
            h0 = js("() => __avV7.secHandle()")
            vis = js("() => getComputedStyle(document.querySelector('.sechandle')).display !== 'none'")
            if not (h0 and vis):
                errors.append(f"section handle not shown with the section on ({proj}): {h0}")
                continue
            ax = h0["ax"]
            L = math.hypot(*ax)
            ux, uy = ax[0] / L, ax[1] / L
            px = 40
            x0, y0 = sb["x"] + h0["x"], sb["y"] + h0["y"]
            pg.mouse.move(x0, y0)
            pg.mouse.down()
            pg.mouse.move(x0 + ux * px, y0 + uy * px, steps=8)
            pg.mouse.up()
            pg.wait_for_timeout(200)
            h1 = js("() => __avV7.secHandle()")
            off = math.hypot(sb["x"] + h1["x"] - (x0 + ux * px), sb["y"] + h1["y"] - (y0 + uy * px))
            r = {"wantMm": round(px / L, 2), "gotMm": round(h1["v"] - h0["v"], 2), "handleOffPx": round(off, 2)}
            sec[proj] = r
            if proj == "ortho" and abs(r["gotMm"] - r["wantMm"]) / r["wantMm"] > 0.02:
                errors.append(f"section handle (ortho) moved the cut {r['gotMm']} mm for {r['wantMm']} mm of drag")
            if off > 3:
                errors.append(f"section handle ({proj}) left the finger behind by {off:.1f} px")
        res["section"] = sec
        js("() => __avV7.setOrtho(false)")
        if shots:
            pg.screenshot(path=os.path.join(shots, "v73_section.png"))
        js("() => document.getElementById('bSect').click()")
        b.close()

    res["errors"], res["ok"] = errors, not errors
    log(f"\n=== verify v7.3 gates {os.path.basename(path)} ===")
    for k, v in res.items():
        if k not in ("errors", "ok"):
            log(f"  v73.{k:<12}: {json.dumps(v)[:420]}")
    for e in errors:
        log("  ERROR " + e)
    log(f"  => {'PASS' if res['ok'] else 'FAIL'}")
    return res


def verify(path, shots=None, floor_ref=None, skip_v6=False, dia=None):
    if shots:
        os.makedirs(shots, exist_ok=True)
    r6 = {"ok": True} if skip_v6 else V6.verify(path, shots=shots, floor_ref=floor_ref, dia=dia)
    r73 = v73_gates(path, shots=shots)
    ok = r6["ok"] and r73["ok"]
    print(f"\n=== verify_av_v7 {os.path.basename(path)}: v6 {'PASS' if r6['ok'] else 'FAIL'} · "
          f"v7.3 {'PASS' if r73['ok'] else 'FAIL'} => {'PASS' if ok else 'FAIL'}")
    if shots:
        with open(os.path.join(shots, "v7_report.json"), "w") as f:
            json.dump({"ok": ok, "v73": r73, "v6_ok": r6["ok"]}, f, indent=1, default=str)
    return {"ok": ok, "v6": r6, "v73": r73}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    arg = lambda k: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else None
    r = verify(sys.argv[1], shots=arg("--shots"), floor_ref=arg("--floor-ref"), skip_v6="--skip-v6" in sys.argv, dia=arg("--dia"))
    sys.exit(0 if r["ok"] else 1)
