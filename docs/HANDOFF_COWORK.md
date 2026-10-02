# FarmHand robot — handoff to Cowork on the Mac (paste everything below the line)

---

You're picking up the **FarmHand** print-farm robot for Shawarma Prints (SP). A cloud session did Phase 1
(research, Gate 1) and a first pass of Phase 2 (CAD, sim, firmware). Your job: finish Phase 2/3 on the Mac,
where the full SP assembly-viewer engine lives, and run the ordering with Shawarma.

**Get the work:** `git clone https://github.com/aryansharma2615-lab/claudecloud ~/Claude/PrintFarm` (or `git pull`)
and `git checkout claude/festive-johnson-0icv8n`. Python deps: `pip install build123d trimesh pybullet pytest`.

**Read first, in this order:** `prompts/A_robot_redesign.md` (the full brief, phases and gates) →
`docs/ARCHITECTURE_ROBOT.md` (the pick: SCARA arm on a Z column on an X rail, and why) →
`docs/DESIGN_DECISIONS.md` (D241–D253 + assumptions ledger + open items) → `docs/RESEARCH.md` (D201–D240 rules) →
`docs/BOM.md` (lean buy list ~C$770) → `sim/SIM_REPORT.md` + `sim/PATHS_REPORT.md` → `docs/WIRING.md`.
Also check Mem0 (project "farmhand").

**State right now (all numbers re-runnable):**
| Thing | Where | Status |
|---|---|---|
| Torque pass | `design/phase1_torque_pass.py` | worst joint J1 62 % (rule ≤ 70 %) |
| Stiffness | `sim/stiffness.py` | Fix B: 0.44 mm tool sag (≤ 1 mm) — lower bound, no bearing/wheel play |
| Dynamics | `sim/sim_check.py` (PyBullet, `urdf/farmhand_scara.urdf`) | sim 84 % of hand calc ✓, revolute hold 0 N·m |
| Job paths | `sim/paths.py` | 7 jobs clean vs printer box models, with joint/reach margins |
| CAD | `cad/params.py` (single source) + `cad/build_parts.py` → `cad/out/*.step/.stl` | 15 printed parts, 0 clashes over 43 bodies, all fit a bed |
| Viewer | `cad/viewer_config.py` → published at https://claude.ai/artifact/AU2Tzgdss1pAZRXaCz1yLW | generic cad-assembly-viewer (no Motion lane) |
| Firmware | `firmware/farmhand_mc/` (ESP32-S3) | host tests pass; **never compiled** (cloud blocked PlatformIO) |

**Your tasks, in order:**
1. **Measurements → re-run.** Get Shawarma's numbers (table W×D×H, printer gap and positions, H2S door hinge side +
   swing + aperture, plate weight + how it comes off, screen photo with a ruler, AMS on top or beside, Ender real
   Y stop). Put them in `cad/params.py` and the ASSUMED block at the top of `sim/paths.py`; re-run
   `python cad/build_parts.py && python sim/paths.py && python sim/sim_check.py`. Fix anything that goes red.
2. **SP assembly viewer (the real one).** Rebuild the viewer on the SP engine in `~/Claude/AV`
   (viewer_template_motion_v5_2.html, patch_engine_v5_2.py, verify_av_v3.py; read AV_FEATURES.md, CONFIG_SCHEMA.md,
   CHECKPOINT.md first) with `/sp-assembly-viewer`. Feed it `cad/out/asm/*.stl` (already in assembly frame).
   Must have: Motion lane with the real job paths from `sim/paths.py` (plate pull/insert, door pull + push, screen
   tap, Ender sheet, rail carry) as through-moves; **ratchet the engine** with a prismatic rail joint (X) and the
   H2S door as a moving obstacle; every screw drawn from its insertion side; Load-vs-stall from the torque pass;
   wiring lane from `docs/WIRING.md`; BOM drawer with HAVE/BUY and ×10/×50/×100. verify_av_v3 must PASS; look at the
   screenshots. Never hand-edit the template: anchored patch → new versioned template + AV_FEATURES.md entry.
3. **Build sheet** (~90 % visual): research cards, the architecture pick, torque and %-of-stall charts, the sag
   before/after (22.8 → 0.44 mm), end-effector exploded view, phased buy list. Publish both.
4. **Firmware compile:** `cd firmware/farmhand_mc && pio run`. Fix library API drift (FastAccelStepper, TMCStepper,
   ArduinoJson 7). Keep `include/supervisor.h` rules intact and `g++ -std=c++17 -Iinclude test/host_test.cpp` passing.
5. **Ordering (with Shawarma):** walk `docs/BOM.md` line by line, open each store link, confirm the real CAD price
   and stock, mark HAVE vs BUY, then give him one cart per store. Most lines are estimates (the cloud couldn't
   reach shops). Nothing gets bought without his OK.
6. **Before the big prints:** print `cad/out/fit_coupon.stl` (~1 h) and tune `SEAT_CLR` / `SPIGOT_CLR` in params.

**Rules that stay:** no CAD changes without updating `docs/DESIGN_DECISIONS.md` (next is D254); every number traces
to a script; plain-English definitions for every term (Shawarma's preference); keep replies short; commit + push
to `claude/festive-johnson-0icv8n` after every step.
