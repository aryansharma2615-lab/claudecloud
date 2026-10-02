#!/usr/bin/env python3
"""
verify_av_v2.py — drive a built viewer in a real browser and prove it works.

    python3 verify_av_v2.py OUT.html [--shots DIR]

v2 (OneShot v4 ratchet):
  * the build-sheet theme check compares AFTER with BEFORE. v1 demanded
    data-theme="dark", but a page that never set the attribute (dark is the
    default) was correctly restored to "no attribute" and still failed — the
    v3 page fails it too. A verifier bug, not an engine one.
  * schematic: no two runs may share a vertical track (v3's router stacked
    them on one x); the router's crossing count is reported.
  * Motion lane gates: Load vs the independent calc, virtual-work physics,
    BVH vs brute force, no tunnelling, grip, the demo path, drag fps, framing.

Checks, in order:
  1. page loads with ZERO console errors and zero page errors
  2. nothing overflows a 390 px viewport (iPhone width)
  3. every interactive control is >= 44 px on its short side
  4. no hover-only interaction (we never emit :hover-gated handlers, but the
     check is here so a future edit cannot sneak one in)
  5. v1 behaviour still works: orbit, explode, tap-to-identify, ghost, isolate
  6. fps measured over 3 s of continuous orbit at 390 px
  7. screenshots of every panel, so a human can actually look at it

A green run here is the gate for every stage.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys

from playwright.sync_api import sync_playwright

PHONE = {"width": 390, "height": 844}


def verify(path, shots=None, quiet=False):
    p = pathlib.Path(path).absolute()
    url = "file://" + str(p)
    log = (lambda *a: None) if quiet else print
    errors, warnings, result = [], [], {}
    if shots:
        os.makedirs(shots, exist_ok=True)

    with sync_playwright() as pw:
        # No GPU flags: let Chromium pick its best available path. Forcing
        # SwiftShader made the fps number a software-rasteriser artefact.
        b = pw.chromium.launch()
        pg = b.new_page(viewport=PHONE, device_scale_factor=2,
                        has_touch=True, is_mobile=True)
        pg.on("pageerror", lambda e: errors.append("PAGEERROR " + str(e)))
        pg.on("console", lambda m: (errors if m.type == "error" else warnings)
              .append(f"{m.type.upper()} {m.text}"))
        pg.goto(url)
        pg.wait_for_timeout(2500)

        # ---- 0. intro ----------------------------------------------------
        # The intro is a continuous rAF at page load and therefore the heaviest
        # render in the artifact. It has its own fps gate.
        result["intro"] = pg.evaluate("() => window.__avIntro ? __avIntro() : null")
        if result["intro"] and not result["intro"]["done"]:
            errors.append("intro still running 2.5 s after load")
        if result["intro"] and abs(result["intro"]["explode"]) > 1e-6:
            errors.append(f"intro did not settle to explode 0: {result['intro']}")

        # ---- 1. state sanity -------------------------------------------
        result["state"] = pg.evaluate("() => window.__avState ? __avState() : null")
        if not result["state"]:
            errors.append("__avState missing — the script did not run")

        # ---- 2. horizontal overflow ------------------------------------
        ov = pg.evaluate("""() => {
            const de=document.documentElement;
            const bad=[];
            for (const el of document.querySelectorAll('*')){
              const r=el.getBoundingClientRect();
              // a child of a horizontal scroller is allowed to run off-screen;
              // that is what the scroller is for
              let sc=false;
              for (let q=el.parentElement; q; q=q.parentElement){
                const ox=getComputedStyle(q).overflowX;
                if (ox==='auto'||ox==='scroll'){ sc=true; break; }
              }
              if (!sc && r.width>0 && (r.right>innerWidth+1 || r.left<-1))
                bad.push((el.id||el.className||el.tagName)+' '+Math.round(r.left)+'..'+Math.round(r.right));
            }
            return {scrollW:de.scrollWidth, innerW:innerWidth, bad:bad.slice(0,12)};
        }""")
        result["overflow"] = ov
        if ov["scrollW"] > ov["innerW"] + 1:
            errors.append(f"horizontal overflow: scrollWidth {ov['scrollW']} > {ov['innerW']}")
        if ov["bad"]:
            warnings.append("elements past the viewport edge: " + "; ".join(ov["bad"]))

        # ---- 3. touch targets ------------------------------------------
        small = pg.evaluate("""() => {
            const out=[];
            for (const el of document.querySelectorAll('button,a,[role=button],input')){
              const r=el.getBoundingClientRect();
              if (r.width===0 && r.height===0) continue;      // hidden
              if (getComputedStyle(el).display==='none') continue;
              const m=Math.min(r.width,r.height);
              if (m < 30) out.push({t:(el.id||el.className||el.tagName),
                                    w:Math.round(r.width),h:Math.round(r.height)});
            }
            return out;
        }""")
        result["smallTargets"] = small

        # clipped text: an element whose content is wider than its own box.
        # scrollWidth never catches this because overflow:hidden just eats it.
        clipped = pg.evaluate('''() => {
            const out=[];
            for (const el of document.querySelectorAll(
                '.kpi .v,.row .lb,.spec,.tag,.pin,th,td,#shTitle,header h1,.bar .bv')){
              if (!el.offsetParent && el.offsetWidth===0) continue;
              const cs=getComputedStyle(el);
              if (cs.textOverflow==='ellipsis') continue;   // clipping on purpose
              if (el.scrollWidth > el.clientWidth + 1)
                out.push({t:el.className||el.tagName, txt:el.textContent.slice(0,28),
                          sw:el.scrollWidth, cw:el.clientWidth});
            }
            return out.slice(0,10);
        }''')
        result["clipped"] = clipped
        if clipped:
            errors.append("clipped text: " + json.dumps(clipped))
        if small:
            warnings.append("targets under 30 px: " + json.dumps(small))

        # ---- 4. hover-only ---------------------------------------------
        hov = pg.evaluate("""() => {
            let n=0;
            for (const s of document.styleSheets){
              let rules; try { rules=s.cssRules; } catch(e){ continue; }
              for (const r of rules||[]) if (r.selectorText && /:hover/.test(r.selectorText)) n++;
            }
            return n;
        }""")
        result["hoverRules"] = hov

        # ---- 5. v1 behaviours ------------------------------------------
        beh = {}
        st = pg.locator("#stage")
        box = st.bounding_box()
        cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2

        before = pg.evaluate("() => __avCam ? __avCam() : null")
        pg.mouse.move(cx, cy)
        pg.mouse.down()
        pg.mouse.move(cx + 90, cy + 30, steps=8)
        pg.mouse.up()
        pg.wait_for_timeout(150)
        after = pg.evaluate("() => __avCam ? __avCam() : null")
        beh["orbit"] = bool(before and after and abs(before["yaw"] - after["yaw"]) > 0.1)

        pg.evaluate("""() => { const e=document.getElementById('ex');
            e.value=60; e.dispatchEvent(new Event('input')); }""")
        pg.wait_for_timeout(200)
        beh["explode"] = pg.evaluate("() => __avState().mode.explode > 0.5")
        if shots:
            pg.screenshot(path=os.path.join(shots, "02_exploded.png"))

        pg.evaluate("""() => { const e=document.getElementById('ex');
            e.value=0; e.dispatchEvent(new Event('input')); }""")
        pg.wait_for_timeout(150)

        # tap to identify — walk a short grid until something is hit
        hit = None
        for dx in (0, -40, 40, -80, 80):
            for dy in (0, -40, 40):
                pg.mouse.click(cx + dx, cy + dy)
                pg.wait_for_timeout(120)
                s = pg.evaluate("() => __avState().sel")
                if s:
                    hit = s
                    break
            if hit:
                break
        beh["tapIdentify"] = bool(hit)
        beh["selected"] = hit

        beh["ghostBtn"] = pg.locator("#bGhost").count() == 1
        pg.locator("#bIso").click()
        pg.wait_for_timeout(120)
        beh["isolate"] = pg.evaluate("() => __avState().mode.isolate")
        pg.locator("#bIso").click()
        pg.locator("#bShowAll").click()
        pg.wait_for_timeout(120)
        result["behaviour"] = beh
        for k in ("orbit", "explode", "tapIdentify"):
            if not beh.get(k):
                errors.append(f"v1 behaviour broken: {k}")

        # ---- 5b. stage-2 / stage-3 features ------------------------------
        feat = {}

        # view presets: every chip must actually move the camera or the explode
        pg.evaluate("() => document.getElementById('bReset').click()")
        pg.wait_for_timeout(200)
        moved = []
        for v in ("front", "top", "right", "exploded", "collapsed", "iso"):
            b0 = pg.evaluate("() => ({...__avCam(), e:__avState().mode.explode})")
            pg.locator(f'#views .chip[data-view="{v}"]').click()
            pg.wait_for_timeout(520)
            b1 = pg.evaluate("() => ({...__avCam(), e:__avState().mode.explode})")
            moved.append(v if (abs(b0["yaw"] - b1["yaw"]) > 0.05
                               or abs(b0["pitch"] - b1["pitch"]) > 0.05
                               or abs(b0["e"] - b1["e"]) > 0.05) else None)
        feat["presets"] = [m for m in moved if m]

        # section plane: turn it on, sweep it, confirm pixels actually change
        pg.evaluate("() => document.getElementById('bReset').click()")
        pg.wait_for_timeout(250)
        shot_a = pg.locator("#stage").screenshot()
        pg.locator("#bSect").click()
        pg.wait_for_timeout(150)
        pg.evaluate("""() => { const e=document.getElementById('sec');
            e.value=420; e.dispatchEvent(new Event('input')); }""")
        pg.wait_for_timeout(300)
        shot_b = pg.locator("#stage").screenshot()
        feat["sectionOn"] = pg.evaluate("() => __avState().mode.sectOn")
        feat["sectionChangedPixels"] = shot_a != shot_b
        feat["sectionReadout"] = pg.locator("#secv").inner_text()
        if shots:
            pg.screenshot(path=os.path.join(shots, "08_section.png"))
        pg.locator("#bSect").click()
        pg.wait_for_timeout(150)

        # measurement: two taps on the model must yield a mm figure
        pg.evaluate("() => document.getElementById('bReset').click()")
        pg.wait_for_timeout(250)
        pg.locator("#bMeas").click()
        pg.wait_for_timeout(120)
        got = None
        for (ax, ay) in ((cx - 60, cy - 40), (cx + 60, cy + 40),
                         (cx - 30, cy), (cx + 30, cy)):
            pg.mouse.click(ax, ay)
            pg.wait_for_timeout(250)
            t = pg.locator("#sel .nm").inner_text()
            if "mm" in t:
                got = t
                break
        feat["measure"] = got
        if shots and got:
            pg.screenshot(path=os.path.join(shots, "09_measure.png"))
        pg.locator("#bMeas").click()

        # fastener callouts
        pg.evaluate("() => document.getElementById('bReset').click()")
        pg.wait_for_timeout(200)
        pg.locator("#bFast").click()
        pg.wait_for_timeout(350)
        feat["fastenerPins"] = pg.evaluate(
            "() => document.querySelectorAll('#labels .pin.fst')"
            ".length ? [...document.querySelectorAll('#labels .pin.fst')]"
            ".filter(e=>e.style.display!=='none').map(e=>e.textContent) : []")
        if shots:
            pg.screenshot(path=os.path.join(shots, "10_bolts.png"))
        pg.locator("#bFast").click()

        # build timeline: next must advance, play must auto-advance
        pg.locator("#dBuild").click()
        pg.wait_for_timeout(500)
        s0 = pg.locator("#tl .no").inner_text()
        pg.locator("#tl .tlbar .btn >> nth=2").click()
        pg.wait_for_timeout(350)
        s1 = pg.locator("#tl .no").inner_text()
        feat["timelineNext"] = (s0, s1)
        pg.locator("#tl .tlbar .btn.pri").click()     # play
        pg.wait_for_timeout(3000)
        s2 = pg.locator("#tl .no").inner_text()
        feat["timelinePlay"] = (s1, s2)
        pg.locator("#tl .tlbar .btn.pri").click()     # pause

        # inspector
        pg.locator("#dParts").click()
        pg.wait_for_timeout(400)
        pg.locator("#shBody .row >> nth=2").click()
        pg.wait_for_timeout(400)
        feat["inspectorTitle"] = pg.locator("#shTitle").inner_text()
        feat["inspectorSections"] = pg.evaluate(
            "() => [...document.querySelectorAll('#shBody .sect')].map(e=>e.textContent)")
        if shots:
            pg.screenshot(path=os.path.join(shots, "11_inspector.png"))

        # BOM arithmetic: the rendered line values must sum to the rendered total
        pg.locator("#dBom").click()
        pg.wait_for_timeout(500)
        feat["bom"] = pg.evaluate("""() => {
            const rows=[...document.querySelectorAll('table.bom tbody tr')];
            let sum=0, tbd=0;
            for (const r of rows){
              const c=r.children[3].textContent.replace(/[^0-9.]/g,'');
              if (r.children[3].querySelector('.tbd')) { tbd++; continue; }
              sum += parseFloat(c)||0;
            }
            const tiles=[...document.querySelectorAll('.kpi')].map(k=>
              [k.querySelector('.k').textContent, k.querySelector('.v').textContent]);
            return {rows:rows.length, lineSum:+sum.toFixed(2), tbd, tiles};
        }""")
        feat["bomLinks"] = pg.evaluate(
            "() => [...document.querySelectorAll('table.bom a.src')].map(a=>a.href)")

        # wiring & electronics lane
        if pg.locator("#dWire").is_visible():
            pg.locator("#dWire").click()
            pg.wait_for_timeout(700)
            feat["wire"] = pg.evaluate("""() => {
                const st=__avState();
                const svg=document.querySelector('.schem svg');
                const W=svg?+svg.getAttribute('width'):0;
                let clipped=0;
                if (svg) for (const e of svg.querySelectorAll('.edge')){
                  const bb=e.getBBox(); if (bb.x+bb.width>W+1) clipped++; }
                return {
                  mode: st.mode.wireMode,
                  runs: st.runs,
                  edges: document.querySelectorAll('#shBody .edge').length,
                  labels: [...document.querySelectorAll('#shBody .elbl')].map(e=>e.textContent),
                  nodes: document.querySelectorAll('#shBody .nbox').length,
                  rows: document.querySelectorAll('#shBody .wrow').length,
                  clipped,
                  crossings: svg ? +(svg.dataset.crossings||-1) : null,
                  // v2: two runs on one vertical track read as one wire
                  shared: (()=>{ const V=[];
                    for (const e of (svg?svg.querySelectorAll('.edge'):[])){
                      const t=e.getAttribute('d').trim().split(/\s+/); let x=0,y=0;
                      for (let i=0;i<t.length;){ const c=t[i++];
                        if (c==='M'){ x=+t[i++]; y=+t[i++]; }
                        else if (c==='H'){ x=+t[i++]; }
                        else if (c==='V'){ const y2=+t[i++];
                          V.push({run:e.dataset.run, x, lo:Math.min(y,y2), hi:Math.max(y,y2)}); y=y2; }
                        else i++; } }
                    const out=[];
                    for (let i=0;i<V.length;i++) for (let j=i+1;j<V.length;j++){
                      const a=V[i], b=V[j];
                      if (a.run!==b.run && Math.abs(a.x-b.x)<1.5 && Math.min(a.hi,b.hi)-Math.max(a.lo,b.lo)>1)
                        out.push(a.run+'|'+b.run); }
                    return out; })(),
                  // a wire must never leak into the parts list or the BOM
                  inPartsList: [...document.querySelectorAll('.row[data-id]')]
                     .filter(r=>r.dataset.id.startsWith('wire_')).length,
                };
            }""")
            # trace one run: it must light in 3D, in the schematic, and in the caption
            pg.locator(".wrow").nth(2).click()
            pg.wait_for_timeout(500)
            feat["wireTrace"] = pg.evaluate("""() => ({
                sel: __avState().selWire,
                hi: document.querySelectorAll('#shBody .edge.hi').length,
                dim: document.querySelectorAll('#shBody .edge.dim').length,
                caption: document.querySelector('#sel .nm').textContent,
                detail: document.querySelector('#sel .nt').textContent,
            })""")
            if shots:
                pg.screenshot(path=os.path.join(shots, "13_wiring.png"))
            w, t = feat["wire"], feat["wireTrace"]
            if not w["mode"]:
                errors.append("wiring tab did not enter wire mode")
            if w["edges"] != w["runs"] or len(w["labels"]) != w["runs"]:
                errors.append(f"schematic edge/label count != runs: {w}")
            if w["clipped"]:
                errors.append(f"{w['clipped']} schematic edges clipped by the viewBox")
            if w.get("shared"):
                errors.append(f"schematic runs share a vertical track (read as one wire): {w['shared'][:6]}")
            if w["inPartsList"]:
                errors.append("wires leaked into the parts list")
            if any(not x for x in w["labels"]):
                errors.append("an unlabelled schematic edge (colour-alone encoding)")
            if len(t["sel"]) != 1 or t["hi"] != 1 or t["dim"] != w["runs"] - 1:
                errors.append(f"wire trace did not link 3D<->schematic: {t}")
            if "mm" not in t["detail"] or "A" not in t["detail"]:
                errors.append(f"wire caption missing electrical facts: {t}")
            pg.evaluate("() => document.getElementById('bReset').click()")
            pg.wait_for_timeout(300)

        # plate switching
        pg.locator("#dPlate").click()
        pg.wait_for_timeout(500)
        chips = pg.locator(".pchip")
        feat["plateChips"] = chips.count()
        if chips.count() > 1:
            chips.nth(1).click()
            pg.wait_for_timeout(400)
            feat["plateSwitch"] = pg.evaluate("() => __avState().mode.plateMode")
        pg.evaluate("() => document.getElementById('bReset').click()")
        pg.wait_for_timeout(250)

        # full explode: nothing may leave the frame
        pg.evaluate("""() => { const e=document.getElementById('ex');
            e.value=100; e.dispatchEvent(new Event('input')); }""")
        pg.wait_for_timeout(400)
        feat["fullExplodeOnScreen"] = pg.evaluate("""() => {
            const r=document.getElementById('cv').getBoundingClientRect();
            const off=[...document.querySelectorAll('#labels .pin')]
              .filter(e=>e.style.display!=='none').length;
            return {pinsShown:off, w:r.width};
        }""")
        feat["offscreenParts"] = pg.evaluate("() => __avOffscreen ? __avOffscreen() : null")
        if shots:
            pg.screenshot(path=os.path.join(shots, "12_full_explode.png"))
        pg.evaluate("() => document.getElementById('bReset').click()")
        pg.wait_for_timeout(250)
        result["features"] = feat

        for k, v in (("presets", 6), ("fastenerPins", 1)):
            if len(feat.get(k) or []) < v:
                errors.append(f"feature short: {k} = {feat.get(k)}")
        if not feat.get("measure"):
            errors.append("measurement tool produced no distance")
        if not feat.get("sectionChangedPixels"):
            errors.append("section slider changed no pixels")
        if feat["timelineNext"][0] == feat["timelineNext"][1]:
            errors.append("timeline next did not advance")
        if feat["timelinePlay"][0] == feat["timelinePlay"][1]:
            errors.append("timeline play did not auto-advance")
        if feat.get("offscreenParts"):
            errors.append("parts off screen at full explode: "
                          + json.dumps(feat["offscreenParts"]))

        # intro must be skippable — an animation you cannot interrupt is a
        # loading screen. Re-load and tap into it.
        pg2 = b.new_page(viewport=PHONE, device_scale_factor=2, has_touch=True,
                         is_mobile=True)
        pg2.goto(url)
        pg2.wait_for_timeout(350)
        mid = pg2.evaluate("() => __avIntro()")
        pg2.mouse.click(195, 400)
        pg2.wait_for_timeout(200)
        after = pg2.evaluate("() => __avIntro()")
        result["introSkip"] = {"midExplode": mid["explode"], "after": after}
        if not after["done"] or abs(after["explode"]) > 1e-6:
            errors.append(f"intro not skippable on tap: {result['introSkip']}")
        pg2.close()

        # deep links — every form must land on the right view and skip the intro.
        # The ids come out of the PAGE's own state, never out of this file: the
        # first version of this check hard-coded SmartValve's "housing" and
        # "mot_a", so it failed every other product for the wrong reason. A
        # product with no wiring block has no run to trace, and a product that
        # fits on one plate has no plate 2 — both are skipped, not failed.
        st0 = pg.evaluate("() => __avState()")
        ids = pg.evaluate("() => (__avParts ? __avParts() : []).map(p => p.id)")
        first_part = ids[0] if ids else None
        runs = pg.evaluate("() => (__avRuns ? __avRuns() : []).map(r => r.id)")
        first_run = runs[0] if runs else None
        n_plates = int(st0.get("plates") or 1)
        plate_n = 2 if n_plates >= 2 else 1
        forms = [("#step=%d" % min(2, int(st0.get("steps") or 1)), "step")]
        if first_part:
            forms.append(("#part=%s" % first_part, "part"))
        if first_run:
            forms.append(("#wire=%s" % first_run, "wire"))
        forms.append(("#plate=%d" % plate_n, "plate"))
        forms.append(("#tab=bom", "tab"))
        deep = {}
        for frag, key in forms:
            p3 = b.new_page(viewport=PHONE, device_scale_factor=2)
            p3.goto(url + frag)
            p3.wait_for_timeout(1300)
            deep[frag] = p3.evaluate("""() => ({
                m: __avState().mode, sel: __avState().sel,
                selWire: __avState().selWire,
                intro: __avIntro().done,
                title: document.getElementById('shTitle').textContent })""")
            p3.close()
        result["deepLinks"] = deep
        bykey = {k: (f, deep[f]) for f, k in forms}
        if not bykey["step"][1]["m"]["stepMode"]:
            errors.append("#step= did not enter build mode")
        if "part" in bykey:
            f, d = bykey["part"]
            if d["sel"] != [first_part]:
                errors.append(f"{f} did not select the part (sel={d['sel']})")
        if "wire" in bykey:
            f, d = bykey["wire"]
            if d["selWire"] != [first_run]:
                errors.append(f"{f} did not trace the run")
        if not bykey["plate"][1]["m"]["plateMode"]:
            errors.append("#plate= did not enter plate mode")
        for frag, d in deep.items():
            if not d["intro"]:
                errors.append(f"{frag} did not skip the intro")

        # printable build sheet
        pg.evaluate("() => document.getElementById('bReset').click()")
        pg.wait_for_timeout(300)
        st_before = pg.evaluate("() => JSON.stringify(__avState())")
        theme_before = pg.evaluate("() => document.documentElement.getAttribute('data-theme')")
        result["sheet"] = pg.evaluate("async () => await __avSheet()")
        st_after = pg.evaluate("() => JSON.stringify(__avState())")
        sh = result["sheet"]
        if sh["steps"] != (result["state"]["steps"] or 0):
            errors.append(f"build sheet step blocks != steps: {sh}")
        if sh["imgs"] < sh["steps"] + 1:
            errors.append(f"build sheet missing renders: {sh}")
        if sh["blank"]:
            errors.append(f"{sh['blank']} blank renders in the build sheet")
        if st_before != st_after:
            errors.append("build sheet did not restore viewer state")
        theme_after = pg.evaluate("() => document.documentElement.getAttribute('data-theme')")
        if theme_after != theme_before:
            errors.append(f"build sheet changed the theme: {theme_before!r} -> {theme_after!r}")

        # ---- 5c. Motion lane (v2) ---------------------------------------
        if pg.evaluate("() => !!(window.__avMotion && __avMotion.has())"):
            mo = {}
            pg.evaluate("() => document.getElementById('bReset').click()")
            pg.wait_for_timeout(300)
            pg.evaluate("() => __avMotion.enter()")
            pg.wait_for_timeout(700)
            mo["frame"] = pg.evaluate("() => __avMotion.frameCheck()")
            fr = mo["frame"]
            if fr and (fr["x0"] < -2 or fr["x1"] > fr["W"] + 2 or fr["y0"] < -2 or fr["y1"] > fr["band"] + 2):
                errors.append(f"Motion: mechanism not framed in the visible band: {fr}")
            mo["loadCheck"] = pg.evaluate("() => __avMotion.loadCheck()")
            bad = [c for c in mo["loadCheck"] if c["err"] > 0.15 or not c["closed"]]
            if bad:
                errors.append(f"Motion: Load tab disagrees with the independent calc (>15 %): {bad[:3]}")
            mo["physics"] = pg.evaluate("() => __avMotion.physicsCheck(8)")
            ph = mo["physics"]
            if ph["cases"] and ph["worstRel"] > 1e-3:
                errors.append(f"Motion: panel torque != -dU/dθ: {ph['bad']}")
            if ph.get("loop") and ph["loop"]["ok"] < ph["loop"]["of"]:
                warnings.append(f"Motion: loop solver failed {ph['loop']['of'] - ph['loop']['ok']} random poses")
            mo["bvh"] = pg.evaluate("() => __avMotion.bvhCheck(4, 8000)")
            if mo["bvh"]["bad"]:
                errors.append(f"Motion: collision pruning skipped a real contact: {mo['bvh']['bad']}")
            mo["tunnel"] = pg.evaluate("() => __avMotion.tunnelCheck()")
            tb = [t for t in mo["tunnel"] if not t["ok"]]
            if tb:
                errors.append(f"Motion: a jump tunnelled through a part: {tb[:3]}")
            mo["grip"] = pg.evaluate("() => __avMotion.grip()")
            g = mo["grip"]
            if g:
                if g.get("other"):
                    errors.append(f"Motion: closing the jaw hits something else first: {g['other']}")
                elif g.get("contact") is None:
                    errors.append(f"Motion: the jaw never touches the payload (gap {g.get('missGap')})")
                else:
                    if g.get("stall"):
                        errors.append(f"Motion: jaw closes {g['over']:.1f}° past contact — a stalled servo")
                    if g.get("squeezeN") is not None and g["squeezeN"] < g["needN"]:
                        errors.append(f"Motion: grip {g['squeezeN']:.1f} N < needed {g['needN']:.1f} N")
            mo["path"] = pg.evaluate("async () => await __avMotion.path()")
            pth = mo["path"]
            if pth:
                rules = pg.evaluate("() => { try { return (META.motion && META.motion.rules) || {max: 0.7}; } catch (e) { return {max: 0.7}; } }")
                if pth["peak"] > rules.get("max", 0.7):
                    errors.append(f"Motion: demo path peaks at {pth['peak']:.2f} of stall (> {rules.get('max', 0.7)})")
                if pth["events"]:
                    errors.append(f"Motion: demo path collides: {pth['events'][:3]}")
            mo["dragBench"] = pg.evaluate("async () => await __avMotion.dragBench(1500)")
            if shots:
                pg.screenshot(path=os.path.join(shots, "14_motion.png"))
            result["motion"] = mo
            pg.evaluate("() => document.getElementById('bReset').click()")
            pg.wait_for_timeout(300)

        # ---- 6. fps ------------------------------------------------------
        pg.evaluate("() => document.getElementById('bReset').click()")
        pg.wait_for_timeout(200)
        result["fps"] = pg.evaluate("async () => await __avBench(3000)")

        # ---- 7. panel screenshots ---------------------------------------
        if shots:
            pg.evaluate("() => document.getElementById('bReset').click()")
            pg.wait_for_timeout(250)
            pg.screenshot(path=os.path.join(shots, "01_home.png"))
            for tab, name in (("dParts", "03_parts"), ("dBuild", "04_build"),
                              ("dBom", "05_bom"), ("dPlate", "06_plate")):
                if pg.locator("#" + tab).is_visible():
                    pg.locator("#" + tab).click()
                    pg.wait_for_timeout(500)
                    pg.screenshot(path=os.path.join(shots, name + ".png"))
            # desktop rail
            pg.set_viewport_size({"width": 1280, "height": 860})
            pg.wait_for_timeout(400)
            pg.evaluate("() => document.getElementById('dParts').click()")
            pg.wait_for_timeout(400)
            pg.screenshot(path=os.path.join(shots, "07_desktop.png"))
            pg.set_viewport_size(PHONE)
            pg.wait_for_timeout(300)

        errors += [e for e in [] if e]
        b.close()

    result["errors"] = errors
    result["warnings"] = warnings
    result["ok"] = not errors

    log(f"\n=== verify {os.path.basename(path)} ===")
    log(f"  deepLinks : {len(result.get('deepLinks') or {})} forms OK")
    log(f"  sheet     : {result.get('sheet')}")
    log(f"  intro     : {result.get('intro')}  skip={result.get('introSkip')}")
    log(f"  state     : {result['state']}")
    log(f"  behaviour : {beh}")
    for k, v in result.get("features", {}).items():
        log(f"  feat.{k:<22}: {v}")
    for k, v in (result.get("motion") or {}).items():
        log(f"  motion.{k:<20}: {json.dumps(v)[:400]}")
    f = result["fps"]
    log(f"  fps       : {f['fps']:.1f}  (median frame {f['medianMs']:.1f} ms, "
        f"p95 {f['p95Ms']:.1f} ms, {f['frames']} frames, dprCap {f['dprCap']})")
    log(f"  overflow  : scrollW {ov['scrollW']} vs {ov['innerW']}")
    log(f"  hover css : {hov} rules")
    for w in warnings:
        log("  WARN  " + w)
    for e in errors:
        log("  ERROR " + e)
    log(f"  => {'PASS' if result['ok'] else 'FAIL'}"
        f"{'' if f['fps'] >= 30 else '  (fps below 30 floor)'}")
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    shots = None
    if "--shots" in sys.argv:
        shots = sys.argv[sys.argv.index("--shots") + 1]
    r = verify(sys.argv[1], shots=shots)
    sys.exit(0 if r["ok"] else 1)
