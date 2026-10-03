# DESIGN_DECISIONS — Shawarma Servo Mount v1 (AV v8 demo)

> **Header: provisional.** Two rows below are defects-with-a-paper-trail until the SG90 is calipered:
> the worst-case window stack-up FAILS on datasheet spread, and the CAD tab-hole ligament (1.45 mm) is
> under the 1.60 house minimum. Nothing here is GREEN until MEASURE_ME rows 1–2 are done.
> Numbering starts here (first record for this part) and never restarts.

## §1 Decisions
| # | asked / sketched | built | why (the number) |
|---|---|---|---|
| D1 | 25 × 25 mm pocket, M3 holes (original brief) | window **23.1 × 12.5**, **M2** self-tappers at pitch 27.8 | SG90 body is ~22.8 × 12.2 and its tabs take M2. A 25 × 25 pocket leaves 12.8 mm of slop on the short axis — the servo rattles. |
| D2 | servo shaft vertical | shaft **horizontal**, arm swings a vertical plane | A vertical shaft puts gravity ⟂ to the joint: 0 torque, nothing to TEST. Horizontal: τ = m·g·r·cosθ, max 0.70 kgf·cm at 0.2 kg on 35 mm. |
| D3 | window clearance 0.20 / side (H11/c11 mid-band) | **0.15 / side** | Every 0.05 of clearance costs 0.05 of ligament. At 0.20 the CAD ligament is 1.40; at 0.15 it is 1.45 (D4). Rejected 0.10: printed window 22.9 vs body 22.8 = 0.1 mm total, below the 0.1–0.3 running band on one side. |
| D4 | pilot Ø1.5 for M2 | pilot **Ø1.8** | Profile: Ø1.5 prints Ø1.13 → −0.87 mm bite = "split" band. Ø1.8 prints Ø1.48 → −0.52 = self-tap bite band (−0.3…−0.6). Cost: CAD ligament 1.60 → **1.45** (< 1.60 house rule); as printed ≈ **1.66** after both holes shrink. Logged as a WARN, not hidden. |
| D5 | M3 into inserts in the base | inserts in the **cradle foot**, screws **from the bottom** through the base | One screw pair clamps base + cradle. Foot 8.0 thick = bore 6.2 + 1.8 cover (≥ 1.40 rule). Engagement 5.4 ≥ 1.5·d = 4.5; tip gap 0.8 to the bore end. |
| D6 | base 5 mm | base **6.0** with Ø6 × 3.4 counterbores | At 5 mm the head left 1.0 mm under it (< 1.60 wall). 6.0 leaves 2.6. |
| D7 | cradle printed wall-down | **foot down** | Inserts go in from the bed face (load in shear). Price: wall bending pulls layers apart (Z) — checked at Z = 0.5 × XY and target SF 3: SF 47 at 0.2 kg. |
| D8 | arm printed on edge | arm **flat, horn pocket up** | Bending stress runs along the arm = in the layer plane (XY strength), 25 layers, 15.5 min. |
| D9 | arm root sharp step | v1 ships **sharp (r 0.2)**; fix = **r 2.0 fillet** shown in TEST | Peterson Kt 2.43 → 1.34. Arm breaks at **2.24 kg** sharp vs **4.05 kg** filleted (35 mm lever). The SG90 stalls at **0.51 kg** either way, so v1 is safe — the fillet is margin, kept visible as a teaching case. |
| D10 | 5 kg test load | slider **0–5 kg, lever 10–40 mm**, default **0.2 kg @ 35 mm** | 5 kg at 35 mm = 17.5 kgf·cm = 9.7 × SG90 stall. Default sits at 39 % of stall (< 50 % continuous rule). |
| D11 | design arm on +Y | turned **180° about Z**: arm side faces the engine's FRONT (−Y) | Engine convention FRONT = −Y; built the other way, the screws read "BACK" and the default view showed the back. Physics unchanged (same SFs to 4 figures) — the calc now uses CAD direction vectors, not assumed axes. |
| D12 | emboss 0.5 mm | **0.6 mm** | 3 layers at 0.2; 0.5 is 2.5 layers and the slicer rounds it unpredictably. |
| D13 | Prusa MK4 / Bambu 3MF | Ender 3 S1 Pro; G-code from **PrusaSlicer 2.7 CLI** with the stock Creality Ender-3 S1 Pro profile | Real grams/minutes (base 9.43 g / 55 min, cradle 15.63 g / 2 h 02, arm 2.07 g / 15.5 min). Creality Print on the Mac will read a few % different — labelled `SLICER · PrusaSlicer`. |
| D14 | PETG-CF | **PETG** | CF eats a brass nozzle in a few hundred grams. H2S nozzle unconfirmed → no CF offer. |

## §2 Assumptions (most dangerous first)
| assumption | value | basis | risk |
|---|---|---|---|
| **SG90 body length / hole pitch** | 22.8 / 27.8 | datasheets disagree (22.2–23.0 / 27.5–28) | **Load-bearing pair.** Worst-case window stack-up = **−0.10 mm (FAIL)**; RSS −0.02. Tightest clearance in the design: window long side, 0.20 mm nominal. Measure before printing. |
| hole shrink (profile) | printed = CAD − 0.10 − 0.40/CAD | placeholder model | every FIT colour + the pilot bite (D4) |
| PETG yield XY / Z factor / E / Tg | 45 MPa / 0.5 / 2000 MPa / 80 °C | fallback values | all SFs, deflection, temp check → UNVERIFIED |
| SG90 stall | 1.8 kgf·cm @ 4.8 V | datasheet | TEST verdict |
| tab pivot lever | 6.1 mm | half body width | tab-screw SF |
| insert pull-out | none | no data | insert check has no limit |
| stall current / supply | 0.65 A / 2 A | widely quoted / unknown brick | PSU check |

## §3 Open items → v2
1. Caliper the SG90 (MEASURE_ME #4) → re-run: window + ligament go PASS or force a redesign (e.g. bosses that move the screws off the window edge).
2. Print + measure the hole coupon → `tolerance_profile_ender3s1pro.json` coupon[].measured.
3. Weigh the parts; spool datasheet → most UNVERIFIED tiles resolve.
4. Bake the r 2.0 arm-root fillet into CAD (D9) once the coupon confirms the pocket fit.
5. Optional: FreeCAD FEM (CalculiX) offline on the arm → per-vertex colours labelled `FEA`, compare with the CALC heatmap.

**Rule learned → propose to `/sp-print-dfm`:** *size self-tap pilots to the PRINTED diameter, not the CAD one —
small holes shrink ~0.3 mm on the Ender, so an M2 pilot is Ø1.8 in CAD, and check the ligament on both CAD and printed geometry.*
