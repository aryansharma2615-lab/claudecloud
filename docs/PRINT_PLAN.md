# FarmHand rail-SCARA v1 — print plan

Grams = solid mass × 0.45 (≈ 4 walls + 35 % gyroid). Hours from ~25 g/h on the H2S, ~12 g/h on the Ender (estimates; the slicer has the final number). PETG-CF needs a hardened nozzle; **plain PETG is fine for the first build** (the lean BOM buys PETG).

| Part | Qty | Printer | Material | Orientation | ~g each | ~h each |
|---|---|---|---|---|---|---|
| shoulder_housing | 1 | Bambu H2S | PETG (CF later) | deck down | 194 | 7.8 |
| upper_arm_root | 1 | Bambu H2S | PETG (CF later) | spigot up (bearing seats print round) | 85 | 3.4 |
| upper_arm_link | 1 | Bambu H2S | PETG (CF later) | open side down, flange flat | 78 | 3.1 |
| forearm | 1 | Bambu H2S | PETG (CF later) | open side down, diagonal | 105 | 4.2 |
| wrist_flange | 1 | Bambu H2S | PETG (CF later) | V-grooves up (no support in the grooves) | 27 | 1.1 |
| hand_body | 1 | Bambu H2S | PETG (CF later) | ball sockets up | 133 | 5.3 |
| jaw_left | 1 | Ender 3 S1 Pro | PETG (CF later) | on its side | 10 | 0.8 |
| jaw_right | 1 | Ender 3 S1 Pro | PETG (CF later) | on its side | 10 | 0.8 |
| finray_pad | 2 | Ender 3 S1 Pro | TPU 95A | flat | 3 | 0.3 |
| plate_shoe | 4 | Ender 3 S1 Pro | PETG (CF later) | flat, slot horizontal | 18 | 1.5 |
| z_motor_mount | 1 | Ender 3 S1 Pro | PETG (CF later) | base down | 24 | 2.0 |

- **Bambu H2S:** ~622 g, ~25 h
- **Ender 3 S1 Pro:** ~124 g, ~10 h
- **Total filament:** ~0.7 kg — the 2 kg PETG on the lean BOM covers it with spares.

**Print first (1 h):** a fit coupon with one 6806, 6805 and 6704 bearing seat + an M3 insert hole, to tune `SEAT_CLR` in `cad/params.py` before the big parts.
