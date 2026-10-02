# Station architectures: which mechanism family tends a two-printer table

FarmHand research, subagent report, 2026-10-02. Scope: options A-E for tending a Bambu Lab H2S (enclosed, front door, 340x320 mm plate) plus a Creality Ender 3 S1 Pro (open bed-slinger, 220x220 mm sheet). No winner is picked here; the lead engineer scores it.

## 0. Method, limits, evidence grades
- Evidence grade: **A** built + documented + video + measured; **B** built + photos/video, few numbers; **C** vendor spec; **D** render/hearsay. **C\*** = a vendor/trade number seen only in a web-search summary of the cited page; I could not re-read the page (see next line), so treat as unverified at source.
- Tooling limits this session: WebFetch only reached github.com (every other domain returned 403 from the egress proxy), and the session's 200-call WebSearch budget ran out after about 40 queries of mine. Verified-by-reading sources are S1-S9 (GitHub files and code). S10-S33 are search-summary based. Quantified "reach depth into a machine door" rules from industry were NOT found; section 1 is reasoning.
- Cost class (CAD-equivalent, FX not looked up, bins wide enough that +-10 % FX does not change the class; amounts are in the source currency on 2026-10-02): **C1** under 1k, **C2** 1-5k, **C3** 5-20k, **C4** over 20k.
- Acronyms: SCARA = Selective Compliance Assembly Robot Arm; TCP = tool centre point (the gripper's working point); CAD = Canadian dollars; USD / EUR = US dollars / euros; um = micrometre; CRX = Fanuc's cobot (collaborative robot) line; UR = Universal Robots; PF = Brooks/Precise Automation PreciseFlex; RTU / CTU = Fanuc / Thomson robot (cobot) transfer unit, i.e. a 7th-axis rail; URCap = UR plug-in for external axes; ISO/TS 15066 = technical specification for collaborative-robot force/pressure limits; AMS = Bambu's filament changer; SBS = standard microplate format; EE = end effector; BOM = bill of materials; G-code = printer motion commands; CoreXY = belt layout where two motors drive both X and Y; NEMA 17 = 42 mm stepper-motor frame size; TMC2130 = stepper-driver chip; AR4 = Annin Robotics' open-source 6-axis arm; WPI MQP = Worcester Polytechnic Institute Major Qualifying Project; CHI = the Computer-Human Interaction conference.

## 1. Job geometry used for scoring (REASONING, not a source; inputs from the brief; "assumed" = must be measured)
| Quantity | Value | Basis |
|---|---|---|
| Plate slide inside H2S | at least 320 mm level, straight, in/out through the door | brief: 340x320 plate, bed depth 320 |
| Gravity torque, 1.5 kg held 0.5 m out | 7.4 N*m (75 kg*cm); 1.2 kg spool: 5.9 N*m | m*g*d; a gantry/SCARA Z axis instead sees only 14.7 N (1.5 kg) |
| Cantilever moment, 1.5 kg at 0.34 m on a gantry Y carriage | 5.0 N*m on the bearings (not the motor) | m*g*d |
| Lead-screw lift torque, 14.7 N, 8 mm lead, assumed 40 % efficiency | 0.047 N*m | F*lead/(2*pi*eta) |
| Entry rule | the forearm must cross the door plane inside the aperture. With wrist depth inside dw = 340 - T (T = wrist-to-TCP tool length), base lateral offset L from the door centre, standoff f in front of the door plane: crossing = L*dw/(dw+f) | geometry |
| Example, aperture half-width 200 and forearm half-thickness 50 mm (both assumed) | L=0 (rail or front-centre): f=0, TCP radius 340. L=250, T=162: f>=119, radius 522. L=250, T=340: f=0, radius 422. L=350, T=162: f>=237, radius 675 | computed; T=162 is the PF400 gripper length [S1] |

Takeaway (reasoning): a base "between the printers" needs either a long plate fork (T near 340), a standoff in front of the door plane, or reach of 520-680 mm; a base on the door axis (rail, front pedestal, gantry) needs none of that.

## 2. Summary (details and sources in sections 3-7)
| | A fixed 6-axis | B 6-axis on rail | C cartesian gantry + wrist | D SCARA | E add-ons + small arm |
|---|---|---|---|---|---|
| Payload documented | printed 0.5-0.75 kg [S4,S5]; industrial 10 kg [S27] | arm's own, rail adds carriage load | 10 kg-class kits [S29] | 0.5-3 kg [S10,S12,S16] | n/a per mechanism |
| Repeatability documented | 0.1 mm printed [S4]; +-0.04 mm industrial [S27] | +-25 um/m rail [S26], 0.05-0.1 mm [S25] | 0.01-0.05 mm [S29] | +-20-90 um [S10,S16]; printed 0.4 mm [S32] | not documented |
| Cost class | printed C1-C2; industrial C4 | add C1-C2 (maker) | C2 maker; C3 industrial | C3 (used PF400, new M1 Pro) | C1-C2 |
| Best evidence | built, small payload | built (DHR, 40+ printers) | built (Jubilee) | built (PF400 plates into instruments) | built for door/eject only |

## 3. (A) One fixed 6-axis arm between the printers
| Real example | Numbers | Grade | Src |
|---|---|---|---|
| PAROL6 (printed desktop arm, open-loop steppers + limit switches) | payload 1 kg near base, 0.5 kg across workspace; reach 400 mm; repeatability 0.1 mm; 5.5 kg | B | [S4] |
| Thor (printed, belts/gears) | payload 750 g including EE; 625 mm tall; hardware under 350 EUR | B | [S5] |
| Faze4 (printed cycloidal gearboxes) | under 1000 USD; about 1000 parts; 15 kg; payload NOT documented | B | [S6] |
| Fanuc CRX-10iA/L (industrial cobot, machine tending) | payload 10 kg; 40 kg arm; repeatability +-0.04 mm | C\* | [S27] |
| WPI 2017 student farm | Fanuc 200iB pulled plates, parked prints on a cooling rack, fitted new plates | B (abstract only) | [S20] |
| Industry guidance | 6-axis can reach around/over/under obstacles to approach machine doors at various angles | C\* | [S31] |

| Attribute | Finding |
|---|---|
| Payload at reach | No printed 6-axis in my sources reaches 1.5 kg at reach (best: 1 kg near base, 0.5 kg full workspace) [S4,S5]; torque need 7.4 N*m at 0.5 m (reasoning). |
| Repeatability | 0.1 mm claim for printed [S4]; +-0.04 mm industrial [S27]; printed-reducer backlash/deflection not documented. |
| Workspace / footprint | Spherical shell with a dead zone at the base; PAROL6 5.5 kg, Faze4 15 kg, CRX 40 kg [S4,S6,S27]; base dimensions not documented. |
| Cost class (CAD-eq., USD/EUR 2026) | Maker C1-C2 (Faze4 under 1000 USD, Thor under 350 EUR) [S5,S6]; industrial C4 (mid-payload 6-axis 50k-110k USD, 2026 trade range) [S31]. |
| Maker build / serviceability | Faze4 about 1000 parts [S6]; PAROL6 limit-switch homing, no collision sensing documented [S4]; repair claim "easy" is the author's (D). |
| Collaborative safety | Industrial CRX is a cobot [S27]. Printed arms: only advice to use the E-stop [S4]; every joint is a pinch point (reasoning). |
| 340 mm level slide through door | Needs 3-4 coordinated joints and wrist roll to keep the plate level; base between printers needs standoff/reach per section 1 (PAROL6 reach 400 mm is below the 422-675 mm radii). |
| 1.2 kg spool lift | Shoulder/elbow motors hold m*g*d (5.9 N*m at 0.5 m, reasoning); documented printed payloads are 2-3x too low [S4,S5]. |

**Pros:** (1) one arm covers both printers, door, screens and AMS from one base, any wrist angle [S31]; (2) industrial precedent with +-0.04 mm and cobot safety [S27]; (3) cheapest per capability for makers, open files plus ROS (Robot Operating System) stacks [S5,S6].

**Cons:** (1) documented printed payload 0.5-0.75 kg vs 1.5 kg need [S4,S5]; (2) a level straight slide costs coordinated joints, and gravity torque grows with reach (section 1); (3) industrial 6-axis is C4 [S31] and printed arms have no documented collision/force limiting [S4].

## 4. (B) 6-axis arm on a linear rail along the table front (7th axis)
How a rail is specified (from the sheets below): stroke (travel), carriage load or compatible robot, repeatability (mm or um per m), max speed, duty cycle, drive type (belt, ball screw, rack and pinion), controller hook (URCap / robot controller treats it as an external axis), mounting (floor, wall, inverted).
| Real example | Numbers | Grade | Src |
|---|---|---|---|
| Thomson Movotrak CTU under Fanuc CRX ("first collaborative 7th axis") | stroke to 10 m; repeatability +-25 um per m of stroke; speed to 1 m/s; user-set collision detection; freedrive teaching | C\* | [S26] |
| Fanuc modular RTU (big robots, not our class) | repeatability +-0.02 mm; stroke to 20 m; payload up to 2000 kg | C\* | [S27] |
| Vention 7th axis for UR3e-UR30 (URCap, MachineMotion controller) | drives: timing belt, ball screw, rack and pinion, belt-rack; travel options from 610 mm (one UR10 design listed at 6685 mm length); 2 m version 2543 x 659 mm footprint; repeatability/payload NOT in retrieved text | C\* | [S24] |
| Cobotracks LMK10 for UR10 | ALU-B: 7000 mm, 250 mm/s, 0.1 mm; ALU-BS: 2500 mm, 250 mm/s, 0.05 mm; 100 % duty | C\* | [S25] |
| Annin AR4 7th axis (user builds) | extra driver; igus cable chain; rail pose is stored with each taught move but is NOT in the kinematics; any direction/rotation | B | [S28] |
| DHR Engineering print farm | custom robot on rail + bed racks; pages report 20, 40+ and 44 printers; added Bambu H2D in under 24 h by swapping gripper jaws; payload/precision NOT documented | B | [S19] |

| Attribute | Finding |
|---|---|
| Payload at reach | Unchanged from the arm (rail only moves the base); rail carriage must also carry the arm (CRX 40 kg [S27]). |
| Repeatability | Rail 0.02-0.1 mm class [S25,S26,S27]; stack-up with arm well under 1 mm (reasoning). |
| Workspace / footprint | Arm sphere swept along a line; Vention 2 m rail 2543 x 659 mm [S24]; rail length is about table width; floor depth about 0.66 m if free-standing. |
| Cost class | Rail prices not retrieved; maker rail = extrusion + linear guide + belt/screw + motor + chain, C1-C2 (reasoning); industrial arm + rail C4. |
| Maker build / serviceability | AR4 users add one driver + chain [S28]; adds homing, hard stops, cable chain wear (reasoning). |
| Collaborative safety | Moving base adds a crush/shear line along the rail; Thomson sells collision detection on the axis [S26]; PF rail runs cables inside [S14]. |
| 340 mm level slide through door | Rail parks the base on each door axis, so entry is straight (section 1, L=0); arm needs only about 340 mm + wrist reach. |
| 1.2 kg spool lift | Same joint-torque problem as A; rail can park the base next to the AMS to shorten reach (reasoning). |

**Pros:** (1) straight-in approach to each door from taught stops [S28,S26]; (2) real print-farm precedent: DHR rail robot serving 40+ printers incl. H2D [S19]; (3) off-the-shelf cobot rails exist at 0.05-0.1 mm [S25,S26].

**Cons:** (1) one more axis, chain and long thin footprint [S24]; (2) arm still carries every A problem (payload at reach) [S4]; (3) economics favour 5+ machines, we have 2 [S31] and rail pose is not in the kinematics (AR4) [S28].

## 5. (C) Cartesian gantry with a small wrist
| Real example | Numbers | Grade | Src |
|---|---|---|---|
| Jubilee (CoreXY gantry + automatic tool changer) | 300 x 300 x 300 mm; about 1350 USD without tools; "non-loadbearing" applications; tool-change repeatability under 40 um (kinematic coupling) | B (README read; 40 um via CHI-paper summary) | [S3,S33] |
| Science Jubilee (labware handling) | deck holds up to 6 standard microplates; pipettes/syringes/cameras | B | [S8] |
| Opentrons Flex (gantry lab robot with a labware gripper) | code shows jaw-width calibration and a grip-force profile; payload/repeatability NOT retrieved | B (code only) | [S9] |
| Generic XYZ kit | 2000 x 2000 x 1000 mm, 10 kg, 0.5 mm, steppers + encoders | C\* | [S29] |
| Cartesian drive classes | ball screw +-0.01 mm; belt +-0.05 mm; ball-screw axes place 50 kg within 10 um | C\* | [S29] |
| Overhead gantry loaders (CNC) | load/unload in 10-14 s; up to 2 m/s; enter machines through automatic doors | C\* | [S30] |

| Attribute | Finding |
|---|---|
| Payload at reach | Kits 10 kg [S29]; Jubilee says non-loadbearing [S3]; 1.5 kg at 0.34 m is 5.0 N*m on carriage bearings (section 1). |
| Repeatability | 0.01-0.05 mm class [S29]; tool plates under 40 um [S33]. +-1 mm is easy; stiffness is the limit. |
| Workspace / footprint | Rectangular box (matches table and plate slides); cannot reach round corners; frame spans both printers plus overhang, dimensions not documented. |
| Cost class | Maker C2 (Jubilee 1350 USD frame) [S3]; industrial cartesian axes 5k-15k USD, 2026 [S31] = C3. |
| Maker build / serviceability | Closest to printer building: belts, rails, steppers, Duet/G-code control, Discord community [S3]; commodity parts. |
| Collaborative safety | Moving bridge/carriage pinch; industrial gantries are normally guarded [S30]; force limiting only via stall/following-error (reasoning). |
| 340 mm level slide through door | Natural: Y axis straight in; needs Y stroke at least 340 mm + clearance and a low-profile plate fork that clears the door aperture (reasoning). |
| 1.2 kg spool lift | Plain Z axis; screw holds load unpowered; 14.7 N, 0.047 N*m (section 1). |

**Pros:** (1) straight axes match plate slide, simplest accuracy model, 0.01-0.05 mm class [S29]; (2) lowest maker difficulty and cost (Jubilee about 1350 USD, documented) [S3]; (3) spool lift is trivial Z with payload headroom [S29].

**Cons:** (1) "non-loadbearing" rating of the reference design [S3]; (2) no tilt/reach-around: screens and AMS slot need extra wrist axes (reasoning); (3) frame spans both printers, occupying table and blocking access, no cobot-safe precedent found [S30].

## 6. (D) SCARA (vertical-axis arm, stiff in Z, selectively compliant in the horizontal plane)
| Real example | Numbers | Grade | Src |
|---|---|---|---|
| Brooks/Precise Automation PF400 (lab plate handler) | arm links 225+210 mm (standard) or 302+289 mm (extended), gripper 162 mm; reach 433/588 mm arm-only, 579/734 mm with gripper (another sheet: 576/731); Z 400/750/1160 mm; about 20 kg (400 Z); repeatability +-90 um; speed 500 mm/s at 0.5 kg; payload 0.5 kg with servo gripper, 1.2 kg bare (3 kg Z-version: 2.5 kg); one sheet says 1 kg incl. gripper | C\* + code | [S1,S10,S11] |
| PF400 plate handling | grips SBS plates landscape or portrait; Z column reaches racks, hotels and stacked instruments; controller embedded; absolute encoders | C\* | [S10,S11] |
| PF3400 | reach 587 mm; 3 kg incl. gripper (2.5 kg with 0.5 kg gripper); +-90 um; 1.5 m/s horizontal; collisions under 100 N free space, 150 N rigid; ISO/TS 15066, no shielding claim | C\* | [S12,S13] |
| PF rail for PF400/PF3400 (hybrid D+B) | 1.0/1.5/2.0 m; +-50 um; 700 mm/s; cables inside | C\* | [S14] |
| Dobot M1 Pro | 1.5 kg; +-0.02 mm; 400 mm reach; 15.7 kg; 5,990 USD / 4,620 EUR | C\* | [S16] |
| Dobot MG400 | 750 g; 440 mm; +-0.05 mm; 190 x 190 mm base; 8 kg; reported collision threshold under 12 N | C\* | [S17] |
| Printed SCARA | PyBot measured 0.4 mm (0.2 mm tuned; its payload claim conflicts, so not adopted); EduSCARA +-3.5 mm with hobby servos, 100 g; PR3 uses 4 NEMA 17 + belts; Z by 8 mm lead screw on 10 mm rods | B | [S32] |
| Dobot M1 Pro vs Bambu X1C (YouTube series) | opened the door; could not solve plate removal; scope changed to vacuum part pick-up | B | [S18] |

| Attribute | Finding |
|---|---|
| Payload at reach | PF400 0.5-1.2 kg, M1 Pro 1.5 kg at 400 mm, PF3400 3 kg [S10,S12,S16]. Spool + gripper (about 1.5 kg) exceeds PF400 and leaves M1 Pro no margin (whether its 1.5 kg includes the gripper: not documented). |
| Repeatability | +-20-90 um industrial [S10,S16]; printed 0.4 mm best measured, 3.5 mm hobby servos [S32]. |
| Workspace / footprint | Annulus about the shoulder x Z column; gripper stays level, yaw only, no tilt [S1]; M1 15.7 kg, MG400 190 x 190 mm base [S16,S17]. |
| Cost class | Used PF400 12,995-15,999 USD (C3) [S15]; new M1 Pro 5,990 USD (C3) [S16]; industrial SCARA 10k-60k USD [S31]; printed not documented. |
| Maker build / serviceability | Three vertical joints + belts + Z screw; PF400 firmware collision stop then power-drop recovery [S2]; printed SCARA evidence is thin [S32]. |
| Collaborative safety | PF3400 under 100/150 N [S13]; vertical axes mean the elbow link pair is the pinch point (reasoning). |
| 340 mm level slide through door | Best fit: level wrist, planar reach, closest industrial analogue (plates into instruments) [S10,S11]; between printers with a 162 mm tool needs 522 mm (L=250) to 675 mm (L=350) radius (section 1): standard PF400 (579 mm with gripper) covers the first, extended (734 mm) both. |
| 1.2 kg spool lift | Z column lifts it; motors do not hold gravity on the revolute joints (reasoning); payload sheets above are the limit. |

**Pros:** (1) closest analogue: PF400/PF3400 move plates into instruments with level wrist and +-90 um [S10,S11,S12]; (2) only the Z axis carries weight (reasoning) and a rail option exists [S14]; (3) low-cost small SCARAs exist (M1 Pro 5,990 USD) with force-limited variants [S13,S16].

**Cons:** (1) payload falls as reach grows (PF400 0.5 kg with gripper) [S10]; (2) no tilt/roll, awkward for spools at angles and angled screens (reasoning); (3) the only M1-on-Bambu attempt stalled at plate removal [S18] and printed SCARAs measured 0.4-3.5 mm [S32].

## 7. (E) Per-printer add-on mechanisms + a small arm only for door and screen
| Real example | Numbers | Grade | Src |
|---|---|---|---|
| 3DQue AutoFarm3D door opener | fits P1S/P2S/X1C/X1E/H2S/H2D/H2C; 129 USD kit with door opener + frictionless bed surface | C | [S22] |
| Prusa MK3 chain-production ejector | about 100 USD BOM; 2x NEMA 17, 2020/3030 extrusion, 2x Arduino, TMC2130 | B | [S7] |
| PrintFlow3D plate changer; A1 mini maker changer | up to 11 plates on A1, no firmware change; G-code lifts plate off, stack behind the printer | C / B | [S23] |
| Swapmod plate switching | supported by SimplyPrint AutoPrint; fit for H2S or Ender S1 Pro NOT documented | B | [S21] |

| Attribute | Finding |
|---|---|
| Payload / repeatability | Per mechanism, not documented; no H2S plate changer found in retrieved sources (only door + eject). |
| Workspace / footprint | Each mechanism lives on its printer (plate stack behind an A1 mini [S23]); table footprint grows per printer. |
| Cost class | C1 per printer (129 USD kit, about 100 USD ejector BOM) [S22,S7]; plus small arm C1-C2 (reasoning) = C2. |
| Maker build / serviceability | Two printers = two bespoke mechanisms to design and maintain; Bambu firmware coupling [S23] (reasoning on risk). |
| Collaborative safety | Small low-energy actuators; the arm for door/screen can be tiny (reasoning). |
| 340 mm level slide / spool | Printer's own bed motion does the work in the A1 mini example [S23]; spool lift not covered (DHR uses a spool carousel + robot [S19]). |

**Pros:** (1) cheapest per function: 129 USD door+eject kit, about 100 USD ejector [S22,S7]; (2) low-energy parts, easiest safety case (reasoning); (3) printer geometry does the reaching [S23].

**Cons:** (1) no H2S plate swapper or Ender S1 Pro swapper found; both must be invented [S22,S23]; (2) two bespoke designs + a third arm, with door-only kit not solving plates or spools [S22]; (3) v2 spools still need a robot or carousel [S19].

## 8. Hybrids and reaching into enclosed machines
| Hybrid / topic | Evidence |
|---|---|
| SCARA on a Z column on a horizontal rail | Commercial: PF400 Z column 400/750/1160 mm [S11] + 1-2 m rail [S14]; the PyLabRobot kinematics models SCARA + Z + rail x-offset [S1]. Grade C\*. |
| 6-axis on rail | CRX on Thomson CTU [S26], UR on Vention/Cobotracks [S24,S25], AR4 [S28], DHR print farm [S19]. |
| Gantry with rotary wrist | CNC overhead gantries with automatic doors [S30]; Jubilee tool plates have no wrist [S3]. A stationary arm acting "like a gantry" with a wedge wrist is a D-grade wiki item [S21]. |
| Industrial reach into a door | Retrieved: 6-axis approaches doors at many angles [S31]; rail-mounted CRX reaches machine doors [S26]; gantry loaders use automatic doors [S30]. NOT retrieved: depth, clearance, wrist-orientation rules. Use section 1. |

## 9. Sources (all retrieved 2026-10-02; S1-S9 read directly, S10+ via search summary)
| ID | Source | URL |
|---|---|---|
| S1 | PyLabRobot PF400 kinematics (link lengths, level gripper, rail) | <https://github.com/PyLabRobot/pylabrobot/blob/main/pylabrobot/brooks/precise_flex/kinematics.py> |
| S2 | PyLabRobot PF400 driver (collision, recovery) | <https://github.com/PyLabRobot/pylabrobot/blob/main/pylabrobot/brooks/precise_flex/precise_flex.py> |
| S3 | Jubilee README | <https://github.com/machineagency/jubilee> |
| S4 | PAROL6 spec page; E-stop advice page | <https://github.com/Source-Robotics/PAROL-docs/blob/HEAD/docs/page2_2.md>, <https://github.com/Source-Robotics/PAROL-docs/blob/HEAD/docs/page3_2.md> |
| S5 | Thor README | <https://github.com/AngelLM/Thor> |
| S6 | Faze4 README | <https://github.com/PCrnjak/Faze4-Robotic-arm> |
| S7 | Prusa chain-production ejector | <https://github.com/d-weber/prusa-chain-production> |
| S8 | Science Jubilee README | <https://github.com/Jubilee-CSL/science_jubilee> |
| S9 | Opentrons gripper code | <https://github.com/Opentrons/opentrons/blob/HEAD/api/src/opentrons/hardware_control/instruments/ot3/gripper.py> |
| S10 | PF400 sheet / QVIRO | <https://qviro.com/product/brooks-automation/pf400/specifications>, <https://www.brooks.com/getmedia/3dd476e9-9925-41b4-b17f-0336f29e8bfa/PreciseFlex-400.pdf> |
| S11 | PF400 reach, Z, plates (UK Robotics, Dynamic Solutions datasheet) | <https://ukrobotics.com/devices/pf400-robot/>, <https://www.dynamicsolutionsusa.com/docs/collaborative_robots/PreciseFlex_400%20Datasheet.pdf> |
| S12 | PF3400 sheet | <https://howtorobot.com/sites/default/files/2023-01/PreciseFlex%203400%20Technical%20Specifications.pdf>, <https://www.brooks.com/preciseflex-robots/preciseflex-3400/> |
| S13 | PF3400 collaborative forces | <https://www.automation.com/en-us/products/product03/precise-automation-introduces-pf3400-industrial-co>, <https://ctemag.com/products/pf3400-industrial-collaborative-scara-robot/> |
| S14 | PF linear axis | <https://www.copiasci.com/microplate-handlers/robotic-arm/components>, <https://www.labx.com/item/precise-automation-linear-axis-rail-for-pf400-1m/13998110> |
| S15 | PF400 used listings | <https://www.labx.com/item/preciseflex-arm-pf400/scp-222003-6f34eadd-5c2f-4965-b37c-ab787fb6ea03> |
| S16 | Dobot M1 Pro | <https://unchainedrobotics.de/en/products/robot/industrial-robot/dobot-m1-scara-roboter>, <https://openelab.io/products/dobot-m1-pro-scara-robot> |
| S17 | Dobot MG400 | <https://rbtx.com/en-US/components/robots/dobot-mg400-desktop-collaborative-robot>, <https://dobot.si/wp-content/uploads/2025/07/MG400-Datasheet.pdf> |
| S18 | Dobot M1 on X1C | <https://forum.bambulab.com/t/dude-on-youtube-trying-to-build-an-x1c-automaton-robot/8098>, <https://www.youtube.com/watch?v=DXR6LVIS1cs> |
| S19 | DHR Engineering | <https://dhr.is/projects/3d-print-farm-automation>, <https://dhr.is/blog/automated-3d-printer-bambuh2d>, <https://dhr.is/projects/automated-filament-spool-swapping-3d-print-farms> |
| S20 | WPI MQP automated farm (2017) | <https://digital.wpi.edu/downloads/8p58pf525?locale=en> |
| S21 | Swapmod / robot ideas | <https://hackaday.com/2024/09/30/3d-printer-swaps-build-plates-to-automate-print-jobs/>, <https://simplyprint.io/features/autoprint>, <https://wiki.opensourceecology.org/wiki/Open_Source_Automated_Printed_Part_Remover> |
| S22 | 3DQue AutoFarm3D | <https://shop.3dque.com/products/autofarm3d-door-opener-for-bambu-lab-p1p-x1c-x1e-pre-sale>, <https://www.tomshardware.com/3d-printing/new-auto-ejection-tool-for-bambu-lab-print-farms-automatically-ejects-finished-3d-prints-from-the-machine-usd129-kit-includes-auto-door-opener-and-special-bed-surface-for-frictionless-part-ejection> |
| S23 | PrintFlow3D; A1 mini changer | <https://printflow3d.com/products/printflow3d-plate-changer>, <https://3druck.com/en/diy/maker-develops-system-to-automatically-change-3d-printing-build-plates-for-bambu-a1-mini-08140368/> |
| S24 | Vention 7th axis | <https://www.universal-robots.com/marketplace/products/01tP40000071NjeIAE/>, <https://vention.io/designs/machine-tending-ur10e-7th-axis-of-2m-range-with-ur3e-workstation-36630> |
| S25 | Cobotracks LMK | <https://www.cobotracks.com/linear-motion-kit/lmk10-alu-b/>, <https://www.cobotracks.com/linear-motion-kit/lmk10-alu-bs/> |
| S26 | Thomson CTU + Fanuc CRX | <https://crx.fanucamerica.com/cobot-devices/thomson-movotrak-cobot-transfer-unit-ctu>, <https://control.com/news/fanuc-and-regal-rexnord-add-a-7th-axis-to-robot-automation-systems> |
| S27 | Fanuc CRX-10iA/L; modular RTU | <https://crx.fanucamerica.com/crx-10ia-l>, <https://www.fanucamerica.com/products/accessories/rtu-modules> |
| S28 | AR4 7th axis | <https://anninrobotics.com/forum/robot-builds/ar4-with-7th-axis-and-easy-transportation/>, <https://anninrobotics.com/forum/questions/7th-axis/> |
| S29 | Cartesian gantry data | <https://rbtx.com/en-US/components/robots/room-linear-robot-stepper-motors-with-encoder-working-space-2000-x-2000-x-1000-mm>, <https://www.machinedesign.com/mechanical-motion-systems/article/21831692/the-difference-between-cartesian-six-axis-and-scara-robots>, <https://www.motiontech.co.uk/cartesian-robots-advantages> |
| S30 | Overhead gantry tending | <https://strategiautomation.com/gantry-machine-tending-robot-smart-automation-for-modern-cnc-manufacturing/> |
| S31 | Class cost/reach guides; rail economics | <https://millbrief.com/cost/industrial-robot-cost/>, <https://amdmachines.com/blog/6-axis-vs-scara-robots-which-is-right-for-your-application/>, <https://amdmachines.com/solutions/machine-tending/> |
| S32 | Printed SCARAs | <https://hackaday.io/project/175419-pybot-scara-robotic-arm-3d-printed-python>, <https://www.sciencedirect.com/science/article/pii/S2468067226000210>, <https://hackaday.io/project/204557-pr3-scara>, <https://howtomechatronics.com/projects/scara-robot-how-to-build-your-own-arduino-based-robot/> |
| S33 | Jubilee CHI paper | <https://www.researchgate.net/publication/341697828_Jubilee_An_Extensible_Machine_for_Multi-tool_Fabrication> |

## What to take
- Size the mechanism on the plate pull/slide (at least 320 mm level, straight, through an aperture), not the door or screen; the one documented SCARA-on-Bambu attempt stalled exactly there [S18].
- Base location beats family: a base on the door axis (rail, front pedestal, gantry) removes the entry-geometry problem; a base between printers needs a long plate fork, standoff, or 520-680 mm reach (section 1, reasoning).
- No printed 6-axis in my sources documents 1.5 kg at reach (PAROL6 0.5 kg, Thor 0.75 kg incl. EE) [S4,S5]; SCARA and gantry keep gravity off the revolute motors (reasoning).
- Print-farm robots on rails are in production today (DHR: 40+ printers, H2D added in under 24 h, spool carousel) [S19]; a 7th axis is a taught-position axis, not a planned joint [S28].
- Cheap rails and gantry axes already meet +-1 mm by 10-20x (0.05-0.1 mm) [S25,S29]; stiffness and cantilever, not repeatability, set the limit.
- Collaborative safety is a design property you buy or build in: PF3400 under 100 N free / 150 N rigid [S13]; Thomson adds collision detection to the rail [S26]. ISO/TS 15066 limit tables were NOT retrieved.
- Option E parts exist for door + eject (129 USD) [S22] but no H2S plate swapper or S1 Pro swapper was found.

## Documented failures -> rule
| Failure | Source | Rule for our robot |
|---|---|---|
| Dobot M1 opened the X1C door but could not remove the plate; switched to vacuum part pick-up | [S18] | Prototype the 340x320 plate extraction on the real H2S before fixing the arm class |
| Hobby-servo SCARA: +-3.5 mm at speed, 100 g | [S32] | No hobby servos; closed-loop steppers/encoders on every axis (R5 +-1 mm) |
| Printed SCARA 0.4 mm measured (0.2 mm tuned) | [S32] | Budget 0.2-0.4 mm for printed joints; test at full extension |
| PAROL6 derates 1 kg to 0.5 kg; Thor 750 g includes EE | [S4,S5] | State payload at the farthest pose including tool mass |
| AR4 7th axis not in kinematics | [S28] | Treat rail as indexed stations with hard stops |
| Jubilee is "non-loadbearing" | [S3] | Compute deflection for 1.5 kg + 340 mm cantilever; do not reuse printer frames blind |
| PF400 collision trips envelope error, drops power | [S2] | Implement fault recovery; absolute encoders so no re-home sweep inside a printer |
| DHR needed per-size gripper jaws and calibrated rack positions (H2D larger tray) | [S19] | Swappable plate tool per printer; per-printer taught points + fiducials |
| PF400 payload quoted 0.5 kg / 1 kg / 1.2 kg across sheets | [S10,S11] | Read payload footnotes; always include gripper mass |
| Faze4 has about 1000 parts | [S6] | Count parts per option as build/service cost |

## Open questions
- Table width/depth, printer gap, front offset, free floor in front (rail/pedestal feasibility); H2S aperture width/height and door hinge side (assumptions in section 1 need measuring).
- Plate mass and removal path (lift vs slide), bed park height, and the Ender S1 Pro screen type (touch or knob-only; unverified here).
- AMS 2 Pro position relative to the H2S (sets spool lift height and reach).
- Re-verify C\* numbers on vendor pages (WebFetch was blocked); get Vention/Thomson rail prices and carriage ratings, ISO/TS 15066 force tables, and any quantified reach-into-door rules.
- Find any H2S plate-swap mechanism; ask DHR for payload/precision of their rail robot.
