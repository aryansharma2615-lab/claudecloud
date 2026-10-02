# PROMPT A — FarmHand robot: research-heavy redesign for a 24/7 two-printer station

Paste into Claude Code from ~/Claude/PrintFarm:
> Read CLAUDE.md, then prompts/A_robot_redesign.md. Run PHASE 1 only and stop at GATE 1.

**Models:** `/model opus` for Phase 1 (research synthesis, architecture) and the physics loop.
`/model sonnet` for CAD scripting, URDF/AV plumbing and docs once the D-table is locked. Research
subagents on sonnet; link-checking subagents on haiku. `/clear` between phases (free).

**First, in one message, ask Shawarma what you can't measure yourself** (a cheap turn saves an
expensive redesign):
1. Table: width × depth × height (mm), what's under/behind it, wall or open on each side, outlets.
2. Printer placement: which side the H2S is on, gap between printers, printer front-edge offset
   from the table edge, room in front of the table (floor space for a rail/stand?).
3. Room: bedroom / garage / basement? Noise limit at night? Kids/pets nearby? (sets guarding and speed)
4. What SP prints most: typical part size and weight range, smallest part that must be picked.
5. Plates owned: how many H2S plates and Ender sheets, which surfaces.
6. Tools/skills: soldering yes; crimping? Willing to buy linear rails and aluminium extrusion?
Then check Claude memory (/areas/oneshot-arm.md, /topics/sp-inventory.md, /topics/workstation.md)
and Mem0 for anything already answered.

---

## Mission
Design the robot that keeps both printers running 24/7 with nobody home. Shawarma's verdict on
the OneShot gripper: "definitely ass, can be 10× better". The new one must handle very different
objects: finished parts, build plates, a door handle, a touchscreen, and later a 1.2 kg spool.
The result must look and work like an engineered product, not printed blocks bolted together.

## Requirements — every one gets a number before CAD
| # | Requirement | Target (refine with research; argue changes with numbers) |
|---|---|---|
| R1 | Station | H2S + Ender side by side on one table, from Shawarma's measurements |
| R2 | Jobs v1 | (a) clear finished parts from both beds into a bin (b) swap build plates on both printers: pull the full one, seat a clean one (c) open/close the H2S front door (d) tap touchscreen buttons on the H2S (capacitive) and the Ender (check its touch type) |
| R3 | Jobs v2 (design for now, build later) | 1.2 kg spools: restock the AMS 2 Pro, swap the Ender spool. Robot threading of the Ender extruder is research-hard; evaluate an auto-loader or a different feed instead |
| R4 | Payload | 1.5 kg at the farthest pose any job needs (spool + tool). v2 sets the motor class now so v1 isn't thrown away. If a rail or gantry makes spools much cheaper, prove it |
| R5 | Accuracy | Plate seating and screen taps ±1 mm at the tool; door ±3 mm; parts ±5 mm. Repeatability AND stiffness: deflection under load counts |
| R6 | Cycle time | Plate swap ≤ 3 min door-to-door (target, justify) |
| R7 | Reliability | 24/7: closed-loop position on every axis (encoders), homing, missed-step and collision detection, wear parts replaceable, no stalled-motor holds |
| R8 | Safety | 24 V-class motion can hurt fingers: hardwired E-stop, guarding or a speed/force-limited zone, enters a printer only when the printer reports idle + bed < 35 °C + toolhead parked + camera confirms. Write the robot rows of docs/SAFETY.md |
| R9 | End effectors | One system for parts, plates, door, screen, spool: tool changer vs multi-mode hand, decided by research. Must include a capacitive stylus finger (explain why a plastic finger can't trigger a phone-style touchscreen), self-centring compliant fingers, a plate tool, contact/force sensing |
| R10 | Vision | Wrist camera (eye-in-hand) + fixed overhead camera(s) + the printers' own cameras; AprilTag fiducials on each printer for automatic calibration. Evaluate reusing the ESP32-S3 OV2640 camera |
| R11 | Interfaces | Motion controller talks to the Windows PC (USB or Ethernet); firmware does real-time motion, the PC plans (Prompt B owns the PC side; agree the protocol with it) |
| R12 | Make it | Printed parts (Ender 220×220×270; H2S 340×320×340 from 2026-10-03, enclosed, so ASA / PETG-CF / PC become options: pick per part with /bambu-labs + /sp-print-dfm) + off-the-shelf steppers, drivers, reducers, rails, extrusion, bearings, M3/M4/M5 screws. No laser-cut/welded parts |
| R13 | Cost | "Whatever it takes", phased: Phase-1 buy list (parts + plates + door + screen), Phase-2 adds spools. Priced, linked, HAVE/BUY |
| R14 | Look | Integrated housings, hidden cabling, consistent fillets and fastener pattern (per /sp-research-first-design design language) |

---

## PHASE 1 — RESEARCH (/sp-research-first-design) → GATE 1
Run research subagents in parallel (sonnet). Each writes `docs/research/<topic>.md`: sources as
links, evidence quality (built + documented + video + measured beats renders), what to take,
what failed. Starting points below are names to verify, not facts.

1. **Print-farm automation that exists:** automatic plate changers/ejectors for Bambu printers
   (e.g. SwapMod, Jobox, 3DQue AutoFarm3D and similar), robot-arm-tended farms (UR / xArm / Dobot
   tending Prusa or Bambu), Formlabs Form Auto (how it removes parts). How each removes parts
   (flex, scrape, push-off, plate swap), cycle times, documented failures.
2. **Open-source arms in the 1–3 kg class:** PAROL6, AR4 (Annin Robotics), Arctos, Thor, BCN3D
   Moveo, Dummy (peng-zhihui), Faze4; SO-ARM100/101 as the weak baseline. Reducer per joint
   (cycloidal / planetary / harmonic / belt), measured repeatability, real payload, cost, failures.
3. **Station architectures:** (A) fixed 6-axis arm between the printers (B) arm on a linear rail
   along the table front (7th axis, the industrial machine-tending pattern) (C) cartesian gantry
   with a wrist (D) SCARA (E) per-printer add-on mechanisms + a small arm for door/screen.
   Score: payload at reach, repeatability, reach through the H2S door to the back of a
   340×320 bed, footprint, cost, build difficulty, safety, serviceability, look.
4. **End effectors:** tool changers (Jubilee, E3D, kinematic couplings, magnetic), adaptive
   grippers (fin-ray, linkage), suction on PEI, capacitive stylus robots (e.g. Tapster),
   door-opening strategies (hook, pull, magnet latch force).
5. **Printer specifics:** H2S door (hinge side, swing, latch force, handle), plate weight,
   alignment pins/edges, how the bed is presented after a print and how to command its height;
   Ender sheet alignment and presenting the bed forward with G-code; both touchscreens' type and
   button sizes; AMS 2 Pro spool loading geometry (v2).
6. **Motion hardware:** closed-loop NEMA 17/23 (e.g. MKS SERVO42D/57D and alternatives), drivers
   (TMC2209 / TMC5160), output-side encoders (AS5600 / AS5048A), controllers (Teensy 4.1,
   ESP32-S3, STM32), planning stacks (ROS 2 + MoveIt on Windows vs a Linux box vs a lean Python
   IK/planner).

Then, before any geometry:
- **Failure table:** each documented failure → the rule it creates (D-row seed).
- **Architecture comparison** of at least 3 options → pick, with the numbers that decided it.
  Never pick a mechanism because it is easy to model.
- **First torque pass:** τ = m·g·d at the worst pose for the 1.5 kg case and for a plate,
  per joint → motor + reduction class, checked against the 50 % hold / 70 % move rules
  (for scale: a 1.2 kg spool held 0.5 m out is ~60 kg·cm, about 33 SG90 servos at stall).

**Deliverables:** docs/RESEARCH.md (tables + failure list + links), docs/ARCHITECTURE_ROBOT.md
(the pick + why + a diagram), docs/BOM_draft.md (priced Phase-1 buy list), questions for Shawarma.

### GATE 1 — STOP
Show in ≤ 15 lines: the pick, the runner-up and why it lost, the headline torque numbers, the
end-effector concept, the Phase-1 buy total, and open questions. No CAD until Shawarma approves.

---

## PHASE 2 — DESIGN → GATE 2
Load and follow in order: /sp-design-brief → /sp-engineering-design → /sp-print-dfm →
/sp-design-decisions. Also /cad, /step-parts, /implicit-cad (for organic housings), /urdf, /sdf.
- **Interface brief:** printer envelopes from measurements (doors and their swing, plate paths,
  screens, AMS), table mounting, cable chains, controller enclosure, E-stop location.
- **Physics loop:** masses from CAD; torque at every pose on the job grid (every plate, door,
  screen and spool pose); reducer efficiency measured or conservative; stepper torque derated
  for supply voltage and speed; hold ≤ 50 %, move ≤ 70 %; tool deflection under load ≤ the R5
  budget; bearing loads. Write design/DESIGN_LOOP.md every iteration.
- **Scripted CAD** (build123d, cad/params.py single source of truth) → STEP + STL, each part
  tagged with the printer and material it's made on and why.
- **URDF + PyBullet:** inverse dynamics vs hand calc within ~15 % (hand calc higher), hold test
  with 1.5 kg (sag ≤ 1 mm at the tool), every job path simulated against printer models with 0
  collisions, including the door swing as a moving obstacle.
- **DFM harness:** 0 clashes through the motion range, watertight single solids, bed fit per
  printer, insert and screw access.
- **Electrical:** 24 V PSU sizing, E-stop chain, fusing, wire gauge vs current, drop < 3 %.
- **Firmware outline** for the motion controller (Prompt B finishes it).

**Deliverables:** cad/, design/DESIGN_LOOP.md, urdf/, sim/SIM_REPORT.md, docs/DFM_REPORT.md,
docs/DESIGN_DECISIONS.md (numbering starts at D201), docs/BOM.md.

### GATE 2 — STOP
Headline numbers (before → after where it applies), anything that failed a rule, the final buy list.

---

## PHASE 3 — ASSEMBLY VIEWER + BUILD SHEET
/cad-assembly-viewer → /sp-assembly-viewer, with /dataviz, /artifact-design, /artifact-diagramming.
- Build on the SP engine in ~/Claude/AV (viewer_template_motion_v5_2.html, patch_engine_v5_2.py,
  verify_av_v3.py). Read AV_FEATURES.md, CONFIG_SCHEMA.md and CHECKPOINT.md first.
- Every screw drawn from the side it goes in; Motion lane with the real job paths (plate swap ×2,
  door, screen tap, part clear, spool v2) as through-moves; printers as ghost envelopes; Load vs
  stall; wiring lane; BOM drawer with HAVE/BUY and ×10/×50/×100; 3MF plates per printer.
- **Ratchet:** leave the engine better (likely: a prismatic rail joint in the Path, tool swaps in
  the Path, the door as a moving obstacle) + an AV_FEATURES.md entry. verify_av_v3 must PASS;
  look at the screenshots. Never edit the template by hand: anchored patch → new versioned template.
- **Build sheet:** ~90 % visual (research cards, the architecture pick, torque and %-of-stall
  charts, end-effector exploded views, phased buy list).
- Publish both as artifacts.

## Definition of done
A robot design Shawarma can buy for and print with confidence: every number traceable, every
job path simulated clean, every screw fit-checked, a priced phased BOM, and a viewer and build
sheet he can read on his phone next to the printers.
