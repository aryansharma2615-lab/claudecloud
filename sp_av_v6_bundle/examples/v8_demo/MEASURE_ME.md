# MEASURE_ME — what to put calipers / a scale on (AV v8, auto-generated)

Assembly: **Shawarma Servo Mount v1**. Sorted by blast radius: the top row unlocks the most checks.
Every row is an `ASSUMED` number that keeps a check at UNVERIFIED. Measure → put the value in the YAML with
`src: MEASURED` → rebuild → the tile turns PASS (or FAIL, which is the point).

| # | measure | tool | unlocks | checks |
|---|---|---|---|---|
| 1 | print the hole coupon, measure 9 holes | calipers | 12 | fit:bore_a, fit:bore_b, fit:clr_a, fit:clr_b, fit:hornhole, fit:loadhole, fit:pilot0, fit:pilot1 … |
| 2 | spool brand → its datasheet (or print + pull a dog-bone in XY and Z) | datasheet / tensile coupon | 6 | defl, sf_arm, sf_arm_stall, sf_tabs, sf_wall, temp |
| 3 | weigh each printed part and the horn | kitchen scale (0.1 g) | 5 | mass:arm, mass:base, mass:cradle, torque_dyn, torque_hold |
| 4 | every SG90 dimension — body L × W × H, tab span, hole pitch, tab height, shaft offset | calipers | 3 | ligament, stack_tab_ligament, stack_window_x |
| 5 | keep — or model the fillet and run FreeCAD FEM (CalculiX) offline | design | 1 | sf_wall |
| 6 | tab edge to screw centre on the real SG90 | calipers | 1 | sf_tabs |
| 7 | hang weights off an M3 insert in a PETG test boss until it lets go | test boss | 1 | insert_pull |
| 8 | SG90 stall current at 5 V | USB power meter | 1 | psu |
| 9 | read the wall adapter's label (V, A) | label | 1 | psu |

## Calipers list (take this to the bench)

1. print the hole coupon, measure 9 holes
2. every SG90 dimension — body L × W × H, tab span, hole pitch, tab height, shaft offset
3. tab edge to screw centre on the real SG90
