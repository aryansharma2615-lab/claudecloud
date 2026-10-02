# SP AV engine — ratchet entries for v5.3 (merge into ~/Claude/AV/AV_FEATURES.md → The ratchet)

Built in the cloud from the published OneShot v5.2 viewer (engine v5.2 + data); `patch_engine_v5_3.py` writes
`viewer_template_motion_v5_3.html`. Every anchor is asserted exactly once. Regression: the patched template still
carries the OneShot v5.2 data and renders with no console errors (headless, 390 px).

| # | Lane | What changed | Hit by | Proof |
|---|---|---|---|---|
| R8 | Looks / UI | Far clip plane follows the scene: `farClip() = max(2000 / 4000 plate, dist() + 3·bbox)`, used by draw, pick, offscreen and curMVP. v5.2 hard-coded 2000 mm, so anything over ~0.6 m (a station, a rail robot) framed itself outside the frustum and the stage rendered black. | FarmHand (1.5 m rail + two printers) | FarmHand stage blank on v5.2 → renders on v5.3; OneShot v5.2 unchanged |
| R9 | CAD-quality tools | **Checks lane**: a 7th dock tab. `META.checks = [{group,label,value,limit,unit,status,source,note}]` → pass / warn / fail KPI row + grouped meters (value vs limit) with the script that proves each gate. Glyph + colour (never colour alone). Hidden when a config has no checks, so old products keep their dock. | FarmHand (22 gates: torque, sim, sag, clashes, bed fit, 7 box-sweep paths, mesh sweep, firmware + link tests, station) | 390 px headless: no overflow, no console errors; caught a plate-packer bug (forearm diagonal fit) on first run |

Data-only uses of existing features worth copying (no engine change):
- **Door as a moving obstacle**: a revolute joint with `parts: ["h2s_door"]` and the door angle in every path key;
  the BVH path sweep then checks the arm against the swinging door. It found 2 real collisions (the upper-arm tail
  vs the Z gantry plate, FarmHand D254) that the box-model sweep had missed.
- **Prismatic driven axes** (`type: "prismatic"`, `units: "mm"`) for rails and lift columns already work in v5.2.

Next rungs exposed by FarmHand:
- Path editor: tap a path frame → edit the key; today paths come only from the config.
- Wiring lane for a 24 V system with an E-stop chain (FarmHand `docs/WIRING.md` → `META.wiring`).
- Fasteners + fit check for the FarmHand screws (needs the Mac's `build_av.py` ray-caster).
