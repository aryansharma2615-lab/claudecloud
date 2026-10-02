# FarmHand rail-SCARA — design decisions (D201+)

D201–D240 are the research rules in [RESEARCH.md](RESEARCH.md) (failure → rule table). Below: decisions made
while designing and checking. Each says what, why (with the number), and where it's checked.

| D | Decision | Why (number) | Checked in |
|---|---|---|---|
| D241 | Architecture = SCARA on a Z column on an X rail | only Z carries gravity; revolute hold torque 0 N·m (sim); scored 4.25/5 vs 3.30 runner-up | design/phase1_torque_pass.md, sim/SIM_REPORT.md |
| D242 | Lean drive train: NEMA 17 + TMC2209 everywhere, closed loop via MT6701 output encoders | no gravity on the arm joints → worst load 62 % (J1); BOM C$2,302 → C$770 | design/phase1_torque_pass.md (lean), docs/BOM.md |
| D243 | Z = T8×2 lead screw, no brake | lead angle 4.5° < friction angle ~8.5° → self-locking; holds 44.7 N with power off | sim/SIM_REPORT.md §2 (verify on the bench) |
| D244 | **Stiffness Fix B**: upper arm closed box 50×60 (cover screwed + glued) with 2 stacked 25×25×2 alu tubes; forearm 44×50 with a 20×20×1.5 tube; **4080** Z column | as first drawn the tool sagged **22.8 mm** under 1.5 kg (U-channel PETG + 2040 on its weak side); Fix B = **0.44 mm** (≤ 1 mm rule, lower bound) for +C$40 | sim/stiffness.py |
| D245 | J2 motor moved from behind J1 to on top of the elbow, single 12T→60T stage (1:5) | frees the upper-arm interior for the spine tubes; costs J1 +4 % (2.16 N·m sim, 62 % hand calc) and J2 now 180° in 2.2 s (55 %) | design/phase1_torque_pass.md |
| D246 | H2S door = pull by the handle to 40°, then push the inner face (140 mm from the hinge) to 170° | pulling past ~45° puts the handle behind the robot's shoulder line (J1 > 150°); pull + push is clean with ≥ 9 mm clearance | sim/PATHS_REPORT.md |
| D247 | One rail stop per plate move (no rail motion while a plate is inside a printer) | single stop X = 600 is clean with 48 mm clearance at 536 of 550 mm reach; mid-move rail jumps were the planner's failure mode | sim/PATHS_REPORT.md |
| D248 | No rail moves through the door's sweep while it is between 30° and 150° | the open door crosses the rail line (y = −115) for those angles | sim/paths.py door model; firmware `keepout` command (supervisor.h, host-tested) |
| D249 | Plates are swapped, then cleared offline at a flex station | cool-down dominates every in-printer clearing method (research); the printer restarts while the robot clears | docs/ARCHITECTURE_ROBOT.md |
| D250 | Hand = one multi-mode hand on a 3-ball kinematic flange; ball seats sit 2.8 mm proud | a ball in a 90° V-groove sits r·√2 above the apex → faces never touch (clash check caught it) | cad/build_parts.py, docs/DFM_REPORT.md |
| D251 | Stylus barrel must point horizontally (screens are on vertical faces, the wrist has no pitch) | path sweep models a horizontal stylus; CAD barrel now runs along +y (done) | sim/paths.py, cad/build_parts.py |
| D253 | Planning margins: J1 ±140°, J2 ±140°, reach ≤ 530 mm (plate pull ≤ 540) | the first sweep planned poses at J1 = −150° and 549/550 mm reach: no room for calibration error | sim/paths.py |
| D252 | Viewer renders at 1:2 scale | the viewer template's far clip is 2 m and the robot spans ~1.5 m | cad/viewer_config.py |

## Assumptions ledger (replace with measurements)
Table 1500 × 750 × 750, printers against the back wall, 100 mm gap, H2S on the left with a left-hinged door
opening 180°, door aperture 452 × 520 mm, plate front edge 60 mm behind the door, bed commanded to 250 mm,
Ender bed at 100 mm, AMS on top of the H2S, printed E-modulus (PETG 2.0 GPa), V-slot inertias from catalogue.

## Open items
- ~~Tight margins~~ **fixed (D253):** planner now keeps J1 ≥ 10° and J2 ≥ 5° from the hard stops and the wrist
  ≥ 20 mm inside full reach (10 mm for the slow straight plate pull); door push point moved to 140 mm from the hinge.
  All 7 jobs still clean.
- **v2 spools:** shoulder max height 950 mm puts the hand ~800 mm up; AMS on top of the H2S needs a ~1.25 m column
  or the AMS moved beside the printer.
- Print the fit coupon (cad/out/fit_coupon.stl) before the big parts; first ESP32 compile on the PC (toolchain blocked in the cloud).
