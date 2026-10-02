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
