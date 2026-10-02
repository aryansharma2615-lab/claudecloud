# Claude Code CLOUD prompt — SP AV engine v7 upgrade

Paste everything below the line into the cloud Claude Code session.

---

**Where the files are (cloud):** this repo has a branch `sp-av-v6-base` with a folder
`sp_av_v6_bundle/`. Check it out and work ONLY there:
- `sp_av_v6_bundle/engine/` = the current engine (`~/Claude/AV` on Shawarma's Mac): templates
  v5.2 + **v6** (current), `patch_engine_*.py`, `verify_av_v3.py`, `av_geom.py`, `av_pack.py`,
  `export_3mf.py`, `build_av.py`, `AV_FEATURES.md`, `CONFIG_SCHEMA.md`, `CHECKPOINT.md`.
  Ignore any older engine elsewhere in the repo (e.g. a v5.3 branch) — v6 is the base.
- `sp_av_v6_bundle/refs/` = BUILT reference viewers for regression:
  `oneshot_v5_2_arm.html` (built on the v5.2 template), `oneshot_v6_bench.html` (built on v6),
  `smartvalve_v3.html` (older NON-motion engine — look only, no patching).
- The Mac paths named below (`~/Claude/...`) do not exist here. Regression in the cloud =
  apply the patches to the built refs: `patch_engine_v6.patch(html)` then your
  `patch_engine_v7.patch(html)` on `oneshot_v5_2_arm.html`; `patch_engine_v7.patch(html)` on
  `oneshot_v6_bench.html`; then `verify_av_v4.py` on each. So give `patch_engine_v7.py` a
  `patch(s) -> s` function the same way `patch_engine_v6.py` does.
- Browser for the verifier: `pip install playwright && python -m playwright install chromium`
  (use `--with-deps` if it asks). If the browser download is blocked, say so — don't fake a PASS.
- Commit everything new to branch `sp-av-v7` (templates, patch, verifier, docs, screenshots in
  `sp_av_v6_bundle/shots_v7/`) and push. Shawarma's other Claude pulls it back to the Mac.



You are upgrading the Shawarma Prints (SP) assembly-viewer engine — one self-contained HTML
file (hand-written WebGL2, no CDN, no build step, no npm) that every SP CAD project ships as its
build viewer. Engine lives in `~/Claude/AV/`. Current engine: `viewer_template_motion_v6.html`
(made by `patch_engine_v6.py` from v5.2). Verifier: `verify_av_v3.py` (Playwright).

**Skills — use these by name, and read each SKILL.md before the part of the work it covers:**
`/sp-assembly-viewer` (the SP standard — read FIRST), `/cad-assembly-viewer` (base engine idea),
`/cad-viewer`, `/ui-ux-pro-max` (mobile patterns, touch targets), `/design-system` (tokens,
3-layer primitive → semantic → component), `/dataviz` (MANDATORY before any chart, tile or KPI),
`/artifact-design`, `/artifact-diagramming` (wiring schematic), `/artifact-capabilities`
(downloads rules), `/sp-print-dfm` (print values the inspector shows), `/blueprintio` (the bar
for completeness). Skip `/ui-styling` — it is Tailwind/npm and this engine bans both. Skills are
on disk at `~/.claude/skills/`; if one reports "not on disk", stop and tell me — I run
`/reload-skills` myself.

**Read before writing code:** `AV_FEATURES.md` (features + THE RATCHET log), `CONFIG_SCHEMA.md`,
`CHECKPOINT.md`, `patch_engine_v6.py`, `patch_engine_v5_2.py`.

**Hard rules**
1. Never edit an existing template. Write `patch_engine_v7.py` (anchored patches, every anchor
   asserted exactly once) that reads `viewer_template_motion_v6.html` and writes
   `viewer_template_motion_v7.html`. New verifier = `verify_av_v4.py` (v3 + the new gates).
2. Config stays backward compatible: every new feature is driven by OPTIONAL config fields with
   sane defaults computed from what configs already carry (part `explode`, screw `axis`/`len`,
   wiring `nodes`/`runs`). Document every new field in `CONFIG_SCHEMA.md`.
3. Mobile-first: 390 px wide, touch targets ≥ 44 px, thumb-reach controls at the bottom, no
   hover-only interactions, ≥ 30 fps (software-WebGL numbers are a floor), `prefers-reduced-motion`
   respected everywhere.
4. 90 % visual, 10 % words. No paragraphs in the UI.

**The upgrades (all five)**

1. **CAD-grade navigation (Fusion 360 / Onshape feel).** Orbit about the point under the cursor
   (ray-pick the pivot), pan (right/middle drag, shift+drag, two-finger drag), zoom to cursor and
   pinch-zoom to the pinch centre, a clickable **view cube** (faces, edges, corners; animated
   moves), **fit all**, **double-tap / double-click a part = zoom-to-fit that part**,
   orthographic ↔ perspective toggle, desktop keys (F fit, numpad-style front/top/right/iso). The
   existing view presets stay and route through the same eased camera.
2. **Better 3D look.** Key + fill + rim lighting with a hemisphere ambient, per-material shading
   (PLA matte, PETG slight gloss, TPU satin, bought plastics, steel screws, brass inserts —
   material comes from the part's `material`/`kind`), screen-space silhouette + crease edge lines
   like a CAD viewport, a soft contact shadow on the ground plane, MSAA where available. Keep the
   resolution-rung tuner so phones hold 30 fps.
3. **Animated build steps.** Each Build step PLAYS: entering parts fly in along their insertion
   direction (new optional per-part `insert: {dir, dist}`; default = the part's `explode` vector),
   screws drive in along their `axis` while turning, earlier steps stay ghosted, the camera frames
   the step's parts. Play / pause / scrub per step and a "play whole build". The printable build
   sheet keeps static renders.
4. **Detailed wiring.** Real connector pinouts in pin order with real wire colours (e.g. SG90
   lead brown GND / red +5 V / orange signal; the moved SG90 potentiometer's 3 wires), connector
   type per end (Dupont, JST, screw terminal, solder joint), gauge + current + voltage-drop chips
   on every run, a power-budget check (sum of stall currents vs the supply rating, common ground
   present), and on trace: current-flow animation along the 3D tube + the schematic edge.
   Optional new fields: node `connector`, pin `color` / `order`, run `ends`.
5. **3MF downloads.** Inside a published claude.ai artifact the platform's `downloads` allowlist
   has no `.3mf` or `.stl` (see the artifact-capabilities `downloads.d.ts`), which is why the
   engine wraps them in a `.zip`. Do not fight the allowlist. Do: label the artifact button
   honestly ("3MF · zipped by the viewer — tap to unzip"), keep the direct `.3mf` download for
   the local / served page, and make the plate panel show the exact local path
   (`stlPath`'s folder `…/av/plates/…`) so the real `.3mf` is one tap away on the Mac.

**Verify (must PASS before you say done)**
- `verify_av_v4.py` = v3 gates + new gates: view-cube click lands the right view; pan moves the
  target, not the model; zoom-to-cursor keeps the picked point under the cursor (≤ 2 px);
  double-tap fit puts the part's bounding box inside the canvas; every build step's animation
  runs with 0 console errors and ends with parts exactly at their assembled pose; wiring panel
  shows pin order + colours for every node; fps ≥ the v6 floor on the same machine.
- Regression: the two OneShot refs patched to v7 (see the top) must PASS `verify_av_v4.py`.
  A better engine must not break an old product.
- Look at the screenshots yourself (`--shots`) at 390 px and 1280 px, light and dark.

**When done:** add one `AV_FEATURES.md → The ratchet` entry (what changed, which build proved it,
the numbers), update `CHECKPOINT.md`, and write `SKILL_UPDATE_v7.md` with the new feature lines
for `/sp-assembly-viewer` so I can update the skill. Then stop and give me a 5-line summary.
