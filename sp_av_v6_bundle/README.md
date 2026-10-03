# SP assembly-viewer engine — v6 base (for the v7 upgrade)

Snapshot of `~/Claude/AV` from Shawarma's Mac, 2026-10-02, plus built reference viewers.

- `engine/` — current engine: `viewer_template_motion_v6.html` (= v5.2 + ratchet R8 gear-train loads),
  patches, `verify_av_v3.py`, geometry/packing/3MF helpers, docs.
- `refs/` — built viewers to regression-test a new engine against.
- `PROMPT_engine_v7_cloud.md` — the task.

Work goes to branch `sp-av-v7`. Do not edit anything in `engine/` in place — add new versioned files.

## v7 (branch `sp-av-v7`)

- `engine/patch_engine_v7.py` (+ `engine_v7.js`, `engine_v7.css`) → `engine/viewer_template_motion_v7.html`.
  `patch(html)` also upgrades any built v6 page in place (that is how `refs_v7/` were made).
- `engine/verify_av_v4.py` — v3 + the v7 gates. `--floor-ref <v6 page>` for the fps gate.
- `engine/build_av_v7.py` — `build_av.py` carried forward without editing it.
- `refs_v7/` — the two OneShot refs upgraded to v7 (+ the arm on v6, the fps floor).
- `examples/v7_demo/` — a small config that uses every new v7 field, built + verified.
- `shots_v7/` — verifier screenshots (390 px + 1280 px, light + dark) for bench, arm, demo.
- `engine/SKILL_UPDATE_v7.md` — lines for `/sp-assembly-viewer`.

On the Mac: copy `engine/*v7*`, `engine/verify_av_v4.py`, `engine/build_av_v7.py` into `~/Claude/AV/`.

## v7.1 → v7.3 (same branch, later)

Each is a patch on the previous template, its module in `engine_v7_N.js/.css`, and a verifier that
runs every earlier gate first: `verify_av_v5.py` (v7.1), `verify_av_v6.py` (v7.2),
`verify_av_v7.py` (v7.3 = current). Pages: `refs_v7/*_v7_1/2/3.html`, `examples/v7_demo/v7_N_demo_av.html`.
Screens: `shots_v7_3/` (and reports `v7_report.json` beside them).

## v8 (branch `sp-av-v8`) — LOAD → FIT → SECURE → TEST

- `engine/patch_engine_v8.py` (+ `engine_v8.js`, `engine_v8.css`) → `engine/viewer_template_motion_v8.html`
  (patches the v7.4 template; `patch(html)` also upgrades any built v7.4 page — that is how `refs_v8/` were made).
- `engine/calc_v8.py` + `engine/engineering_schema_v8.json` — the engineering-data contract (source labels,
  checks, UNVERIFIED / MISSING, MEASURE_ME). `engine/tolerance_profile_ender3s1pro.json` — hole shrink (stub).
- `engine/build_av_v8.py` — builder (eng, motion, checks, mass, LOD meshes, brand).
- `engine/verify_av_v9.py` — every earlier gate (v3 → v7.4) + the v8 gates. (The v7.4 gates live in
  `verify_av_v8.py`; the file numbers ran ahead of the engine numbers in v7.x.)
- `examples/v8_demo/` — Shawarma Servo Mount v1: YAML, build123d CAD, PrusaSlicer G-code, URDF/SRDF/SDF +
  PyBullet check, `servo_mount_v8.html`, `coupon/hole_coupon_v8.html`, DESIGN_BRIEF / DESIGN_DECISIONS / MEASURE_ME.
- `research_v8.md`, `ADR_v8.md`, `BOM_v8.xlsx`, `engine/SKILL_UPDATE_v8.md`, `shots_v8/`.

Rebuild everything:
```bash
cd examples/v8_demo
python3 cad/servo_mount_v1.py && python3 cad/slice.py && python3 cad/make_urdf.py && python3 cad/hole_coupon.py
python3 ../../engine/calc_v8.py engineering_data_servo_mount_v1.yaml --measure MEASURE_ME.md
python3 make_config.py && python3 ../../engine/build_av_v8.py av_config_v8.json servo_mount_v8.html
(cd coupon && python3 ../../../engine/build_av_v8.py av_config_coupon.json hole_coupon_v8.html)
python3 ../../engine/verify_av_v9.py servo_mount_v8.html --eng engineering_data_servo_mount_v1.yaml \
  --floor-ref servo_mount_v7_4_floor.html --measure MEASURE_ME.md --exports out --coupon coupon/hole_coupon_v8.html --shots ../../shots_v8/servo_mount
```
On the Mac: copy `engine/*v8*`, `engine/calc_v8.py`, `engine/engineering_schema_v8.json`,
`engine/tolerance_profile_ender3s1pro.json`, `engine/verify_av_v9.py`, `engine/build_av_v8.py` into `~/Claude/AV/`.
