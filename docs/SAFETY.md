# FarmHand — Safety (Phase 1, 2026-10-02)

Rule: **hardware cuts power on its own; software only adds a second layer and alerts.** Nothing unattended runs before Gate 3 passes.

Layers:
1. **Printer firmware** — thermal-runaway protection (both printers), H2S flame/temperature detection (per [spec page](https://bambulab.com/en/h2s/tech-specs)).
2. **Hardware cutoff** — smoke + heat detector dry contacts → latching relay → IoT Relay outlets that drop printer mains. No PC, no Wi-Fi involved.
3. **Supervisor** — separate Windows service, reads printer telemetry, smart-plug power, robot status, and the latch's aux contact; pauses jobs, halts the robot, alerts.
4. **Human** — Pushover emergency alert (repeats until acknowledged), E-stop at the station, ABC extinguisher by the door.

| # | Hazard | Detection | Automatic action | Test (monthly unless noted) |
|---|---|---|---|---|
| H1 | Fire / smoke at a printer | 4-wire photoelectric smoke detector (relay contact), ceiling above the station, ≤ 1 m horizontally | Detector contact → latch relay trips → both IoT Relays cut printer mains; latch stays tripped until manual reset; supervisor sees aux contact → robot halt + Pushover P2 | Detector test button (and canned smoke spray quarterly) → outlets dead, phone alert < 30 s, power stays off after smoke clears |
| H2 | Overheat without smoke (smouldering, heater stuck on) | Fixed 57 °C + rate-of-rise heat detector (passive NO contact), **above** the H2S top (not inside — chamber runs to 65 °C) | Same latch → mains cut | Hair dryer on detector → trip (quarterly); confirm no false trip during a 65 °C chamber print |
| H3 | Thermal runaway (thermistor falls out, heater fails) | Printer firmware: Ender Marlin `THERMAL_PROTECTION`, H2S firmware | Printer firmware kills heater + shows error; supervisor sees error via MQTT/OctoPrint → pause farm, alert | Once at setup + after any firmware change: **printer cold and unplugged**, unplug the hotend heater connector, power on, set 200 °C → expect "Heating failed" within ~40 s. Never test by detaching a thermistor while hot |
| H4 | Electrical overcurrent / plug fault | Smart plug (Shelly Plug, local API) power reading + its built-in overcurrent cutoff; breaker | Plug switches off over limit; supervisor alerts if power is out of band (e.g. > 1300 W H2S, > 450 W Ender) | Read power during a heat-up; check alert threshold fires on a simulated value |
| H5 | Power cut / brownout | UPS on PC + router only (printers **not** on UPS) | PC rides through; on return H2S power-loss recovery is **disabled** for unattended runs → supervisor marks job failed, alerts | Pull the wall plug on the UPS: PC stays up, alert arrives |
| H6 | Farm server crash / hang | Supervisor watchdog: farm heartbeat every 2 s, timeout 10 s | Supervisor pauses printers (MQTT/OctoPrint direct), halts robot, alerts; does **not** cut mains (a hot nozzle needs its fan) | Kill the farm process → pause + alert < 15 s |
| H7 | Supervisor itself dies | Windows service auto-restart; farm server checks supervisor heartbeat; ESP32 latch board optional dead-man | Restart; if down > 60 s farm refuses new jobs + alert | Kill supervisor → restarts; jobs refused while down |
| H8 | PC dead entirely | Hardware layers 1–2 still active; robot controller watchdog (500 ms) | Robot controlled stop; printers finish/stop on firmware; smoke/heat still cut mains | Unplug PC mid-robot-routine (Phase 5) → robot stops < 1 s |
| H9 | Robot collision / pinch / person in cell | Following-error (encoder vs command), current limit, limit switches, interlocks; E-stop | Controller fault-stop; latched until reset + re-home | Push the arm by hand during a slow move → fault E04 |
| H10 | Robot moves into a hot or running printer | Interlocks: printer idle, bed < 35 °C, toolhead parked, door state, camera OK (checked on PC + permit lease on controller) | Routine refused (E06) | Try to run plate_swap mid-print in dry-run → refused |
| H11 | E-stop pressed | NC mushroom button in series with motor-driver power (category 0 stop) + input to controller | Motor power cut in hardware; controller → ESTOP; supervisor pauses printers + alert | Press during motion → motion stops, PC unaffected; twist-release does **not** restart motion |
| H12 | Phone "stop everything" | MCP `stop_all` (no confirmation, never rate-limited) | Pause both printers, robot halt, queue frozen | Send from phone → all paused, photo reply |
| H13 | Print failure (spaghetti, detached part) → mess/fire fuel | H2S built-in AI; Obico on Ender | Pause + photo alert | Fake spaghetti photo through Obico test endpoint |
| H14 | Bed not clear → crash into old part | Bed-clear camera check before every start (light forced on) | Start refused, alert with photo | Leave a part on the bed → start refused |
| H15 | Remote attacker / prompt injection via file names, MQTT, OCR | OAuth single-user allowlist, tool whitelist, no raw G-code, approved file library by hash, rate limits, action log; farm LAN segment | Reject + log + alert on denied auth bursts | Quarterly: invalid token, unknown file id, injected file name → all refused |
| H16 | Windows 10 out of support | ESU enrolment (runs to 2027-10-12) | — | Calendar: plan Linux move before 2027-07 |

### Robot rows (Prompt A, Gate 1 draft — rail-SCARA, see ARCHITECTURE_ROBOT.md)
Only the Z column carries weight; the SCARA joints swing in a horizontal plane. Design target: tool force ≤ 50 N in the shared zone (*assumed*, below the PF3400's 100 N; check against ISO/TS 15066 tables before Phase 3).

| # | Hazard | Detection | Automatic action | Test (monthly unless noted) |
|---|---|---|---|---|
| H17 | Z column drops on power loss, E-stop or a drive fault | Brake is power-off-applied; brake coil fed through the E-stop contactor | Power gone = brake on; revolute joints have no gravity load so nothing else falls | Cut mains with 1.5 kg on the hand at the top of Z → drop < 1 mm |
| H18 | Pinch/crush between SCARA links, or hand vs printer frame/door | Motor current caps per axis, following error, output-encoder mismatch, breakaway flange microswitch | Fault-stop (E04/E07), latched; links have finger gaps ≥ 25 mm or ≤ 8 mm | Spring scale at the tool during a slow move → stop below 50 N |
| H19 | Printer moves (bed, toolhead, door) while the hand is inside | Robot sets `inside_printer`; farm server refuses `project_file`, `gcode_line`, OctoPrint jobs while it is set | Print start refused; robot keeps its permit only while the printer stays idle | Dry run: start a print with the arm inside → refused |
| H20 | Bed lowered/raised by `gcode_line` into the hand | Only reviewed server constants move the bed, and only with the hand outside the printer envelope | Command refused if `inside_printer` | Unit test + dry run |
| H21 | 24 V bus overvoltage from regen (decelerating Z/X) | Bus voltage monitor on the controller | TVS / brake resistor absorbs it; decel limits; fault if > 30 V | E-stop from top speed, log bus < 30 V |
| H22 | Stylus ground path ties robot and printer electrics together | Stylus bonded only to robot 0 V / PSU earth, never into printer internals | — | Measure tip-to-printer-chassis < 1 V AC with the robot on (once at build) |
| H23 | Steel plate dropped (sharp edge, part flung) | Gripper load + FSR "plate present" | Fault-stop, alert; plates carried ≤ 150 mm above the table outside printers | Pull the plate from the jaws by hand → fault |
| H24 | Hands caught at the X rail carriage, belt or cable chain | Soft limits + hard end stops; brush/cover strip over belt and carriage | — | Visual check, end-stop trip test |
| H25 | Person in the cell when a job starts | Amber beacon + buzzer 3 s before motion; supervisor "home occupied" flag (phone/Pushover ack); guard + door interlock if Q3 = kids/pets | Unattended jobs only when nobody is flagged home, or after the warning | Start a job while flagged occupied → refused / warned |

**Latch detail (H1/H2):** smoke and heat contacts drive a 12 V self-holding relay (DPDT: one pole holds itself, one pole signals the IoT Relays). A NC "RESET" button breaks the hold. Fail-safe check: if the 12 V supply dies, the IoT Relays use their "normally ON" outlets → printers keep power (this is the one non-fail-safe point; mitigated by the supervisor monitoring the 12 V rail and the smart plugs as a second cut). **Open question:** Prompt A/electrician review of this before Phase 3.

**Mains wiring:** everything above is plug-in or low-voltage (≤ 24 V). No hard-wired 120 V changes without a licensed electrician.

**Suppression:** one automatic extinguisher (thermally triggered, e.g. AFO ball / tube type) mounted above the Ender (open frame); ABC 5 lb extinguisher by the room door; nothing flammable stored on or above the station.

Monthly routine (10 min, logged in `logs/safety_tests.csv`): H1 button, H4 power reading, H6 kill test, H11 E-stop, H12 phone stop, extinguisher gauge.
