# Design brief — Shawarma Servo Mount v1 (/sp-design-brief, before any geometry)

An SG90 bracket you bolt to a surface; a printed arm on the horn carries a test load. It is the AV v8 demo
part, so every interface is written down and every unmeasured number is ledgered.

## 1. Interface inventory
| interface | mating part | envelope W×H×D (mm) | access needed | source |
|---|---|---|---|---|
| servo window | SG90 body | 22.8 × 12.2, 15.9 behind the tabs | slide in from the front, cable out the back | **assumed** (datasheets 22.2–23.0) |
| tab screws | M2 × 8 self-tapper, pan Ø3.8 | pitch 27.8 | PH0 straight on, from the front | assumed pitch; datasheet screw |
| output spline | SG90 horn (21T assumed) | hub Ø7 × 4 | horn pressed on after centring at 90° | assumed |
| arm ↔ horn | stock single horn in a 1.6 mm pocket | 16 long, 5 → 3.6 wide | horn screw through the arm hub | assumed |
| base ↔ cradle | 2 × M3 × 8 socket into RX-M3×5.7 inserts | Ø4.0 × 6.2 bore | 2.5 mm hex from the **bottom** | datasheet (/sp-print-dfm table) |
| base ↔ your surface | 2 slots 3.4 × 10 | — | your screws | spec |
| cable | SG90 3-wire + JR plug | plug body 7.6 × 2.6 × 14 | exits behind the wall, nothing pinches it | assumed plug size |
| load | test weight on a pin through Ø3.4 | 35 mm from the shaft | hang / swap weights | spec |

## 2. Worst case
SG90 clones vary: body 22.2 → 23.0 mm, pitch 27.5 → 28.0 mm. The window is sized for the **fat** body
(22.8 + 2 × 0.15). If yours measures 23.0, the window prints too tight (stack-up FAIL below) → open
`window_clear`, which costs tab-hole ligament one-for-one. **Measure first.**

## 3. Assumption ledger — blast radius first
| assumption | value | blast radius | if wrong |
|---|---|---|---|
| **SG90 body length + hole pitch** | 22.8 / 27.8 | **sets the window AND the ligament — the most dangerous pair** | +0.2 body → servo won't go in; −0.3 pitch → ligament 1.3 mm, tab screws split the wall |
| hole shrink on this printer | −0.10 − 0.40/Ø | every FIT colour, the pilot bite, the insert melt | pilots too tight (split) or too loose (no bite) |
| PETG yield / Z factor | 45 MPa / 0.5 | every safety factor | SFs scale 1:1 |
| SG90 stall torque | 1.8 kgf·cm @ 4.8 V | the TEST verdict | stall load moves 1:1 |
| horn mass, insert pull-out, stall current, supply rating | 0.3 g / none / 0.65 A / 2 A | one check each | see MEASURE_ME |

## 4. Measurement list → `MEASURE_ME.md` (auto-generated, sorted by blast radius)
1. SG90: body L × W × H, tab span, hole pitch, tab height, shaft offset (calipers)
2. Print + caliper the hole coupon (9 holes)
3. Weigh the three printed parts and the horn
4. Spool brand → datasheet (or a dog-bone pull in XY and Z)

## 5. Envelope + machine
Ender 3 S1 Pro 220 × 220 × 270, PETG, brass nozzle, open frame. Largest part (base, after D15) 80 × 54 × 6.6; tallest (cradle) 26 × 39.4 × 56 — fits.
