# /sp-assembly-viewer — proposed update for engine v7

Paste-ready lines for the skill. Everything else in the skill stays as it is.

## "The engine" block — replace the file list lines

```
  viewer_template_motion_v7.html   the CURRENT engine (v6 + ratchets R10–R15)
  patch_engine_v7.py               how it was made: anchored patches, each asserted once,
  engine_v7.js / engine_v7.css     + the v7 module it inlines before BOOT
  build_av_v7.py                   build_av.py carried forward (passes insert / finish / screw,
                                   plate_dir / project_dir; fills the Motion template)
  verify_av_v4.py                  v3 + the v7 gates; must PASS (--floor-ref <v6 page> for the fps gate)
```

## "What every SP AV must have" — add / amend

1. **Build timeline scrubber** — … *(add)* Every step **plays**: parts fly in along their
   `insert` (default: their explode vector), screws drive in along their axis while turning.
   ▷ / ❚❚ / scrub / ↺ per step, ▶ plays the whole build. The printed build sheet stays static.
4. **Section plane, measurement, view presets** — *(add)* **CAD navigation**: orbit about the
   point under your finger, pan (right/middle/shift drag, two fingers), zoom to the cursor and
   pinch-zoom about the pinch centre, a **view cube** (faces, edges, corners), **Fit**,
   **double-tap a part = fit it**, **Persp / Ortho**. Keys: F fit · 1 / 3 / 7 front / right / top
   (Ctrl = opposite) · 0 iso · 5 ortho · 9 flip.
6. **Mobile-first** — *(amend)* tool rail buttons are 44 px tall on phones (were 36).
11. **Wiring lane** — *(add)* a **connector card per node**: pins in order, every conductor
    with its real lead colour (config → label → part library → convention → shown *unset*),
    the connector at each end of every run; gauge · current · drop **chips** on every run;
    a **power budget** (sum of stall currents vs the supply rating, 80 % line) and a
    **common-ground** verdict; tracing a run animates the current flow on the 3D tube and
    the schematic edge.
13. **Viewport look (new)** — key + fill + rim lights over a hemisphere ambient, shading by
    material (PLA matte, PETG gloss, TPU satin, bought plastic, steel screws, brass inserts —
    override with `finish`), CAD edge lines (silhouette, crease, seam between parts) on the
    still frame, a soft contact shadow, MSAA. Edges drop out while a hand is on the model and
    come back crisp on release, so phones keep 30 fps.
14. **3MF hand-off (new)** — inside an artifact the button says **"3MF · zipped by the viewer —
    tap to unzip"** (the platform's downloads allowlist has no .3mf / .stl — do not fight it);
    locally it is the direct .3mf. The plate panel's **On the Mac** card shows the exact
    `…/av/plates/…3mf` path with copy / open-in-slicer / reveal-in-Finder buttons.

## "Verify before reporting done" — replace the command block

```bash
python3 <project>/av/build_av_v<n>.py        # or: python3 ~/Claude/AV/build_av_v7.py av_config.json <out>.html
python3 ~/Claude/AV/verify_av_v4.py <project>_artifact_v<n>.html --shots ./shots --floor-ref <same build on v6>.html
```

…and add to the list of what it proves: view-cube clicks land the right view (face, edge,
corner); pan moves the target, never a model matrix; zoom-to-cursor and pinch keep the picked
point within 2 px (persp and ortho); orbit pivots on the picked point; double-tap fit puts the
part's whole bbox on screen; every build step animates and ends **bit-exact** at the assembled
pose; one connector card per node with ordered pins and a colour per conductor; power budget +
common ground; flow shown in 2D and 3D; the Mac path of the 3MF; the honest zip label and a
.zip handed to the platform inside an artifact; orbit fps ≥ 30 and ≥ 0.9 × the v6 page.

## New config fields (all optional) — one line for the skill

`insert {dir, dist}`, `finish`, top-level `plate_dir` / `project_dir`, wiring node `connector` /
`supply {volts, amps}` / `stall_a`, pin `color` / `order` / `wires`, run `ends` / `dir` —
full table in `CONFIG_SCHEMA.md → Engine v7 fields`; `examples/v7_demo/av_config.json` uses
every one.
