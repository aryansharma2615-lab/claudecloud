# /sp-assembly-viewer — proposed update for engine v8

Paste-ready lines for the skill (via `/skill-creator`). Everything else in the skill stays as it is.

## "The engine" block — replace the file list lines

```
  viewer_template_motion_v8.html   the CURRENT engine: v7.4 + R38–R54 (LOAD → FIT → SECURE → TEST)
  patch_engine_v8.py               anchored patches, each asserted once (+ engine_v8.js / engine_v8.css)
  build_av_v8.py                   build_av.py carried forward: eng (YAML -> calc_v8 -> META.eng), motion,
                                   checks, parts[].mass, parts[].stl_hi (LOD), brand
  calc_v8.py                       the engineering-data contract: validate, compute, source-label, MEASURE_ME
  engineering_schema_v8.json       JSON Schema every engineering_data_<assembly>.yaml must pass
  tolerance_profile_ender3s1pro.json   hole shrink per printer × material (STUB until the coupon is measured)
  verify_av_v9.py                  v3 → v7.4 gates first, then the v8 gates; must PASS
```

## "Order of operations" — add before any geometry

- Write `engineering_data_<assembly>.yaml` (every value `{v, u, src}`; src ∈ MEASURED · CALC · CAD · SLICER ·
  DATASHEET · ASSUMED · SPEC). The CAD script reads its `params`; nothing is typed twice.
- `python3 calc_v8.py engineering_data_<assembly>.yaml --measure MEASURE_ME.md` — hand the list to Shawarma first.
- Slice for real: PrusaSlicer CLI with the flattened stock Creality Ender-3 S1 Pro profile (see
  `examples/v8_demo/cad/slice.py`) → grams / minutes are `SLICER`, not estimates.

## "What every SP AV must have" — add

14. **Guided phases — LOAD → FIT → SECURE → TEST.** A stepper over the tabs; each phase is a URL-hash state
    (bare token, because a published artifact passes only `[A-Za-z0-9._~-]`: `#v8~test~kg0.75~lev22.5~sec1_0.4000_0~xr~cam…`). LOAD: hover/tap tooltip (name, material, mass,
    print time). FIT: explode spacing (mm), **tolerance rings** on every hole coloured from the printer profile,
    **caliper**, **stack-up** (worst-case + RSS, "eats most"), fit calculator. SECURE: auto-assembly with insert
    iron temperature + screw torque chips (with their source). TEST: load slider (kg + lever) → **CALC stress
    heatmap**, servo-stall warning, "what breaks first?" ranking with fly-to and the fillet fix (Kt before/after),
    τ(θ) chart, sweep on the Motion lane, X-ray, wireframe, section with **capped** faces.
15. **Every engineering number carries its source label.** No invented numbers: a check with any ASSUMED input
    reads UNVERIFIED, never PASS; a missing required field is an orange MISSING badge and fails the build.
16. **Engineering data card in the inspector** (material XY/Z, E, Tg, mass/COM, print panel from the profile,
    G-code grams/time), **parts tree** drawer (bottom sheet under 768 px), **Share** button, **STL per part +
    Send to slicer (3MF)**, BOM rows on the shelf read **OWNED $0**, **Perf** HUD (fps · triangles · calls),
    LOD swap past 2× zoom, default view < 50k triangles.
17. **Every test print gets its own AV** (e.g. `hole_coupon_v8.html`: LOAD + FIT only; measurements typed in
    ride in the link).

## "Verify before reporting done" — replace the command

```bash
python3 ~/Claude/AV/verify_av_v9.py <out>.html --eng engineering_data_<assembly>.yaml \
   --floor-ref <same build on v7.4>.html --measure MEASURE_ME.md --exports <cad out dir> \
   [--coupon <coupon AV>.html] --shots ./shots
```
Adds to the proof list: YAML validates (jsonschema) and META.eng.missing is empty; every §5 check is a tile and
calc_v8 recomputes each value (≤ 1e-4, 5 s.f.); the §5 formulas agree JS vs Python; the TEST model = calc_v8 at
6 load cases (≤ 1 %) and the Motion lane's r × F = the hand calc; every phase restores from the hash in a fresh
page; a DOM scan finds no numeral without a source label; ring colours = the profile, and recolouring the profile
recolours them; a pixel inside the cut is the cap colour; < 50k triangles, LOD swaps in, orbit ≥ 30 fps at 390 px;
no horizontal scroll and every control ≥ 44 px at 390 px; screws fly in from their declared side; STL watertight,
3MF / GLB load, URDF loads in PyBullet; the stress ramps pass the dataviz validator; the caliper reads a known
70.00 mm; OWNED $0 in the BOM.

## New config fields — one line for the skill
top level `eng` (YAML path) or `eng_json`, `motion`, `checks`, `brand`; parts `mass {g, com, how}`, `stl_hi`.
Full contract: `engineering_schema_v8.json`; worked example: `examples/v8_demo/`.

## Lessons to keep
- A uniform branch in a fragment shader is NOT free on SwiftShader (headless) — it cost ~15 % fps. Optional
  shading (heat, wireframe) lives in a second program used only when on.
- Share state in a BARE hash token (`#v8~…`): artifacts strip `=` and `&`.
- The engine's FRONT is −Y. Build the design's front facing −Y or every screw reads "BACK".
- Size self-tap pilots to the PRINTED diameter (holes shrink); check ligaments on CAD and printed geometry.
