# Open-source and low-cost robot arms, 1-3 kg class: what really works

FarmHand research, 2026-10-02. Target: 1.5 kg at ~0.5 m reach, +/-1 mm at the tool, 24/7, closed-loop on every axis.

**Abbreviations.** DOF = degrees of freedom. BOM = bill of materials. EE = end effector. QDD = quasi-direct-drive actuator (low-ratio gear, backdrivable). NEMA 17/23 = 42/57 mm stepper frames. EG17 = StepperOnline planetary gearbox for NEMA 17. HTD/GT2/T5 = timing-belt tooth profiles. CPR = counts per revolution. LSB = one encoder count. arcmin = 1/60 degree. CAN = controller area network. PETG = print plastic, softens ~80 C. n/d = not documented in sources I could read. Grades: A built+documented+video+measured, B built+photos/docs, few numbers, C vendor claim, D render/hearsay.

## Bottom line

- **No hobby arm in the evidence is shown to hold 1.5 kg at 0.5 m with +/-1 mm.** PAROL6 documents 0.5 kg full-workspace; Thor 0.75 kg; SO-101 is 2.5-4.5x short on servo torque. AR4 (1.9 kg) and Arctos (2 kg) claim it but are vendor numbers, and AR4 is non-commercial licensed. OpenArm 2.0 (4.1 kg nominal) has the torque by a wide margin but no repeatability data and costs US$4.7-7k per arm.
- **Repeatability: claimed 0.1-0.2 mm (PAROL6, AR4) and 50 um (Dexter HD, output encoder); measured by anyone independent: none found.** Real limit is backlash: PAROL6's EG17 gearboxes are 15-20 arcmin = 2.2-2.9 mm at 0.5 m.
- **Mechanisms worth copying**: output-side absolute encoder (Dexter), switchless absolute zeroing (Dummy), tapered-roller pairs (PAROL6), belt-offset hollow cable path (Faze4), purchased 20 N.m actuator class (OpenArm). Details below.

## Method and limits (read first)

- Only GitHub was reachable (git clone, raw files, github.com issue pages). Vendor sites, Hackaday, Reddit, YouTube, Discord, forums, readthedocs and arXiv returned proxy 403 (EGRESS_BLOCKED). The session's WebSearch quota (200) was already used up after my first 4 queries (PAROL6, AR4, Arctos, Faze4); those results are snippets only and are tagged "snippet".
- So: primary evidence = repo docs, firmware, BOMs and issue threads. **I found no independent measurement of payload-at-reach or repeatability for any arm, so no arm earns grade A.** Videos and Discord were not viewable. Numbers marked "my calc" are derived by me from cited constants.
- "Zeus" and "Krabby" leads: no matching arm repo found (GitHub search: Krabby 0 results; Zeus = an InMoov-style hand, https://github.com/RoboTech-URJC). Dobot, Elephant, Interbotix vendor specs were not retrievable; commercial anchors are therefore thin (see end of Table 1A).

## Source key (all fetched 2026-10-02 unless marked snippet)

- P1 PAROL6 docs: https://github.com/Source-Robotics/PAROL-docs/blob/HEAD/docs/page2_2.md (specs, temps, ratios). P2 same repo page3_2.md (homing, belts, couplers). P3 page6.md (no brakes). P8 page3_1.md (control board).
- P4 BOM: https://github.com/PCrnjak/PAROL6-Desktop-robot-arm/blob/HEAD/BOM/BOM.md. P5 firmware: .../PAROL6%20control%20board%20main%20software/src/motor_init.cpp. P6 manual: .../Building%20instructions/Parol%20building%20instructions.pdf. P7 issues: https://github.com/PCrnjak/PAROL6-Desktop-robot-arm/issues?q=is%3Aissue+is%3Aclosed (#12, #15, #17, #18).
- A1 AR4 licence + firmware: https://github.com/Annin-Robotics/ar4-hmi (LICENSE.txt, Sketches/AR4_teensy41_sketch_v6.3). A2 ROS 2 driver firmware: https://github.com/Annin-Robotics/ar4_ros_driver (annin_ar4_firmware/AR4_teensy). A3 user issues: https://github.com/ycheng517/ar4_ros_driver/issues (#15, #17, #38, #50, #53, #55). A4 vendor specs, snippet: https://anninrobotics.com/docs/what-are-the-dimensions-and-key-specifications-of-the-ar4-mk3-robot/ . A5 MK5 sensors, snippet: https://www.hackster.io/news/chris-annin-calls-the-open-source-ar4-robot-arm-done-with-the-new-final-mark-5-revision-62b51e0ae555
- R1 Arctos vendor, snippet: https://arctosrobotics.com/6-axis-robot-arm-kit/ and https://hackaday.com/2023/05/08/arctos-robotics-build-a-robot-arm-out-of-3d-printer-spares/ . R2 https://github.com/Arctos-Robotics/ros2_arctos (issues #2, #7) . R3 https://github.com/ArctosRobotics/ROS
- F1 Faze4 docs: https://github.com/PCrnjak/Faze4-Robotic-arm (README, LICENSE, docs/B_Design_decisions.rst, docs/Electronics_PCB.rst). F2 BOM_7_11_2023.xlsx in the same repo. F3 issues (8, all closed, none mechanical).
- T1 Thor: https://github.com/AngelLM/Thor (README; issues #84, #90). M1 Moveo: https://github.com/BCN3D/BCN3D-Moveo (README, BOM pdf, issues #42, #56). D1 Dummy: https://github.com/peng-zhihui/Dummy-Robot (README, 2.Firmware/.../dummy_robot.cpp, issues #180, #204).
- S1 SO-ARM100/101: https://github.com/TheRobotStudio/SO-ARM100 (README, issues #170, #181). S2 LeRobot: https://github.com/huggingface/lerobot (tables.py, so_follower.py, issues #1296, #1333, #2074, #2819, #3400).
- O1 OpenArm: https://github.com/enactic/openarm (website/docs: overview/index.mdx, hardware/openarm-2.0/{general,motor}.mdx, purchase/index.mdx). O2 issues: https://github.com/enactic/openarm/issues (#255, #265, #287, #309, #323, #324, #430, #468, #471). O3 https://github.com/enactic/openarm_hardware/issues/15
- X1 Dexter HD wiki: https://github.com/HaddingtonDynamics/Dexter/wiki (Encoders, Joints, Hardware, Troubleshooting). X2 Lite 6 URDF: https://github.com/xArm-Developer/xarm_ros2/blob/HEAD/xarm_description/urdf/lite6/lite6.urdf.xacro
- Press snippet (PAROL6 0.08 mm, source page not fetchable): https://www.hackster.io/news/petar-crnjak-s-parol6-is-an-industrial-style-robot-arm-you-can-print-and-build-at-home-366866022a7b

## Table 1A: performance, cost, licence

| Arm | DOF | Reach | Payload claimed -> measured | Repeatability claimed -> measured | Cost (currency, date) | Licence | Build difficulty (my judgement) | Grade |
|---|---|---|---|---|---|---|---|---|
| PAROL6 (Source Robotics) | 6 | 400 mm with std gripper [P1] | 1 kg near base, 0.5 kg full workspace [P1] -> none | 0.1 mm [P1]; 0.08 mm [press snippet] -> none | BOM has no prices [P4]; kit price not retrieved | GPLv3 [repo LICENSE]; #12 "STLs violate GPLv3" closed [P7] | High: 80+ page manual, own PCB + ST-Link flash, inductive-sensor tuning [P2,P6] | B |
| AR4 MK3/MK5 (Annin) | 6 | 629 mm [A4 snippet] | 1.9 kg [A4] -> none | +/-0.2 mm [A4] -> none; drift/offset reports [A3 #53, #55] | not retrieved | Annin Non-Commercial v1.1: no selling robots, parts, kits or derivatives; CAD may not be redistributed [A1] | Medium (kits sold, Teensy, ROS 2) | C specs, B firmware |
| Arctos | 6 | 600 mm [R1 snippet] | 2 kg, ~10 kg arm [R1] -> none | n/d | kit from US$326, DIY from US$231 (2023-era articles, [R1]) | CAD in 4 formats; licence not retrieved; ros2_arctos Apache-2.0 [R2] | Medium: 168 printed PLA parts [R1] | C |
| Faze4 | 6 | n/d | n/d; arm 14-15 kg [F1] | n/d | <US$1000 (README), US$1000-1500 (docs) [F1]; 961 parts, 197 printed [F2] | LICENSE file = CERN-OHL-S v2 but README badge says MIT: conflict [F1] | High: ~1000 parts, cycloid tuning | B |
| Thor (AngelLM) | 6 | 625 mm stretched height [T1] | 750 g incl. gripper [T1] -> none | n/d | <EUR 350 hardware, date n/d [T1] | CC-BY-SA-4.0 [T1] | Medium | C |
| BCN3D Moveo | 5 + gripper | n/d | n/d | n/d | n/d | MIT [M1] | Low-medium; last commit 2016-10-03, 52 issues, many with 0 replies | C/D |
| Dummy (peng-zhihui) | 6 | n/d | n/d | n/d | Harmonic module ~CNY 600 used each; printed-cycloid "youth edition" target CNY 2000 (aspirational) [D1] | no LICENSE file found [D1] | High (CNC aluminium original) | B design, no numbers |
| SO-ARM100/101 (weak baseline) | 5 + gripper (6 servos) | n/d | n/d. Servo stall 16.5 kg.cm (7.4 V, at 6 V) or 30 kg.cm (12 V) = 1.62 / 2.94 N.m [S1] | n/d (#181 asks, unanswered) | US$121.94 follower parts, US$229.88 leader+follower, US column [S1] | Apache-2.0 [S1] | Low | B |
| OpenArm 2.0 (Enactic) | 7 + gripper | n/d in docs read | 4.1 kg nominal (1-min hold, worst posture), 6.0 kg peak (3 s move + 1 s hold), both incl. EE [O1] -> none | n/d: docs lack it, #255 open [O2] | US$4,699-7,080 per arm from vendors [O1 purchase]; site BOM tables sum to ~JPY 0.49 M per arm (my calc, JPY); #287 says ~US$3,000 vs advertised US$6,500 | hardware CERN-OHL-S-2.0, software Apache-2.0 [O1]; #265 discusses mismatch | Medium (CNC via Misumi + Damiao actuators; kits exist) | B |
| Dexter HD (Haddington) | 5 arm axes + wrist twist/grip | n/d | n/d | 50 um, step <10 um (wiki claim) [X1] -> none | n/d (BOM sheet only) | GPLv3 | High (FPGA, harmonic drive 9-12 wk lead [X1]) | C |
| Commercial anchors (Lite 6, myCobot 320, Dobot CR3/Nova, Elephant, RX-200) | | | not retrieved. Only fact: Lite 6 URDF joint effort limits J1-J6 = 50/50/32/32/32/20 N.m [X2] | not retrieved | ballpark US$3-7k (memory, D, verify) | closed | | D |

## Table 1B: drivetrain and electronics

| Arm | Reducer per joint (J1..J6) | Motors | Encoders / homing | Controller + firmware | Software |
|---|---|---|---|---|---|
| PAROL6 | J1 belt 6.4:1 (HTD3M 15T:96T); J2 EG17 planetary 20:1 (20 arcmin backlash); J3 EG17 20:1 x belt 38:42 = 18.1:1; J4 belt 4:1; J5 belt 4:1; J6 EG17 10:1 (15 arcmin) [P1,P4,P5] | 6x NEMA 17 only (16/45/65 N.cm); J2 = 65 N.cm, J6 = 16 N.cm [P4,P6]; open-loop | none. Inductive sensors J1/J4/J6, limit switches J2/J3/J5 [P2,P6] | own board STM32F446RE, 6x TMC5160, 32 microsteps, 24 V, USB + CAN [P1,P8]; C++ PlatformIO | Python GUI, Python API, ROS 2/MoveIt sim repo |
| AR4 | total ratios derived from firmware steps/deg, assuming the 4000-count/rev encoder comment applies to the motor shaft (my calc): J1 40, J2 50, J3 50, J4 44.8, J5 9.8, J6 20 :1; reducer types not retrievable (vendor BOM blocked) | steppers, frame sizes not retrieved | 4000-count quadrature encoder on every motor (motor side), used only to flag missed steps; limit switches, MK5 adds Hall on J1-J3 (snippet) [A1,A2,A5] | Teensy 4.1 + step/dir drivers, Arduino Nano gripper [A1] | Python/Tk HMI; ROS 2 Jazzy/Humble ros2_control + MoveIt; controller overrun above 25 Hz (#50) |
| Arctos | belts (GT2); reducer types n/d [R1] | NEMA 17 and 23 [R1]; MKS SERVO57D/42D closed-loop drivers over CAN [R2 #2, #7] | driver-internal | ESP32/Arduino [R1] | vendor GUI; Moveo-derived ROS 1 (rosserial) [R3]; ros2_arctos |
| Faze4 | J1 cyclo 15:1 x belt 5:3 = 25:1; J2 cyclo 27:1; J3 cyclo 15:1; J4 cyclo 11:1 x belt 28:26; J5 cyclo 11:1; J6 planetary 19.19:1; belts HTD 5M 10 mm [F1,F2] | 3x NEMA 23, 2x NEMA 17, 1x NEMA 14 + 19:1 gearbox [F2]; open-loop | none; limit switches + inductive sensors [F1,F2] | Teensy 3.5 + generic step/dir drivers (TB6600-class) + own PCB (v1 "alot of errors") [F1] | MATLAB (Corke toolbox), ROS URDF |
| Thor | printed gears + GT2 belts [T1] | steppers [T1] | none | Arduino Mega shield, GRBL/RRF G-code [T1] | Asgard GUI, ROS 2 |
| Moveo | T5 belts 16 mm; one 5:1 planetary [M1 BOM] | 2x NEMA 23 (112 mm), 2x NEMA 17, 1x NEMA 14 [M1 BOM]; open-loop | none | Arduino Mega + RAMPS 1.4 + TB6560 | Arduino sketch |
| Dummy | harmonic modules J1 50, J2 30, J3 30, J4 24, J5 30, J6 50 [D1 dummy_robot.cpp] | 42-class and 20 mm steppers with onboard closed-loop driver [D1] | single-turn absolute encoder at motor; homing by driving to hard stop at low torque, then fine zero inside the 360/30 = 12 deg window [D1] | STM32F405 FreeRTOS "REF" + CAN-bus Ctrl-Step drivers | DummyStudio (Unity), RoboDK driver |
| SO-101 | in-servo metal gear trains; follower 6x 1/345 [S1] | Feetech STS3215 7.4 V or 12 V | 12-bit (4096/rev) in servo [S2 tables.py]; homing by hard stops [S1 #170] | Waveshare bus-servo board, USB | LeRobot (Python) |
| OpenArm 2.0 | Damiao actuators: J1/J2 DM-J8009P 9:1; J3/J4 DM4340 40:1 (not QDD); J5-J8 DM-J4310 10:1 (J8 = gripper) [O1 motor.mdx] | rated/peak N.m: 20/40, 9/27, 3/7 [O1] | 2 magnetic 14-bit single-turn encoders per actuator [O1] | CAN-FD, USB2CANFD | openarm_can (C++), ROS 2, MuJoCo, Isaac, LeRobot |
| Dexter HD | J1-J3 harmonic 52:1; J4/J5 differential belts 90:16 [X1] | NEMA 17 0.9 deg, 16x microstep [X1] | absolute optical disc on the joint after the gearing (Joints page; Encoders page says "motor-integrated", ambiguous), ~1 M CPR; FPGA corrects stepped angle from it [X1] | Zynq FPGA + Linux, DexRun.c | DDE IDE, node web server |

## Table 2: documented failures

| Arm | Failure mode | Evidence |
|---|---|---|
| PAROL6 | Stepper heat vs plastic: 5 h holding 48-61 C, 2 h moving 52-73 C; PETG softens ~80 C; docs say reduce current for long use "or you risk destroying your robot" | P1; PETG note in Building instructions/PETG_printing.md |
| PAROL6 | No brakes, low ratios: arm falls on power loss; hand-turned steppers back-power the board | P3, P2 |
| PAROL6 | Coupler set screws loosen, joint slips; threadlocker + 24 h cure; belts on J1/J3/J4/J5 need tension checks and grease | P2 |
| PAROL6 | Over-torqued bearing-retainer screws cause friction; J1 beyond one turn damages cables; screw holes in printed parts wear if re-tapped (glue and re-tap) | P6 pp.10, 47, 80 |
| PAROL6 | BOM/CAD errata: wrong hole pattern J5/J4 pulley (#15), BOM outdated (#17, #18) | P7 |
| AR4 | Calibration drift over cycles while encoders still report home (motor-side encoder blind to downstream slip) | A3 #53 (open) |
| AR4 | MK3 calibration far off on J4-J6 (#15); Teensy calibration loop stuck, one joint stops ~90 deg short (#17); "failed to move to Joint Limits" (#38); ROS firmware ships per-joint offsets (1.2, -0.8 deg on J1, J2) for assembly tolerance | A3, A2 |
| AR4 | Missed-step trip is 50 motor steps = 0.45 deg at J2 (0.9 deg on MK1-3) = ~4.9 mm at 629 mm reach (my calc); not a precision guarantee | A1 (encOffset), A2 |
| AR4 | Laser crosshair shifts when Z moves 20 cm to 13 cm at constant XY | A3 #55 |
| Arctos | none found in readable sources (repo issues are feature requests) | R2, R3 |
| Faze4 | Author: all motors at joints is "not good", would move J3 to base; cheap drivers noisy; PCB v1 many errors. No backlash/wear report found | F1 |
| Thor | 5 mm rods do not fit 625ZZ bearings (#84); no mechanical-wear reports | T1 |
| Moveo | stepper sourcing pain (#56); dead repo | M1 |
| Dummy | zero-point procedure needs two steps (#204); stall-detect logic questioned (#180) | D1 |
| SO-101 | P gain 16 gives dead-band: same command lands differently by approach direction (#3400); wrist_roll instability, P 16->4 gave 37% improvement (#1333); gripper servo seized (#2819); gripper torque capped at 50% "to avoid burnout" in code; calibration relies on hard stops (#170) and overflows (#1296, 24 comments) | S2, S1 |
| OpenArm | J2 cable caught on bolt at output shaft and broke (#309); insulation worn through between J3 and J4, short circuit (#468); J4 connector hits spacer (#324); J2 only responds with CAN-FD (#471); 53-59 mm hand-pose error per stage of a pick pipeline, fixed offset on non-Cartesian paths (#430, cause unresolved); manual zero calibration error-prone (#323); CNC-unmanufacturable features in J2_A/J8_B (O3) | O2, O3 |
| Dexter | encoder LED/sensor displaced makes joints shake, squeal, lose position; wrong PSU voltage (needs 36 V) stalls | X1 Troubleshooting |
| All | printed-part creep, cycloid wear, belt-tooth jump under gravity load, 24/7 cable fatigue: **no quantified report found** (sources blocked); treat as untested | - |

## Joint geometry of the best three (+2 notes)

**PAROL6 (B).** Output bearings: NSK tapered-roller pairs, HR32907J on J1/J2, HR32906J on J3-J5; J1 also an AXK3552 needle thrust (35x52x4) between plates [P4,P6]. Preload is set only by tightening printed retainer/back-plate screws (no shim or nut), so it depends on plastic stiffness [P6]. J2: NEMA 17 (65 N.cm) + EG17 20:1 sits in the J1 turret and drives the shoulder shaft through a rigid set-screw coupler [P6, P2]. Cables: everything passes inside the links, 1 m leads per motor, J1 limited by an M3 screw blocker, J6 homes against a pin [P6, P2]. Weak links: J2/J3 (20 arcmin gearbox + coupler + plastic housing); J3 also has a 6 mm HTD3M belt in series with the planetary carrying elbow gravity torque; J4/J5 motor temps closest to PETG softening [P1].

**Faze4 (B).** Printed cycloid stages (11/15/27:1), two discs per stage, eccentric shafts on bearings; BOM lists 200x 3x8x4 and 40x 3x10x4 ball bearings (ring pins and belt tensioners, exact split not stated) [F1,F2]. The BOM bearings are thin-section deep-groove balls (35x47x7, 50x65x7, 15x28x7); no tapered or crossed-roller part is listed, so moment stiffness comes from the printed housing [F2]. Belt stages on J1/J4/J5 offset the axis so wiring passes through the body [F1]. No backlash number exists; "low backlash" is a claim.

**OpenArm 2.0 (B).** Purchased actuators carry the joint: DM-J8009P (98 mm OD, 896 g, 9:1, 20 N.m rated) on J1/J2, with cross-roller bearings where the joint is supported on one side [O1 motor.mdx]; two encoders per actuator. Cable path through the J2 rotation centre is the field failure (#309, #468). Weak link: wiring and calibration, not torque.

**Dummy (note).** Harmonic 24-50:1 + closed-loop stepper with absolute single-turn encoder; zeroing needs no switches (see What to take) [D1]. **Dexter HD (note).** Per its wiki the encoder sits on the joint after the harmonic drive, so reducer springiness is measured and corrected [X1].

## 1.5 kg at 0.5 m: torque sanity check (my calc)

Payload alone at the shoulder: 1.5 x 9.81 x 0.5 = **7.36 N.m**, before link mass, acceleration and a margin of ~1.5-2x.

| Arm | What its own numbers give | Verdict |
|---|---|---|
| PAROL6 | claim 0.5 kg x 0.4 m = 1.96 N.m. J2 holding torque 0.65 x 20 = 13 N.m (no efficiency, no speed loss): payload alone = 57% of holding torque; torque-angle deflection asin(0.57)/90 x 1.8 deg = 0.69 deg motor = 0.035 deg joint = 0.30 mm at 0.5 m, with no reserve for accel | No (claims 0.5 kg) |
| AR4 | claim 1.9 kg x 0.629 m = 11.7 N.m; motor/reducer at J2 not retrievable | Claimed yes, unverified |
| Arctos | 2 kg x 0.6 m = 11.8 N.m, vendor claim | Claimed yes, unverified |
| Thor | 0.75 kg incl. gripper | No |
| SO-101 | servo stall 1.62 N.m (7.4 V) / 2.94 N.m (12 V) vs 7.36 needed | No, 2.5-4.5x short |
| OpenArm | DM-J8009P rated 20 / peak 40 N.m = 2.7x / 5.4x the need; its 4.1 kg nominal is a 1-minute hold, not 24/7 | Yes on torque; duty unproven |
| Lite 6 (anchor) | URDF J2 limit 50 N.m [X2] = 6.8x | Yes (commercial) |

**Accuracy budget (my calc).** +/-1 mm at 0.5 m = +/-2.0 mrad = +/-6.9 arcmin total over all joints. One EG17 at 15 / 20 arcmin = 2.18 / 2.91 mm at 0.5 m, so one 20 arcmin joint gives 2.9 mm peak-to-peak lost motion on reversal against a 2 mm peak-to-peak (+/-1 mm) budget for the whole arm. PAROL6 step size (0.0028 deg at J2, 0.02 mm at 0.4 m) is not the limit; backlash and compliance are. Output encoder LSB at 0.5 m: 12-bit = 0.77 mm (SO-101 servo), 14-bit = 0.19 mm, 15-bit = 0.10 mm, 16-bit = 0.05 mm. AR4-style motor-side encoders cannot see belt or gear error at all.

## What to take

- **Encoder on the joint output, not the motor.** Dexter HD's wiki puts an absolute disc on the joint after the 52:1 harmonic drive and lets the FPGA correct the stepped angle [X1]; AR4's motor-side encoders still drifted with "encoder says home" (#53). Use >=15-bit absolute at the output of J2/J3 (0.1 mm) plus a motor-side encoder for commutation/stall.
- **Dummy zeroing trick.** Absolute single-turn motor encoder + low-torque push to a hard stop gives coarse zero, fine zero inside 360/N degrees; no switches, no machining sensitivity [D1]. Needs a real hard stop at every joint (SO-101 #170 failed without them).
- **Tapered-roller pairs for J2/J3 (PAROL6 HR32907J)**: cheap, real moment stiffness, beats thin ball bearings (Faze4). Add a metal lock-nut or shim for preload; do not rely on printed screws.
- **Belt only where gravity does not act**: PAROL6 J1 belt 6.4:1 + needle thrust, J4/J5 wrist belts. Keep belts out of J2/J3 load paths (PAROL6 J3 belt in series is the weak spot).
- **Offset belt stage to open a hollow cable path** (Faze4 J1/J4/J5); then route cables through the joint centre away from bolts with a service loop (OpenArm #309, #468).
- **Low-ratio planetary or QDD actuators are backdrivable** (PAROL6 falls at power loss, OpenArm is QDD): add holding brakes on J2/J3 from day one.
- **Damiao-class J8009P actuators** are the only fully documented 20 N.m part found; ~JPY 51k each on the OpenArm BOM (JPY 205,790 for 4). Candidate for J2/J3 if a printed reducer cannot be proven.
- **Thermal**: PAROL6 measured 73 C moving vs PETG ~80 C. Use metal motor/gearbox adapters and hold-current cuts.
- **Licences**: AR4 is non-commercial, so copy no AR4 file or firmware. GPLv3 (PAROL6, Dexter) and CERN-OHL-S (OpenArm, Faze4 file) are copyleft: copy ideas, not files. Moveo MIT is safe but obsolete.

## Documented failures -> rule

| Failure | Source | Rule for our robot |
|---|---|---|
| Position drift while encoder says home | A3 #53 | Absolute encoder on every joint output; compare with motor encoder, fault on mismatch above 0.05 deg |
| Missed-step trip too coarse (~5 mm) | A1 encOffset | Closed-loop servo, not step counting; tolerance set from the 6.9 arcmin budget |
| Backlash 15-20 arcmin = 2-3 mm | P4 gearbox slugs, my calc | J2/J3 reducer <=3 arcmin or output-encoder closed loop; measure on our rig before design freeze |
| Dead-band / approach-direction error | S2 #3400, #1333 | Tune gains at power-on; always final-approach from one direction; log dead-band in CI |
| Coupler set screw / belt slip | P2 | No set screws on load paths: clamp hub or keyed; no belts in gravity paths; threadlocker + torque stripe |
| Motor heat softens PETG | P1 | Thermal budget: motor surface <=60 C at 24/7; metal adapters; current derate table |
| Power loss drops arm | P3 | Spring-applied brake on J2/J3 (and J5 if loaded) |
| Cable wear, snag, short | O2 #309, #468 | Hollow-shaft routing, bend radius >=10x cable OD, strain relief, 1 M-cycle flex test |
| Calibration brittle, no stops | S1 #170, A3 #15/#17, O2 #323 | Hard stop per joint, single homing routine with timeout and abort, witness marks; store offsets in firmware |
| Systematic 50+ mm pose offset | O2 #430 | Kinematic calibration with a jig; verify URDF against measured link lengths |
| BOM/CAD errata, unmanufacturable features | P7, O3, T1 #84 | Build the first unit from our own CAD; do not trust upstream BOMs |
| Undocumented repeatability | O2 #255, S1 #181 | Publish our own dial-gauge/laser tracker data per arm, 1000 cycles, hot and cold |

## Open questions

1. Real backlash and wear of printed cycloid (Faze4) and EG-series gearboxes: nobody published it. Needs our own bench test (reversal error at 0.5 m).
2. AR4 reducer types, motor frames, price; Arctos reducers and licence: vendor sites were blocked. Re-run with open web.
3. Independent repeatability for PAROL6, AR4, OpenArm (Discord, YouTube, Reddit): not reachable.
4. Can PAROL6-style 65 N.cm steppers hold 7.4 N.m plus link mass without losing position at 24/7? Probably not (57% of holding torque for payload alone); a NEMA 23 or QDD shoulder is needed.
5. OpenArm DM-J8009P continuous duty at 7.4 N.m (37% of rated): thermal data missing; "nominal" is a 1-minute hold.
6. Harmonic-drive lead time and price at ~50:1, 1.5 kg class (Dexter notes 9-12 weeks for special order [X1]).
7. "Zeus" and "Krabby": not found; ask the requester for links.
