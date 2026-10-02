# FarmHand robot — research synthesis (Phase 1, 2026-10-02)

Six research passes, one file each in `docs/research/`:
[farm_automation](research/farm_automation.md) · [open_arms](research/open_arms.md) ·
[station_architectures](research/station_architectures.md) · [end_effectors](research/end_effectors.md) ·
[printer_specifics](research/printer_specifics.md) · [motion_hardware](research/motion_hardware.md).
The pick that follows from it: [ARCHITECTURE_ROBOT.md](ARCHITECTURE_ROBOT.md).

## Read this first: how solid is the evidence?

- **The research network was badly restricted.** The sandbox proxy blocked page fetches for everything except
  GitHub, and the session's 200-search cap ran out part-way. So:
  - **Hard facts** come from files actually read on GitHub: Bambu Studio's own H2S profiles and G-code, the
    Home Assistant Bambu integration, OpenBambuAPI, Marlin/Klipper configs, open arm repos and their issues,
    and vendor PDFs hosted on GitHub.
  - **Vendor facts and prices** come from search-result summaries. They are tagged `[s]`/`[web]`/`C*` in the
    topic files and **must be re-checked on the real page before money is spent.**
- Grades used everywhere: **A** built + documented + video + measured · **B** built, photos/code, few numbers ·
  **C** vendor spec · **D** hearsay/render. Very little reached A: nobody publishes measured repeatability for hobby arms.
- **Re-run needed with open web:** rail/extrusion/brake/PSU prices, encoder accuracy datasheets, stepper 24 V
  torque curves, H2S door/plate videos, ISO/TS 15066 force tables (the standard for how hard a collaborative robot may hit a person).

## Research table (designs worth learning from)

| Design | Source | Joint mechanism | Reduction | Bearings | Actuator | Load (documented) | Strengths | Weaknesses | Worth adapting | What we improve |
|---|---|---|---|---|---|---|---|---|---|---|
| Brooks PreciseFlex PF400 / PF3400 (lab plate handler) | [PyLabRobot kinematics](https://github.com/PyLabRobot/pylabrobot/blob/main/pylabrobot/brooks/precise_flex/kinematics.py), PF sheets (C*) | SCARA, Z column, level wrist, optional 1–2 m rail | belts + harmonic (not documented in detail) | not documented | servo, absolute encoders | 0.5–1.2 kg (PF400), 3 kg (PF3400), ±90 µm | moves plates into instruments through doors; collision < 100 N | US$13–16k used | **the whole layout: Z-column SCARA on a rail, level wrist** | steppers + belts + output encoders at ~1/6 the cost; printed housings |
| DHR Engineering print-farm robot | [dhr.is](https://dhr.is/projects/3d-print-farm-automation) (B, numbers not documented) | robot on a rail, plate racks | n/d | n/d | n/d | serves 20–44 Bambu printers incl. H2D | production precedent for rail + whole-plate swap; robot-friendly spool containers | payload/precision unpublished | rail stations, whole-plate swap, standardised plate/spool features | open, documented, H2S-specific; smaller |
| Dobot M1 Pro on a Bambu X1C (YouTube series) | [forum thread](https://forum.bambulab.com/t/dude-on-youtube-trying-to-build-an-x1c-automaton-robot/8098) (B) | SCARA | n/d | n/d | servo | 1.5 kg at 400 mm (C) | opened the door | **could not get the plate out**; gave up on swaps | warning: plate extraction is the hard job | prototype the plate pull on the real H2S first (D217) |
| PAROL6 (Source Robotics) | [docs](https://github.com/Source-Robotics/PAROL-docs) (B) | 6-axis | EG17 planetary + belt J1 6.4:1 | tapered-roller pairs J2/J3 | NEMA 17, TMC5160, open loop | 1 kg near base, 0.5 kg full workspace | well documented, Python API on Windows (Ruckig + IK) | 15–20 arcmin backlash (2–3 mm at 0.5 m), no brakes, PETG near motor-heat limit | tapered-roller pairs, belt J1, Python control pattern | output encoders, brakes where gravity acts, no gravity on revolute joints |
| Dexter HD (Haddington) | [wiki](https://github.com/HaddingtonDynamics/Dexter/wiki) (B) | 6-axis | harmonic 52:1 | n/d | steppers | n/d | **absolute encoder on the joint output** (50 µm claim) | FPGA complexity | output-side encoder idea | 14-bit magnetic encoders on an ESP32-S3 |
| Dummy (peng-zhihui) | [repo](https://github.com/peng-zhihui/Dummy-Robot) (B) | 6-axis | harmonic 30–50:1 | n/d | closed-loop steppers | n/d | switchless absolute zeroing against a hard stop | small payload | hard-stop + absolute encoder zeroing | same trick on X and Z |
| Faze4 | [repo](https://github.com/PCrnjak/Faze4-Robotic-arm) (B) | 6-axis | printed cycloidal | thin ball bearings | steppers | n/d; arm 15 kg | offset belt stage opens a hollow cable path | ~1000 parts; cycloid backlash unpublished | hollow joint cable routing | fewer parts; no printed reducers on load paths |
| FarmLoop Stage 2 H (3D Farmers) | [kit page](https://3d-farmers.com/products/farmloop-stage-2-h-series) (C) | add-on: door opener (64 N) + 2 plate-edge actuators | — | — | linear actuators | plate stays in the H2S | cheap (~US$235), supports H2S | no plate swap, no spools; push-off fails on grippy plates | flex-then-push physics → our offline flex station | done outside the printer, in parallel with the next print |
| Jubilee kinematic coupling | [repo](https://github.com/machineagency/jubilee) (A for 40 µm) | 3 balls in V-seats + lock | — | — | — | "non-loadbearing" machine | 40 µm tool repeatability | not rated for load | the quick-change flange for v2 tools | mechanical seat carries load, magnets only preload |
| DoorBot (door opening) | [repo](https://github.com/TX-Leo/DoorBot) (A) | mobile manipulator | — | — | — | 90 % on 20 unseen doors | motor-current haptics for push/pull/unlock | 10 % fail on grasp pose | current-limited handle grasp | AprilTag-refined handle pose, hook fallback |

## Key facts by topic (the ones that shaped the pick)

| Topic | Fact | Grade | Effect on the design |
|---|---|---|---|
| Farm automation | Nothing swaps plates on an H2S/H2D; FarmLoop and 3DQue only flex in place and push with the toolhead | C | our robot does something no kit does (SP product gap) |
| Farm automation | Cool-down to release temperature (25–44 °C in sources) dominates every cycle | C/B | swap the plate, clear it offline while the next print runs |
| Farm automation | Grippy plates (SuperTack, Frostbite) never release or shear off | C | one approved plate type per printer (textured PEI) |
| Arms | No hobby 6-axis arm is shown holding 1.5 kg at 0.5 m; nobody publishes measured repeatability | B | don't hang 1.5 kg on revolute motors → SCARA |
| Arms | AR4 licence forbids selling robots/parts/kits; PAROL6/Dexter GPLv3, OpenArm CERN-OHL-S | B | copy ideas, never files (SP must own its design) |
| Station | Base on the door axis (rail) removes the 520–680 mm reach problem of a base between printers | reasoning | rail |
| Station | Lab SCARAs on rails already load plates into instruments | C* | layout precedent |
| End effector | A quick-changer costs 0.2–0.36 kg of the 0.3 kg left at the spool pose; pogo pins are the weak point | C/B | one hand, kinematic flange for v2 only |
| End effector | Projected-capacitive screens need a grounded conductive tip ~8–9 mm; resistive needs 0.3–1 N of press | C | grounded stylus on a > 1 N spring plunger works on both |
| Printer | H2S door state = MQTT `print.stat` bit 0x00800000 (captured on an H2D); `home_flag` doesn't carry it | A | interlock field for the permit lease |
| Printer | H2S plate outline 355.0 × 346.5 mm, 0.5 mm steel (~486 g computed); bed ends a print ~100 mm down, commandable with `gcode_line` | C (code) | plate grip, hand-off height |
| Printer | AMS 2 Pro: on top of the H2S, spools 197–202 mm OD × 50–68 mm wide | C/D | Z travel ~0.95 m for v2; check 1.2 kg spool fit |
| Printer | Ender screen is a DWIN/DGUS touch panel, capacitive vs resistive unknown; OctoPrint + `M108` avoids taps | C (code) | stylus works on both; taps are fallback only |
| Motion | MKS SERVO42D stall trip **releases the shaft**; PAROL6 has no brakes | C | brake on the only gravity axis (Z) |
| Motion | Printed PLA cycloid 319 N·m/rad (39 mm at 25 N·m, 0.5 m), backlash grows in 60 h | A | no printed reducers on load paths |
| Motion | ±1 mm at 0.5 m = ±6.9 arcmin for the whole chain; 20 arcmin planetary = 2.9 mm | derived | belts + output encoders, not cheap planetaries |
| Motion | MoveIt 2 is Ubuntu-only in practice; Ruckig + roboticstoolbox have Windows wheels | B | lean Python planner; SCARA IK is closed-form |

## Failure → rule table (seeds for DESIGN_DECISIONS D201+ in Phase 2)

| D | Documented failure | Source (topic file) | Rule it creates |
|---|---|---|---|
| D201 | Hobby arms derate payload (PAROL6 1 → 0.5 kg); Forte missed steps above 0.63 kg | open_arms, motion_hardware | no revolute joint carries gravity torque; gravity only on the Z screw |
| D202 | Arm drops at power loss (PAROL6 no brakes); MKS stall trip releases the shaft | open_arms, motion_hardware | Z has a power-off brake wired through the E-stop contactor |
| D203 | 15–20 arcmin gearbox backlash = 2–3 mm at 0.5 m | open_arms | belt reductions + 14-bit output encoders; final approach from one direction |
| D204 | Printed PLA cycloid soft (319 N·m/rad) and wears in 60 h | motion_hardware | no printed reducers on load paths; printed parts are housings and links |
| D205 | AR4 drifts while its motor encoder still reads home | open_arms | absolute encoder on every joint output; fault on motor/output mismatch |
| D206 | Coupler set screws loosen, belts slip (PAROL6) | open_arms | clamp hubs or keys, no set screws on load paths, threadlocker + torque stripe |
| D207 | Motors run 73 °C next to PETG (softens ~80 °C) | open_arms | metal or PETG-CF/ASA/PC motor mounts; low hold current (no gravity load) |
| D208 | Cables break and wear through (OpenArm) | open_arms | cable chains on X and Z, hollow joint routing, bend radius ≥ 10× cable diameter |
| D209 | Calibration fails without hard stops (SO-101, AR4) | open_arms | hard stop per axis, one homing routine with timeout; absolute encoders = no re-home sweep inside a printer |
| D210 | 50 mm systematic pose offset (OpenArm) | open_arms | kinematic calibration against AprilTags; per-printer taught points |
| D211 | A rail axis outside the kinematics drifts (AR4 7th axis) | station_architectures | X rail = indexed stations, re-referenced to an AprilTag at each station |
| D212 | Jubilee frame is "non-loadbearing" | station_architectures | compute column + link deflection for 1.5 kg; ≤ 1 mm at the plate pose |
| D213 | MKS SERVO42D firmware bugs (homing, PID not saved, freezes) | motion_hardware | CL57T step/dir drives; homing, PID and limits live in our firmware |
| D214 | Regen spikes kill drivers on a normal PSU (moteus docs) | motion_hardware | TVS/brake-resistor clamp on the 24 V bus, decel limits, no hot-plugging |
| D215 | StallGuard unreliable below ~10 rpm (Klipper docs) | motion_hardware | collision = following error + encoder mismatch + current, never a position reference |
| D216 | PLA encoder mounts warp; loose magnets | motion_hardware | PETG/PC/aluminium encoder brackets, glued diametric magnets, 2 mm gap |
| D217 | Dobot M1 opened an X1C door but couldn't remove the plate | station_architectures | mock-tool test of the H2S plate pull on arrival day, before freezing geometry |
| D218 | False "door open" until pushed at the magnet (H2S forum) | printer_specifics | after closing, push at the magnet; door bit clear for 2 s before any start |
| D219 | Door state read from the wrong MQTT field | printer_specifics | read `stat` bit 0x00800000; unknown = open |
| D220 | Printer door sensor doesn't always pause | printer_specifics | robot interlock never depends on the printer stopping |
| D221 | "Marker not detected" / plate offset even when seated | printer_specifics | max 2 reseat retries, then stop + alert; keep plate underside clean |
| D222 | Bed left at the bottom grinds the next start | printer_specifics | park the bed mid-height after each robot job |
| D223 | `FINISH` arrives while end G-code is still moving (Bambuddy) | farm_automation | FINISH ≠ safe: also idle + `stg_cur` + camera |
| D224 | Push-off knocks the toolhead cover off; firmware faults | farm_automation | robot never touches the toolhead; parked toolhead confirmed before entry |
| D225 | SuperTack / Frostbite plates don't release or shear off | farm_automation | one approved plate type per printer; hold the plate down against any sideways force |
| D226 | Parts don't release while the bed is warm | farm_automation | clear at a calibrated release temperature (hand-release temp − 4–6 °C), never above 35 °C entry |
| D227 | Spaghetti can't be swept | farm_automation | failed prints are "human needed"; robot doesn't clear them |
| D228 | Vision gating can be wrong | farm_automation | fail closed: uncertain = hold the queue |
| D229 | Ender screen prompt stalls host prints | printer_specifics | `M108` from OctoPrint, not a screen tap |
| D230 | AMS slots locked mid-print; spool tape lets go at the end | printer_specifics | restock only when idle; swap before empty (gram tracking) |
| D231 | Pogo pins "more problematic than expected" | end_effectors | v1: no electrical pass-through; one hand, passive tools later |
| D232 | Dust and loosening docks degrade tool changers | end_effectors | covered coupling, threadlock, AprilTag check of the dock |
| D233 | Fin-ray fingertips lose force on edge contact | end_effectors | rigid steel nail at the fingertip; fin-ray pads for wrap grips |
| D234 | Conductive-rubber stylus tips crack; plastic never registers | end_effectors | replaceable tip + tap counter + ground wire; test on both screens |
| D235 | Suction loses 20–50 % of area on texture | end_effectors | no suction on textured PEI in v1 |
| D236 | Spool bores vary 50–58 mm; cardboard sheds dust | end_effectors | printed hub plug on every spool |
| D237 | Door grasp-pose errors (DoorBot 10 % fails) | end_effectors | camera-refined handle pose, current-limit abort, hook fallback |
| D238 | Magnets alone can't hold heavier tools | end_effectors | magnets preload only; the mechanical seat carries load and moment |
| D239 | PAROL6 E-stop is a firmware DISABLE | motion_hardware | E-stop cuts driver power in hardware (category 0) + drops the Z brake |
| D240 | Collaborative SCARAs cap collision force (PF3400 < 100 N; MG400 < 12 N reported) | station_architectures | current caps → ≤ 50 N at the tool in the shared zone (target, verify vs ISO/TS 15066) |
