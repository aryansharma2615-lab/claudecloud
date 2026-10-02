# FarmHand: physical and software interfaces of the two printers

Shawarma Prints (SP) | research note dated 2026-10-02 (H2S arrives 2026-10-03) | scope: what a robot must touch, read, or command.

**Evidence grades.** A = measured, teardown, or live capture. B = photo, video, or hands-on review. C = vendor spec or vendor-authored file (including Bambu Studio profiles and Marlin example configs). D = hearsay, forum summary, or unverified. "(code)" = read by me from open-source files I downloaded and parsed.

## 0. Read this first: limits of this research

- The sandbox egress proxy blocked bambulab.com, wiki.bambulab.com, forum.bambulab.com, Reddit, Wikipedia, archive.org and every review site I tried (Tom's Hardware, Fabbaloo, TechRadar, etc.) for page fetches. The 200-call WebSearch budget for the session ran out part-way through.
- So prose facts about the H2S (door, plate, AMS, screen) come from **search-result snippets** (a summary, not the page). I grade those D unless two sources agree or a vendor store page is the source (C).
- Hard facts come from raw GitHub files I downloaded and parsed: Bambu Studio's H2S profile, start/end G-code and bed model; the Home Assistant Bambu integration (ha-bambulab); OpenBambuAPI; Marlin, Orca, Cura and Klipper configs for the Ender.
- **Not found anywhere I could read:** H2S door hinge side, handle shape/size, latch force, plate removal motion and alignment pins, touchscreen button layout, AMS 2 Pro lid direction, camera positions, bed cool-down time. Ender plate size, magnet strength and spool path are also missing. Section "Measure on arrival day" covers each.
- Terms: MQTT = Message Queuing Telemetry Transport (the printer's pub/sub messaging). LAN = local network. AMS = Automatic Material System (Bambu's spool feeder). PEI = polyetherimide (the print-surface coating). HMS = Health Management System (Bambu error codes). G-code = machine command text (G1 = linear move, M-codes = machine functions). STL = triangle-mesh 3D model file. RFID = radio tag on a spool. RTSPS = encrypted video-stream protocol. CR Touch = Creality's bed-height probe. DWIN/DGUS = display-module maker and its touch-UI system.

## 1. Bambu Lab H2S

### 1.1 Body, door, lid, sensors

| Item | Value | Grade | Source |
|---|---|---|---|
| Exterior | 492 x 514 x 626 mm (vendor does not state which is W/D/H); 30 kg (Laser Edition 30.5 kg) | C | [S1] [S2] |
| Build volume / limits | 340 x 320 x 340 mm; nozzle 350 C; bed 120 C; actively heated chamber to 65 C | C | [S1] [S3] |
| AMS 2 Pro position | On top of the printer, set on with the top glass cover (quick-start guide). Stacked height is about 626 + 226 = 852 mm if it sits fully on top (my arithmetic, unverified) | D | [S7] [S4] |
| Top lid | Glass top with a motorised vent flap at the front (review snippets; which review is uncertain). The printer also monitors the top glass; a sensor field is requested but not exposed in Home Assistant | D | [S51] [S52] [S37] |
| Door | Glass front door, fully hinged, with upper and lower hinges, door magnets and silicone pads (spare-part kit contents). Review says it opens 180 degrees (unlike the X1C) | C/D | [S8] [S9] [S10] |
| Hinge side, handle shape/size, magnet pull force, swing clearance | **Not documented.** Nobody I could read measured it | n/a | see "Measure on arrival day" |
| Door sensor | Hall-effect magnet sensor. Forum: two magnetic switches (top and bottom) but one magnet on the door. A false "door open" cleared when the door was pushed at the magnet; also check the small rubber square is fully seated | D | [S11] [S13] |
| Door sensor in software | Printer-side 3-state option: 0 off, 1 warn, 2 pause print. Users say it acts only while printing | C(code) / D | [S24] [S12] |
| Refuses to start with door open? | **Not documented.** A stage "check_door_and_cover" (id 42) exists in the stage list. An X1-era request asks to "refuse to start a new print if the door has not been opened since the last print", i.e. not implemented there | C(code) / D | [S15] [S25] |
| Door state over MQTT | H2-series: field `print.stat`, a hex string; bit 0x00800000 = door open. Capture on an H2D: `46258000` closed, `46A58000` open. `home_flag` does NOT carry it on H2 | A (capture) | [S14] [S16] |

### 1.2 Build plate

| Item | Value | Grade | Source |
|---|---|---|---|
| Printable area | 340 x 320 mm, origin (0,0) front-left | C(code) | [S19] |
| Plate outline | 355.0 x 346.5 mm: X -7.5..347.5, Y -18.5..328.0 relative to the printable origin (margins L/R 7.5, front 18.5, rear 8). Third-party listing says 346 x 355 mm, matching | C(code) + D | [S23] [S42] |
| Outline features | From the Bambu Studio bed STL (0.7 mm thick model): rear edge steps in 5 mm for X 40..300; front-centre notch about 136 mm wide x 15.5 mm deep (X 102..238, Y -18.5..-3). Purpose unknown. This is a render model, so hidden pins or magnets are not shown | C(code) | [S23] |
| Material | Textured PEI = 0.075 mm PEI powder coat on 0.5 mm stainless steel. Plate weight: not documented | C/D | [S41] |
| Plate types | Profile default "Textured PEI Plate"; profile lists "Cool Plate" as NOT supported; "High Temp" and Engineering plates are referenced; third-party smooth PEI exists. "Cool Plate SuperTack" status unknown | C(code) | [S22] [S40] |
| Replacing the sheet | Bambu wiki: only High Temp and Cool plates take replacement sheets; Textured PEI is one piece | D | [S46] |
| Price | USD 59.99 for the Bambu Textured PEI Plate. **CAD price not found**; check ca.store.bambulab.com | D | [S41] |
| Magnetic base, rear pins/tabs, how to lift/seat | **Not documented** in readable sources | n/a | measure |
| Printer verifies the plate itself | Start G-code runs heatbed detection, toolhead-camera detection (`M972 S31`), plate-offset detection (`M972 S34`), and a heatbed foreign-object check. Stage ids 11, 73, 74, 75 report these. Errors seen in the wild: "marker not detected", "Buildplate offset 0500-808C" | C(code) / D | [S21] [S15] [S27] [S28] [S40] |
| Marker detector switch | MQTT `xcam_control_set` module `buildplate_marker_detector` has a `print_halt` flag (halt print on error) | C(code) | [S18] |

### 1.3 Bed motion, toolhead park, temperatures

| Item | Value | Grade | Source |
|---|---|---|---|
| Bed axis | Bed moves in Z. G-code Z = nozzle-to-bed gap, so larger Z = bed lower. Vendor G-code clamps at Z 340 (= printable height) | C(code) | [S19] [S20] |
| Bed at end of print | Bambu Studio end G-code: `G1 Z{max_layer_z+0.4}`, toolhead to macro `G150.3`, then Z-motor current cut (`M17 Z0.4`) and `G1 Z{max_layer_z + 100 - max_layer_z/2}` (cap 340). Result: about 100 mm between nozzle and part top for short parts, shrinking to about 0 for parts 200 mm tall. **The bed does not go to the bottom by default** | C(code) | [S20] |
| Toolhead park | `G150.3` is commented "move to garbage can" (waste chute) in the start G-code. X/Y coordinates not documented | C(code) | [S21] |
| Post-print wait | The bed heater is switched off (`M140 S0`) early in the end G-code, then, when the post-print air-filter option is on, a 180 s fan cycle (`M400 S180`) runs before the job ends. So `gcode_state` can stay RUNNING about 3 min after the last move | C(code) | [S20] |
| Commanding bed height | MQTT `print.gcode_line` takes raw G-code in `param` (`\n` between lines). Home Assistant's jog sends `M211 S / M211 X1 Y1 Z1 / M1002 push_ref_mode / G91 / G1 Z{d} F{speed} / M1002 pop_ref_mode / M211 R`; home = `G28`. Bambu wraps low moves in `M17 Z0.4 ... M17 R` "to reduce impact if there is something in the bottom" | C(code) | [S18] [S17] [S20] |
| Built-in "lower bed" button | Touchscreen jog exists on older Bambu models (a user lowered the bed and moved the head by touchscreen). H2S-specific: not confirmed | D | [S50] |
| Cool-down to < 35 C | **Not documented.** Bed heater is off from print end; cooling is passive | n/a | measure: log `bed_temper` |
| Known tilt issue | A new H2S arrived with a tilted bed; fixed by half a turn on the rear-left tramming screw | D | [S39] |

### 1.4 Touchscreen

| Item | Value | Grade | Source |
|---|---|---|---|
| Size/resolution | 5-inch, 720 x 1280 | C | [S1] |
| Position | Front top-left corner, tiltable (reviews). Spare-part page quotes a 5-55 degree rotation range | D | [S44] [S51] [S43] |
| Touch type | Capacitive per a snippet; **no primary source**. Test with a plastic tip vs a conductive tip | D | [S43] |
| Active area (derived) | If 5.0 inch diagonal and 9:16: about 62 x 111 mm, 0.086 mm per pixel. Real area may be smaller | derived | my arithmetic |
| Layout, button size | **Not documented**; photograph with a ruler on day 1 | n/a | measure |
| What needs a tap | LAN live-view (RTSPS camera) is off by default on observed H2S firmware 01.02.00.00 and is enabled only by a touchscreen toggle (Settings, General, LAN live-view; label varies). A human does this once | C(code) | [S45] |

### 1.5 AMS 2 Pro

| Item | Value | Grade | Source |
|---|---|---|---|
| Size/weight | 372 x 280 x 226 mm; 2.5 kg | C | [S4] |
| **Spool limits** | Diameter **197-202 mm**, width **50-68 mm**. Check the planned 1.2 kg spools against this now | C | [S4] |
| Seating | Spool rests on active support-shaft rollers that also rotate it (rotation during drying and feeding) | C | [S5] |
| Lid | Transparent top lid; spare parts are base, shaft and damping pad, so likely hinged with a damper. Opening direction not documented | D | [S6] |
| Drying | Two drying modules (heater, fan, sensors), up to 65 C, spools auto-rotate | C | [S4] |
| Feed | Brushless servo feeding motor + RFID. Four run-out sensors on an H2D path: motor, internal, buffer, extruder. Whether it self-pulls when you push the tip in: not documented | C / D | [S4] [S33] |
| Control | No panel of its own; run from the printer. MQTT: `ams_filament_setting` (type, colour, temp range; needed for non-RFID spools), `ams_change_filament`, `ams_control` (resume/reset/pause), `ams_filament_drying` (temp >= 45, duration, mode 0/1, `rotate_tray`; print-class command) | C(code) / D | [S10] [S18] [S17] [S38] |
| Restock needs | Idle printer only: slot info is locked while printing. Lift the empty spool off the rollers, place the new one with correct unwind direction, push the tip into the slot, then set the tray by MQTT | D | [S35] [S36] |

### 1.6 Cameras

| Camera | Spec | Grade | Source |
|---|---|---|---|
| Live view (chamber) | 1920 x 1080, built in; position not documented | C | [S1] |
| Toolhead | 1600 x 1200, built in; used for plate detection in start G-code (`M972 S31`) | C / C(code) | [S1] [S21] [S48] |
| BirdsEye | 3264 x 2448, Laser Edition only (not ours) | C | [S1] |
| Access | `rtsps://IP:322/streaming/live/1`, user `bblp`, LAN access code; off by default on H2 (see 1.4) | C(code) | [S45] |

### 1.7 Power and robot interlock fields

- **Power.** Snippets say max about 1170 W and about 1250 W at 110 V (they disagree). Read the nameplate. A 15 A, 120 V branch is 1800 W nominal (my arithmetic). Grade D. [S1] [S49]
- **Interlock fields** (MQTT `print` object; all C(code) unless noted; [S16] [S15] [S18]):

| Need | Field | Rule of thumb |
|---|---|---|
| Printer idle | `gcode_state` in {IDLE, FINISH, FAILED}; PREPARE/RUNNING/PAUSE are busy | Enter only when idle AND `stg_cur` is -1 or 255 |
| Stage | `stg_cur` ids: 0 printing, 1 bed levelling, 2 bed preheat, 11 plate type, 13 homing, 42 door/cover check, 50 bed cooling, 54 wait bed temp, 73 plate alignment, 74/75 foreign-object checks | Log the id with every error |
| Door | `stat` bit 0x00800000 (see 1.1) | Treat missing/unknown as open |
| Bed temp | `bed_temper`, `bed_target_temper`; newer firmware packs `device.bed.info.temp` (low 16 bits current, high 16 bits target) | Read both forms |
| Chamber temp | `chamber_temper` or `device.ctc.info.temp` | Needed for the hot-day pause (see "Documented failures") |
| Axes homed | `home_flag` bits X=1, Y=2, Z=4 | Home before any `G1 Z` |
| Filament at extruder | `hw_switch_state` (NOT a door switch) | Do not confuse |
| Errors | `hms`, `print_error`, `mc_print_error_code` | Stop robot motion on any non-empty HMS |

## 2. Creality Ender 3 S1 Pro

### 2.1 Body, bed, plate

| Item | Value | Grade | Source |
|---|---|---|---|
| Exterior | 455 x 490 x 625 mm (listing gives 17.91 x 19.29 x 24.61 in; order not stated); weight not retrieved | C | [E2] |
| Build/limits | 220 x 220 x 270 mm; hotend 300 C; bed 110 C; Sprite full-metal direct-drive extruder; filament sensor; CR Touch levelling | C | [E1] [E2] |
| Axis travel, Marlin example | X -9..220, Y -6..220, Z 0..270. Y homes at its minimum (bed pulled to the rear, inferred) | C(code) | [E3] |
| Axis travel, other firmware | Community Klipper: X -5..235, Y -2..235, Z -10..275. One Marlin fork sets bed 235 x 225. A fork user reports the nozzle at X110/Y110 sat 20 mm left and 5 mm back of centre | D | [E9] [E7] [E15] |
| "Bed forward" | Y increases = bed comes toward the front (bed-slinger, inferred). Orca's end G-code "presents the print" at `G1 X5 Y{0.8 x 220}` = Y 176. Max Y reach differs by firmware, so measure the real stop | C(code) | [E5] [E6] |
| Sheet | "Flexible magnetic PEI bed" (magnetic base + flexible spring-steel sheet). Your 235 x 235 mm guess: no source found. Alignment stops, magnet strength: **not documented** | D | [E1] |
| Probe offset | CR Touch sits at about (-31.8, -40.5) mm from the nozzle | C(code) | [E3] |

### 2.2 Screen

| Item | Value | Grade | Source |
|---|---|---|---|
| Size | 4.3-inch colour (listing title says "LCD Screen") | C | [E1] |
| Touch? | Yes: Marlin's S1 Pro config uses `DGUS_LCD_UI E3S1PRO` under the header "DGUS Touch Display with DWIN OS"; community firmware calls it "TouchPanel Display" and supports DWIN and Dacai variants. The base S1 uses a knob UI | C(code) / D | [E3] [E7] [E8] [E11] [E14] |
| Capacitive vs resistive | **No definitive source found.** Marlin, Klipper and the screen-firmware repos do not say. Test on arrival (plastic tip, gloved finger, conductive tip) | D | n/a |
| Interface | 6-pin JST XH serial link to the mainboard | D | [E12] |
| Button layout/size | Not documented | n/a | measure |
| Does the robot need it? | **No**, if OctoPrint drives everything over USB. One catch: a screen prompt can stall host prints ("busy: paused for user" until `M108` is sent). Use `M108` from the host, never a screen tap | D | [E10] |

### 2.3 Filament path, threading, alternatives

| Item | Value | Grade | Source |
|---|---|---|---|
| Spool holder | Top of frame (from your brief; not independently sourced) | D | n/a |
| Runout sensor | One switch sensor; state HIGH = no filament; trigger distance 25 mm; pin PC15 in Klipper. Position along the path not retrieved | C(code) | [E3] [E9] |
| M600 flow (Marlin example, shipped firmware may differ) | Unload 100 mm at 20 mm/s; load lengths 0 (you insert, then it purges 50 mm); nozzle heater times out after **45 s** of waiting; `M701`/`M702` load/unload and host action commands enabled | C(code) | [E4] |
| Robot threading difficulty | Direct drive, so no long Bowden tube. The robot must feed a clean-cut 1.75 mm tip into the sensor and gear pinch inside a 45 s window, or run `M701` so the gears pull it. No measurement of the entry hole exists in sources | D | measure |

| Option | Needs | Evidence | Verdict |
|---|---|---|---|
| Bigger spools (3-5 kg) on an external stand | Stand + guide tube; reduces swaps 2.5x (3 kg) or 4x (5 kg) vs 1.2 kg (arithmetic) | Frame-top holder capacity not documented | Best first step: no firmware change |
| Klipper + Happy Hare (+ Box Turtle) | Klipper host, new firmware, drop OctoPrint-Marlin design | Happy Hare README: "MMU driver for Klipper", v4 installer offers Box Turtle, EndlessSpool hand-off [E13]. Klipper on S1 Pro is proven by community configs [E9] [E16] | Possible but a platform change |
| Marlin built-in MMU options | Spare UART, config rebuild | Marlin lists PRUSA_MMU2/2S/3 and EXTENDABLE_EMU_MMU2 (ERCF/SMuFF) options, commented out for S1 Pro [E3] | Unverified on this board |
| Creality CFS | Compatibility unverified; no search budget left | none | Assume NOT compatible until Creality says so (D) |
| 3MS, spool joiner/splicer | n/a | not researched | Manual idea only |
| Robot swaps spool using M600 | Gripper that can hold a spool + thread in 45 s | Marlin flow above | Hardest; defer |

## What to take

1. **MQTT is the main sensor.** Read the door from `stat` bit 0x00800000, idle from `gcode_state` + `stg_cur`, bed from `bed_temper`. Capture the raw `stat` on arrival to confirm the bit on the H2S.
2. **The bed is the plate elevator.** Command `G1 Z` over `gcode_line` (with `M17 Z0.4` first) to a hand-off height; the default end position is about 100 mm down, not the bottom.
3. **The printer checks plate seating itself** (camera, offset, foreign object). Use that as the robot's pass/fail test, set the marker detector to halt, and find the real placement tolerance by deliberately offsetting a plate.
4. **Check the spool fit now:** AMS 2 Pro takes diameter 197-202 mm and width 50-68 mm.
5. **Do not plan on touchscreen taps.** H2S: only the one-time RTSPS toggle. Ender: use OctoPrint and `M108`.
6. **Ender filament: start with bigger spools,** not a threading robot. Revisit Klipper + Happy Hare only if the platform change is acceptable.
7. **Unknowns that drive door and plate design** (hinge side, handle, force, plate lift/seat, alignment) are measured on day 1, so keep the door actuator and gripper adjustable.

## Documented failures → rule

| Failure | Source | Rule for our robot |
|---|---|---|
| False "front door open" until the door is pushed at the magnet | [S11] | After closing, give a final push at the magnet position; require the `stat` door bit clear for 2 s before starting |
| Door state read from the wrong field (`home_flag`) never changes on H2 | [S14] | Read `stat`; treat unknown door state as open |
| Door sensor not pausing or notifying on some units | [S12] | Never rely on the printer to stop the robot; the cell needs its own interlock |
| Plate "marker not detected" / "Buildplate offset" even when seated | [S27] [S28] [S40] | Allow 2 reseat retries (lower bed, reseat, retry), then stop and alert; keep plate underside clean |
| Foreign-object stop on a clean plate (X2D report; same check exists in H2S start G-code) | [S32] | Camera check plate empty before start; one sweep retry, then alert |
| Bed left at the bottom, next print grinds at start | [S26] [S47] | Park bed at a mid height (not Z 340) after every robot move; use reduced Z current for low moves |
| Hot-day chamber-too-hot pause (idle chamber read 43 C) with third-party filament | [S29] | Log `chamber_temper`; set `chamber_temperature` in the filament profile; ventilate; hold the queue above a threshold |
| Custom filament profile triggers a chamber pre-heat loop | [S31] | Use stock profiles; freeze slicer settings |
| AI nozzle-clumping false positive pauses a good print | [S30] | Handle PAUSE with `resume` and a retry count; escalate after 2 |
| AMS spool runs out, tape lets go, spool free-spins, retract error | [S33] [S34] | Swap spools before the end (track grams per spool); do not run to empty |
| AMS slot info locked during a print; unknown spool has no data | [S35] [S36] | Restock only when idle; push type/colour with `ams_filament_setting` |
| New H2S bed tilted from the factory | [S39] | Check first-layer and tram before calibrating robot offsets |
| Ender: screen prompt stalls a host print | [E10] | Use `M108`, not a screen tap |
| Ender: nozzle gouged the textured sheet with a wrong Z offset | [E8] | Probe a fresh mesh on every print; reject unknown sheets |
| Ender: real travel differs from stated bed size | [E15] [E7] | Measure the real Y stop, set soft limits, do not trust `G1 Y max` |

## Measure on arrival day

| Check | Tool |
|---|---|
| H2S outer W/D/H, AMS stacked height, door aperture W/H, gap from bed to door sill at Z 0 and 100 | Tape measure |
| Door: hinge side, swing angle, handle position/size, clearance when open 90 and 180 degrees | Tape + phone video |
| Door opening force, and pull to unlatch (grams at the handle) | Luggage scale on a string |
| Door sensor: capture `stat` (door open/closed, top lid open/closed) and confirm bit 0x00800000; try a print start with door open (supervised) | `mosquitto_sub` on the printer's MQTT topic |
| Plate: weight, thickness, rear/side features, lift and seat motion (video), pull force to remove | Kitchen scale, calipers, luggage scale, phone |
| Plate placement tolerance: offset by 1, 2, 3, 5 mm and rotate 1, 2 degrees; note which pass detection (stage 73) | Ruler, MQTT log |
| Bed height vs `G1 Z` (surface height at Z 0, 100, 200, 340); toolhead park X/Y after a print | Ruler, phone |
| Bed cool-down from 60 C to < 35 C, with and without door open | MQTT log of `bed_temper` |
| Screen: photo with ruler, button sizes and positions; capacitive vs plastic tip | Phone + ruler |
| AMS: lid direction and angle; spool seat height above table; test the 1.2 kg spool fit; does the tip self-feed | Tape, spool in hand |
| Power: nameplate watts; measured draw during preheat | Plug-in power meter |
| Ender: real Y stop (`G1 Y220`, then `Y235` carefully), plate size/thickness/weight, magnet pull, sheet alignment play | Ruler, calipers, luggage scale |
| Ender: screen type test; spool holder height; filament entry hole width and the sensor position | Phone + ruler |

## Open questions

1. H2S: hinge side, handle geometry, latch force. (Arrival day.)
2. Does H2S firmware refuse to start with the door open, and does it check the top glass?
3. How does a plate come off and seat (lift front? slide?), and what placement error does the toolhead camera tolerate?
4. Is "Cool Plate SuperTack" supported on H2S? The profile excludes "Cool Plate".
5. AMS 2 Pro: does it auto-pull on tip insertion; which way does the lid open?
6. Is H2S bed cool-down fast enough to avoid waiting (< 35 C)?
7. Ender: capacitive or resistive; plate size and alignment; how much further forward than Y 220 the bed can reach safely.
8. Is Creality CFS compatible with the S1 Pro? (Unverified: check Creality's page.)
9. CAD price of a spare H2S plate.
10. Bambu Studio's start/end G-code is firmware-coupled (end G-code dated 2026-03-13, start 2026-04-21): re-read it from the version installed on arrival day.

## Sources

IDs used in the tables above. Snippet-only sources (page not fetchable) are S1-S13, S39-S44, S46-S49, S51-S52, E1-E2; the rest were read as files or issue text.

S1 https://bambulab.com/en-us/h2s/tech-specs | S2 https://simplyprint.io/compatibility/bambu-lab-h2s  
S3 https://3dprintingindustry.com/news/bambu-lab-launches-the-new-h2s-technical-specifications-and-pricing-243603/ | S4 https://us.store.bambulab.com/products/ams-2-pro  
S5 https://us.store.bambulab.com/products/ams-2-pro-active-support-shaft-assembly | S6 https://us.store.bambulab.com/products/ams-2-pro-top-lid  
S7 https://manuals.plus/m/c958e0dcd05a772c20b7b541dfe87df8ba4c045e1d24807f9c1f36a87d8ea8a7 | S8 https://us.store.bambulab.com/products/front-door-mounting-kit-h2-series  
S9 https://www.digitmakers.ca/products/bambu-lab-front-glass-door-h2d-and-h2s | S10 https://www.fabbaloo.com/news/hands-on-with-the-bambu-lab-h2s-3d-printer-part-2  
S11 https://forum.bambulab.com/t/bogus-front-door-is-open-error-message/166361 | S12 https://forum.bambulab.com/t/the-front-door-sensor-is-not-working-for-me/161966  
S13 https://wiki.bambulab.com/en/h2/maintenance/replace-hall-effect-sensor | S14 https://github.com/greghesp/ha-bambulab/issues/1421  
S15 https://raw.githubusercontent.com/greghesp/ha-bambulab/main/custom_components/bambu_lab/pybambu/const.py | S16 https://raw.githubusercontent.com/greghesp/ha-bambulab/main/custom_components/bambu_lab/pybambu/models.py  
S17 https://raw.githubusercontent.com/greghesp/ha-bambulab/main/custom_components/bambu_lab/pybambu/commands.py | S18 https://raw.githubusercontent.com/Doridian/OpenBambuAPI/main/mqtt.md  
S19 https://raw.githubusercontent.com/bambulab/BambuStudio/master/resources/profiles/BBL/machine/Bambu%20Lab%20H2S%200.4%20nozzle.json | S20 https://raw.githubusercontent.com/bambulab/BambuStudio/master/resources/profiles/BBL/machine/Bambu%20Lab%20H2S%200.4%20nozzle%20template%20machine_end_gcode.json  
S21 https://raw.githubusercontent.com/bambulab/BambuStudio/master/resources/profiles/BBL/machine/Bambu%20Lab%20H2S%200.4%20nozzle%20template%20machine_start_gcode.json | S22 https://raw.githubusercontent.com/bambulab/BambuStudio/master/resources/profiles/BBL/machine/Bambu%20Lab%20H2S.json  
S23 https://raw.githubusercontent.com/bambulab/BambuStudio/master/resources/profiles/BBL/bbl-3dp-O1S.stl | S24 https://github.com/bambulab/BambuStudio/blob/master/src/slic3r/GUI/DeviceManager.hpp  
S25 https://github.com/bambulab/BambuStudio/issues/2751 | S26 https://github.com/bambulab/BambuStudio/issues/647  
S27 https://github.com/bambulab/BambuStudio/issues/2705 | S28 https://github.com/bambulab/BambuStudio/issues/9945  
S29 https://github.com/bambulab/BambuStudio/issues/11133 | S30 https://github.com/bambulab/BambuStudio/issues/10137  
S31 https://github.com/bambulab/BambuStudio/issues/11167 | S32 https://github.com/bambulab/BambuStudio/issues/11823  
S33 https://github.com/bambulab/BambuStudio/issues/7612 | S34 https://github.com/bambulab/BambuStudio/issues/11818  
S35 https://github.com/bambulab/BambuStudio/issues/11887 | S36 https://github.com/bambulab/BambuStudio/issues/10099  
S37 https://github.com/greghesp/ha-bambulab/issues/1805 | S38 https://github.com/greghesp/ha-bambulab/issues/1448  
S39 https://forum.bambulab.com/t/issue-with-build-plate-on-new-bambulab-h2s/201223 | S40 https://forum.bambulab.com/t/engineering-print-plate-not-recognized-marker-was-not-detected/232948  
S41 https://us.store.bambulab.com/products/bambu-textured-pei-plate | S42 https://www.amazon.com/Bamboo-Printer-346x355mm-Platform-350mmx320mm/dp/B0GH6PCMZ9  
S43 https://us.store.bambulab.com/products/touchscreen-h2-series | S44 https://www.grayscalpminiatures.com/blog-3/bambu-lab-h2s-review  
S45 https://raw.githubusercontent.com/Doridian/OpenBambuAPI/main/video.md | S46 https://wiki.bambulab.com/en/general/build-plate  
S47 https://forum.bambulab.com/t/print-bed-hits-bottom-of-z-axis-when-starting-new-print/32174 | S48 https://us.store.bambulab.com/products/toolhead-camera-h2-series  
S49 https://forum.bambulab.com/t/h2d-max-power-overated-for-the-power-plug/163074 | S50 https://github.com/bambulab/BambuStudio/issues/1359  
S51 https://the-gadgeteer.com/2025/10/20/bambu-lab-h2s-3d-printer-review-bigger-and-better/ | S52 https://www.cgmagonline.com/review/hardware/bambu-lab-h2s-3d-printer/  
E1 https://www.microcenter.com/product/649022/creality-ender-3-s1-pro-3d-printer | E2 https://www.bhphotovideo.com/c/product/1707834-REG/creality_ender_3_s1_pro_3d.html  
E3 https://raw.githubusercontent.com/MarlinFirmware/Configurations/bugfix-2.1.x/config/examples/Creality/Ender-3%20S1%20Pro/Configuration.h | E4 https://raw.githubusercontent.com/MarlinFirmware/Configurations/bugfix-2.1.x/config/examples/Creality/Ender-3%20S1%20Pro/Configuration_adv.h  
E5 https://raw.githubusercontent.com/SoftFever/OrcaSlicer/main/resources/profiles/Creality/machine/Creality%20Ender-3%20S1%20Pro%200.4%20nozzle.json | E6 https://raw.githubusercontent.com/Ultimaker/Cura/main/resources/definitions/creality_ender3s1pro.def.json  
E7 https://github.com/synman/Ender-3-S1-Pro-Firmware | E8 https://github.com/ThomasToka/MarlinFirmware/issues/98  
E9 https://github.com/mpohoda/Klipper_E3S1Pro | E10 https://github.com/synman/Ender-3-S1-Pro-Firmware/issues/46  
E11 https://github.com/Pethical/Ender-3-S1-Pro-Screen | E12 https://github.com/gpatsiaouras/ender3-s1-pro-screen-sw  
E13 https://github.com/moggieuk/Happy-Hare | E14 https://raw.githubusercontent.com/CrealityOfficial/Ender-3S1/main/README.md  
E15 https://github.com/ThomasToka/MarlinFirmware/issues/104 | E16 https://github.com/fire1ce/klipper-ender3-s1  
