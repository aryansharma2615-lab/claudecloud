# AV engine — CHECKPOINT

**Updated:** 2026-09-13
**Build state:** ✅ GREEN. `smartvalve_v3_artifact_v2.html` builds, opens, and
passes the full suite (`verify_av.py` → PASS, 46.4 fps, 0 console errors).
Nothing is mid-edit.

## Rebuild / re-verify

```bash
cd ~/Claude/SmartValve/v3_viewer
python3 make_av_config.py                                    # CAD -> av_config.json
python3 ~/Claude/AV/build_av.py av_config.json smartvalve_v3_artifact_v2.html
python3 ~/Claude/AV/verify_av.py smartvalve_v3_artifact_v2.html --shots ./shots
```

---

## DONE

### v2 baseline (previous session)
All 12 AV_V2_PROMPT features, engine extracted to `~/Claude/AV/`, SmartValve
generated from a config, v1 geometry parity proved byte-for-byte, 3MF written +
self-audited, BOM priced from real listings. See `AV_FEATURES.md`.

### Reconciliation against `/sp-assembly-viewer` (this session)
The three SP skills **were genuinely absent from disk** at the start of this
session — confirmed by filesystem search, and `/reload-skills` cannot be invoked
by the assistant. They became available mid-session and were then read in full
(`/cad-assembly-viewer`, `/sp-assembly-viewer`, `/blueprintio`, `/dataviz`).
Result of reconciling:

| # | Finding | Fix | Verified |
|---|---|---|---|
| R1 | **Print-by-object hazard audit assumed multi-plate sequential hardware.** The Ender 3 S1 Pro + Creality Print prints the whole plate at once, single gantry — the toolhead never crosses a finished part. The red "the gantry will hit them" box was **false on this machine**. | Gated the entire audit behind `printer.sequential` (default **false**). `gantry`/`skirt` now default `None` and are never shown unless opted in. Replaced with what is true: "prints as ONE job, all objects together". | plate panel re-shot |
| R2 | Engine config shape differed from the shape documented in `/sp-assembly-viewer` (`print.supports` bool, per-part `fasteners`, per-part `bom`). | Added `normalise_sp()` in `build_av.py`. The documented SP shape now builds **verbatim**; the engine's richer shape is kept as a superset. | synthetic SP-shape config built: 14 parts / 18 callouts / 13 priced |
| R3 | `/dataviz` is **mandatory** before any BOM tile or chart and had not been read. Audit found: chart marks used the UI accent tokens, which sit at OKLCH L 0.745/0.768 — **outside** the dark categorical band [0.48, 0.67] → lightness check FAIL. Also no legend for a 2-series chart, pill-shaped bars floating off their baseline, and no interaction. | Added dedicated `--series-1 #009686` / `--series-2 #a47800`, snapped to the same hues at L 0.60. **Validator run, not eyeballed** — all six checks PASS in *both* modes. Added the legend, anchored marks to the baseline with a 4 px data end, made bars tappable (tap not hover). | `validate_palette.js` PASS ×2; computed colours read back from the live page |
| R4 | SP convention: publish as an artifact. The publisher supplies its own `<!doctype>/<head>/<body>`, so the standalone file would nest a second document. | `build_av.py` now emits `*_fragment.html` alongside the standalone. | fragment asserted free of all wrapper tags |
| R5 | Scrim covered the header → theme toggle unreachable while a panel was open (same class as the earlier dock bug). | Header raised above the scrim, as the dock already was. | clicked with sheet open, OK |

### ✅ STAGE 1 — Wiring & electronics lane (this session)

Shipped and verified. `AV_FEATURES.md` §13 and `CONFIG_SCHEMA.md` → **wiring**.

- `av_geom.tube()` — swept tube along a polyline, **parallel-transport frames**
  (a fixed-up frame flips and turns the tube inside out the moment a run goes
  vertical, which two of these runs do) and mitred corners. Verified watertight,
  positive volume, and a straight run matches the 8-gon ideal exactly.
- `build_av.build_wiring()` — runs → tubes packed into the **same int16 buffer**
  as the parts, carrying `kind:"wire"`. Pick / ghost / isolate / section work on
  a cable for free. 11 runs = 880 triangles.
- Real electrical facts per run from a standards AWG table: length from the
  routed polyline, DC resistance, voltage drop (V and %), and an `undersized`
  flag against the gauge's chassis rating. Gauge is sized off the motor's
  **5.5 A stall** (Pololu 4745 published figure), not its 0.2 A running current.
- 2D pinout schematic: node boxes, pin rows, coloured pin dots, orthogonally
  routed edges, direct net labels. Tap a node for what it *is* in plain words.
- Bidirectional highlight across all three surfaces (3D tube ↔ schematic edge ↔
  run list), plus per-kind filter chips.
- Verification extended: edge/label counts match run count, zero clipped edges,
  zero unlabelled edges, no wire leaks into the parts list, and a trace must
  light exactly one edge and dim the rest.

**Design finding surfaced by building it:** the motor runs need a lid
pass-through at ~(55, −30, 66) that **v3 does not have** — the CAD cuts a gland
in the housing wall only. Flagged in the run notes. Real output of the feature.

**Verified:** full suite PASS · 45.4 fps · 0 console errors · 25 parts (14 + 11
runs) · 11 edges / 11 labels / 5 nodes / 0 clipped.

### ✅ STAGE 2 — Animation polish (this session)

Shipped and verified. `AV_FEATURES.md` §14.

- **Auto-explode intro**: apart → hold → settle, ~2 s, yaw drift, skipped by any
  input and by `prefers-reduced-motion`. Verified skippable mid-flight (caught
  at explode 0.98, jumped to 0).
- **Every camera move eased** through one `glide()`/`animate()`. Entering a
  step / plate / wire trace and Reset all used to snap; they no longer do. The
  pointer drag and wheel deliberately stay direct — easing a drag is lag.
- **`animGen` cancellation**: a newer move kills the one in flight. Two rAF
  loops both calling `draw()` per frame was costing 12 fps and was found by the
  benchmark disagreeing with itself.
- **Intro fps**: starts on the bottom DPR rung because it is the one heavy frame
  we can see coming; the 500 ms tuner step is too slow for a 2000 ms animation.
  iPhone 30.3 → **42.4**, desktop 28.6 → **38.7**, iPad **32.8**. All clear 30.
- **Pin width caching**: `offsetWidth` per pin per frame was a layout thrash.

**Verified:** full suite PASS · 45.5 fps steady-state · intro ≥30 fps on three
viewports · 0 console errors · every Stage-1 and reconciliation probe still green.

### ✅ STAGE 3 — PDF build sheet + deep links (this session)

Shipped and verified. `AV_FEATURES.md` §15.

- **Deep links**: `#step=` `#part=` `#wire=` `#plate=` `#tab=`, all five verified
  to land on the right view and skip the intro. Hash written back with
  `replaceState` on every state change; `⧉` copies the link to the current view.
- **Build sheet**: cover + hero render, 8 stat tiles, BOM table with live links,
  one block per step with its own render / tool / spec / parts / fasteners,
  fastener schedule, wiring schedule. 9 renders, 3 tables, 45 rows, 332 kB PDF.
- Captured via `draw()` + `toDataURL()` in one synchronous task (no
  `preserveDrawingBuffer` cost), in **light** theme so it does not print as a
  black rectangle, inside `try/finally` that restores camera, explode, mode,
  step, selection and theme — verified by comparing `__avState()` either side.
- No PDF library. `@media print` + `window.print()` is the exporter.

**Verified:** full suite PASS · 46.4 fps · 0 console errors · 5/5 deep links ·
0 blank renders · state and theme restored.

---

## IN PROGRESS

**Nothing.** Clean stopping point. Restore point in `~/Claude/AV/.good/`.

---

## NEXT — Stage 4: Tolerance & clearance callouts

Not started. No files touched for it yet.

Plan when resuming:
1. Config `fits: [{id, a:"partA.feature", b:"partB.feature", nominal, hole,
   shaft, at:[x,y,z], note}]` — the designed fit at each mating interface.
2. Classify clearance / transition / interference from hole−shaft, and flag
   anything under **0.2 mm** as an FDM print risk (real parts come out slightly
   larger than modelled; the CAD already carries `FIT = 0.20` and
   `PRINTER_HOLE_OFFSET = 0.15`, so derive from those constants, do not retype
   them).
3. Render as callouts in 3D reusing the fastener-pin machinery, plus a table in
   the inspector for the selected part.

### Remaining stages (not started)
5 mass properties · 6 kinematics.

---

## Decisions worth not re-litigating

- **`printer.sequential` defaults false.** Do not re-enable the gantry/skirt
  audit for SP hardware. It exists for a future machine that genuinely prints
  one object at a time.
- **Chart series tokens are separate from UI accent tokens** and are not
  interchangeable — the accents fail the categorical lightness band. Re-run
  `validate_palette.js` after ANY change to `--series-*`.
- **Two outputs per build**: standalone `.html` (opens locally) and
  `_fragment.html` (artifact publisher). Keep both.
- **Dark is the bare `:root` default**, light is the `[data-theme="light"]`
  override. This is what makes the fragment correct in both directions after the
  `<html data-theme>` attribute is dropped.
- **Header and dock both sit above the scrim (z 45).** A control the user needs
  while a panel is open must not be behind the panel's own dimmer.
- **4 plates is a product fact**, not a packing failure — housing, lid and shell
  are each 146 mm wide.
- Geometry parity with v1 differs by ≤1 quantisation LSB (~2 µm); this is a
  rounding-mode difference, already investigated, not worth chasing again.

## Known gaps (deliberate, not bugs)
- 14 of 28 BOM lines are `TBD` — unsourced, excluded from every total, listed in
  the build report. Do not fill these with guesses.
- Valve price came from a search index; valworx.com blocks automated fetch.
  Flagged in the inspector.
- fps is measured on SwiftShader (software rasteriser), not a real GPU or a
  real iPhone. It is a floor, not a device figure.
