# AV v8 — research, product check, UX architecture

Skills run: `/sp-research-first-design`, `/sp-research`, `/marketing:competitive-brief` (inline), `/sp-go-no-go`, `/blueprintio` (bar for completeness).
Date: 2026-10-03.

## 1. What proven viewers do (and what v7 lacked)

| Viewer | What it does well | v7 had it? | v8 answer |
|---|---|---|---|
| Onshape view-only toolbar ([help](https://cad.onshape.com/help/Content/Collaboration/using_the_view_only_toolbar.htm)) | exploded views, named positions, section view from the view cube on mobile | explode, section, cube | **phases = named positions** (LOAD / FIT / SECURE / TEST), each a shareable URL |
| ExplodeView (three.js, [jsdelivr](https://www.jsdelivr.com/package/npm/explodeview)) | explode animation, measurements, section cuts, "manufacturing tools" | yes (no tolerance view) | **tolerance rings coloured from a measured printer profile** — none of these do that |
| Obsidian STEP viewer ([plugin](https://community.obsidian.md/plugins/step-viewer)) | click-two-points distance with X/Y/Z components, view cube, edges | measure | **caliper tool** (animated jaws, source-labelled reading) |
| Codulon STEP Viewer ([WP](https://cn.wordpress.org/plugins/codulon-step-viewer-lite/)) | part list, isolate / show all, section, explode, screenshots | yes | **parts tree with eye toggles** (Assembly › Part › Feature) |
| 3DViewer.net (open source) | pure client-side WebGL, many formats | single-file engine | same: zero network, one HTML |
| Fusion web viewer / MakerWorld preview | pretty turntable, print-profile metadata | look + print panel | **real G-code numbers** (`SLICER`) in the print panel |

**The gap no viewer fills:** every number is decoration. None says *where a number came from*, none
computes whether the part survives the load, none ties a hole colour to how THIS printer prints holes.
That is the v8 wedge: **source-labelled engineering, live hand calcs, measured tolerances.**

## 2. Viewer UX architectures (scored 1–5, weights in brackets)

| Architecture | Phone (3) | Guided for a first-timer (3) | Expert speed (2) | Artifact-safe single file (3) | Total |
|---|---|---|---|---|---|
| A. Tabs only (v7: Parts · Build · Motion · BOM · Wiring · Plate · Checks) | 4 | 2 | 5 | 5 | 47 |
| **B. Phase stepper over the tabs (LOAD → FIT → SECURE → TEST), tabs stay** | 4 | 5 | 4 | 5 | **56** ✅ |
| C. Wizard that hides the tabs (one screen per step) | 5 | 5 | 1 | 5 | 47 |

Pick **B**: the stepper tells a client the story in four taps; the tabs keep every v7 tool one tap away
(zero regression). Each phase is a URL-hash state, so a phase is also a link you send.

## 3. GO / NO-GO — "AV as a service" for makers + Kickstarter creators

| Lane | Verdict | One-liner |
|---|---|---|
| Interactive AV for hardware Kickstarters | ⚠️ GO-IF | price under agency 3D sites, sell the *engineering proof* |
| AV bundled with SP prototype jobs | ✅ GO | every SP print job ships an AV — free differentiator |
| Self-serve AV builder (SaaS) | ❌ NO-GO (for now) | needs a CAD-import pipeline + hosting |
| Content: build reels from AV captures | ✅ GO | the TEST heatmap + stall warning is a 30-s reel |

- **Market / price:** crowdfunding 3D microsites run **$3,000–8,000**; basic rotate/zoom viewers from **~$400**; configurators **$170–350/month** ([svilenkovic](https://www.svilenkovic.com/3d/crowdfunding-3d-website), [Contra/Spline](https://contra.com/s/6cE7BBqe-spline-3-d-product-viewer)). Claimed 30–50 % conversion lift is a vendor number — treat as marketing, not data.
- **Buyer:** first-time hardware founders who need a backer to trust that the thing goes together and survives.
- **SP's edge:** nobody else ships source-labelled checks + measured tolerances + a build sequence in one link.
- **The wall:** CAD comes in as STEP from strangers → part split, joints and the engineering YAML still need an engineer (hours, not minutes).
- **Lane 1 next 3 steps:** (1) publish the Servo Mount AV as the portfolio piece; (2) one free AV for a local maker in exchange for a testimonial; (3) price **$450 basic / $1,200 with TEST + checks**.
- **NO-GO flip (SaaS):** X = a STEP → parts + joints auto-splitter, Y = YAML templates per mechanism type, Z = 10 paid service jobs proving demand.
- **Stepping stone (ship this year):** every SP print job gets a free LOAD + SECURE AV; TEST is the upsell.

Lessons: **(a)** *Source labelling* is a trust product: a number with "ASSUMED" next to it is more credible than a confident number with nothing. **(b)** *The servo is the fuse:* when a cheap actuator stalls before the bracket breaks, the failure is safe and recoverable — that is design intent, not luck.
Skill tree: 3D printing & design (tolerances, DFM), electronics (servo torque / stall current), content (reel).

## 4. Corrections applied (from the prompt's §3)
SG90 pocket from measured-later dims (not 25×25) · Ender 3 S1 Pro + PrusaSlicer-CLI G-code (no MK4) ·
PETG default (no CF on brass) · hole coupon + tolerance profile (not a made-up 3.30→3.02) · iron temp from
the `/sp-print-dfm` table (240 °C PETG) · torque guides labelled ASSUMED · hand-calc heatmap (σ = M·c/I,
Kt, von Mises) instead of a decorative shader · lever arm stated, compared to SG90 stall · Motion lane +
min-jerk instead of a physics library · 60 / 30 fps targets + perf HUD · <50k triangles + LOD · 0.6 mm
emboss · studio = the v7 three-light rig + contact shadow (no external HDRI, no three.js — the engine is
hand-written WebGL2 and stays one file).
