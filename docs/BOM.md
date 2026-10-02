# FarmHand robot — LEAN buy list (v1, plates + door + screen)

**Total ≈ C$730 before tax (~C$840 with tax/shipping).** Replaces the C$2,302 "industrial" list in
[BOM_draft.md](BOM_draft.md), which is kept only as the upgrade path.

**Why it got cheaper without losing the design:** the SCARA's arm joints never hold weight, so
- 42 mm **NEMA 17** stepper motors (C$15) replace the 57 mm NEMA 23s (C$50);
- **TMC2209** driver chips (C$7) replace C$53 closed-loop drivers. Closed loop (R7) now comes from a
  C$9 **magnetic encoder** (a chip that reads the exact angle of a magnet glued on the joint) on every
  joint output, which our firmware checks;
- **V-slot extrusion + rolling wheels** replace steel linear rails;
- a **T8×2 lead screw** (2 mm per turn) lifts Z. It is *self-locking*: friction is bigger than the push
  the weight makes along the thread, so the arm can't fall with power off, so no brake.

Costs of going lean: slower moves (shoulder 180° in 2.2 s instead of 1.5 s; plate swap ~2 min, still
under the 3 min target), Z travels at ~20 mm/s, and wheels need re-tightening every few months.
Torque check for this version: `design/phase1_torque_pass.md` → "Lean variant" (all OK under the 70 % rule).

**Links:** shop pages were blocked during research, so most links are **store searches** (pick a
listing with good reviews), and prices are estimates. Me and Cowork can verify at checkout.

| # | Item | For | Qty | ~CAD each | ~CAD line | Link |
|---|---|---|---|---|---|---|
| 1 | NEMA 17 stepper, 0.59 N·m, 2 A (e.g. 17HS19-2004S1) | X, Z, J1, J2, wrist | 5 | 15 | 75 | [StepperOnline 17HS19-2004S1](https://www.omc-stepperonline.com/nema-17-bipolar-59ncm-84oz-in-2a-42x48mm-4-wires-w-1m-cable-connector-17hs19-2004s1) |
| 2 | TMC2209 driver module (UART) | one per motor + 1 spare | 6 | 7 | 42 | [Amazon.ca search](https://www.amazon.ca/s?k=TMC2209+stepper+driver) |
| 3 | MT6701 magnetic encoder board + diametric magnet | closed loop on every joint | 6 | 9 | 54 | [AliExpress search](https://www.aliexpress.com/w/wholesale-MT6701-encoder.html) |
| 4 | ESP32-S3 DevKitC-1 N16R8 | motion controller | 1 | 25 | 25 | [Amazon.ca search](https://www.amazon.ca/s?k=ESP32-S3+DevKitC-1+N16R8) |
| 5 | 24 V 15 A power supply (Mean Well LRS-350-24 or similar) | motor power | 1 | 45 | 45 | [Amazon.ca search](https://www.amazon.ca/s?k=LRS-350-24) |
| 6 | Feetech STS3215 servo + serial bus board | gripper (reports grip force) | 1 | 40 | 40 | [Amazon.ca search](https://www.amazon.ca/s?k=STS3215+servo) |
| 7 | 2040 V-slot: 1.5 m (X rail) + 1.0 m (Z column) + corner brackets + T-nuts | frame | 1 | 55 | 55 | [Makerstore.cc V-slot](https://www.makerstore.cc/product-category/v-slot/) |
| 8 | V-slot gantry plate kit with 4 wheels + eccentric spacers | X carriage, Z carriage | 2 | 18 | 36 | [Amazon.ca search](https://www.amazon.ca/s?k=v-slot+gantry+plate+2040+wheels) |
| 9 | T8×2 lead screw 1000 mm + brass nut + 5→8 mm coupler + KP08 bearing | Z lift (self-locking) | 1 | 25 | 25 | [Amazon.ca search](https://www.amazon.ca/s?k=T8+lead+screw+1000mm+pitch+2mm) |
| 10 | GT2 6 mm belt 5 m + 16T/20T/64T pulleys + idlers | X drive, J1 1:16, J2 1:8, wrist 1:4 | 1 | 40 | 40 | [Amazon.ca search](https://www.amazon.ca/s?k=GT2+64+tooth+pulley+8mm+bore) |
| 11 | Bearings: 6806 ×2, 6805 ×2, 6704 ×2, 608 ×6 | J1, J2, wrist, idlers | 1 | 35 | 35 | [Amazon.ca search](https://www.amazon.ca/s?k=6806-2RS+bearing) |
| 12 | Micro limit switches | homing + hard stops | 6 | 1.7 | 10 | [Amazon.ca search](https://www.amazon.ca/s?k=micro+limit+switch+3d+printer) |
| 13 | Cable chain 10×15, 1.5 m | hidden cables on X | 1 | 18 | 18 | [Amazon.ca search](https://www.amazon.ca/s?k=cable+drag+chain+10x15) |
| 14 | 24 V 30 A relay + socket ×2 (E-stop cuts motor power) | safety, category-0 stop | 1 | 20 | 20 | [Amazon.ca search](https://www.amazon.ca/s?k=24V+30A+relay+socket) |
| 15 | Wiring: silicone wire 18/22 AWG, JST-XH kit, blade fuses + holder, terminal blocks | wiring | 1 | 50 | 50 | [Amazon.ca search](https://www.amazon.ca/s?k=JST+XH+connector+kit) |
| 16 | Hand: MGN9 100 mm rail+carriage ×2, FSR402 ×2, conductive stylus tip, 10 mm steel balls ×6 | gripper + stylus + quick-change seat | 1 | 65 | 65 | [MGN9](https://www.amazon.ca/s?k=MGN9+100mm), [FSR402](https://www.amazon.ca/s?k=FSR402), [stylus tip](https://shop.adaptarobotics.com/en-us/products/compressible-touch-panel-test-stylus) |
| 17 | M3/M4/M5 screw + T-nut + heat-set insert top-up | assembly | 1 | 25 | 25 | [Amazon.ca search](https://www.amazon.ca/s?k=M5+heat+set+insert) |
| 18 | PETG 2 kg + TPU 0.5 kg (skip what you already have) | printed parts, fin-ray pads | 1 | 70 | 70 | — |
| | **Total** | | | | **≈ 730** | |

**You already have (C$0):** M2–M4 screw kit, M3 heat-set inserts + tips, calipers, solder, grease, magnets.
**On other lists:** E-stop button (SHOPPING.md Phase 3); wrist + overhead cameras (SHOPPING.md Phase 5, ~C$180).
**Later / optional:** extra H2S plate (~C$84 each), extra Ender sheet (~C$25), crimper if you don't own one (~C$45),
v2 spool tool (~C$55).
