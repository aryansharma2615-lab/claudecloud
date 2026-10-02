# SP assembly-viewer engine — v6 base (for the v7 upgrade)

Snapshot of `~/Claude/AV` from Shawarma's Mac, 2026-10-02, plus built reference viewers.

- `engine/` — current engine: `viewer_template_motion_v6.html` (= v5.2 + ratchet R8 gear-train loads),
  patches, `verify_av_v3.py`, geometry/packing/3MF helpers, docs.
- `refs/` — built viewers to regression-test a new engine against.
- `PROMPT_engine_v7_cloud.md` — the task.

Work goes to branch `sp-av-v7`. Do not edit anything in `engine/` in place — add new versioned files.
