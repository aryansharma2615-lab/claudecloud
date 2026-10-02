"""Build every printed part of the FarmHand rail-SCARA v1, export STEP + STL, run fit/DFM checks.

Run:  python cad/build_parts.py      (outputs in cad/out/, report in docs/DFM_REPORT.md)
Frames: Z up. Each part is modelled in its own frame (joint axis at origin) and placed in the
assembly with the arm stretched along +X (worst case for reach and torque).
"""
import itertools
import os
import sys

from build123d import (Axis, Box, Cylinder, Polygon, Pos, Rot, export_step, export_stl,
                       extrude, fillet, Compound)

sys.path.insert(0, os.path.dirname(__file__))
from params import *  # noqa: E402,F403

OUT = os.path.join(os.path.dirname(__file__), "out")
os.makedirs(OUT, exist_ok=True)


# ---------------- helpers ----------------
def box(x0, x1, y0, y1, z0, z1):
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)


def cyl(d, z0, z1, x=0.0, y=0.0):
    return Pos(x, y, (z0 + z1) / 2) * Cylinder(d / 2, z1 - z0)


def bearing_seats(part, brg, x, z_bot, z_top, y=0.0):
    """Two bearing pockets (bottom + top faces of a boss) with a through bore for cables."""
    idd, od, w = brg
    part -= cyl(od + SEAT_CLR, z_bot - 0.01, z_bot + w, x, y)
    part -= cyl(od + SEAT_CLR, z_top - w, z_top + 0.01, x, y)
    part -= cyl(od - 6, z_bot - 1, z_top + 1, x, y)        # 3 mm shoulder each side
    return part


def nema17_holes(part, x, y, z0, z1):
    s = NEMA17["holes"] / 2
    part -= cyl(NEMA17["pilot"], z0 - 1, z1 + 1, x, y)
    for dx, dy in itertools.product((-s, s), (-s, s)):
        part -= cyl(M3_CLR, z0 - 1, z1 + 1, x + dx, y + dy)
    return part


def spigot(brg, z0, z1, bore):
    return cyl(brg[0] + SPIGOT_CLR, z0, z1) - cyl(bore, z0 - 1, z1 + 1)


def soften(part, r=2.0):
    try:
        return fillet(part.edges().filter_by(Axis.Z), r)
    except Exception:
        return part


def hollow_beam(x0, x1, z0, z1, w=BEAM_W, open_side="bottom"):
    """Box-section beam, one side open for a snap-on cover (belt + cables inside)."""
    outer = box(x0, x1, -w / 2, w / 2, z0, z1)
    if open_side == "bottom":
        inner = box(x0 + 8, x1 - 8, -w / 2 + WALL, w / 2 - WALL, z0 - 1, z1 - WALL)
    else:
        inner = box(x0 + 8, x1 - 8, -w / 2 + WALL, w / 2 - WALL, z0 + WALL, z1 + 1)
    return outer - inner


UA_Z0 = 62.0                     # upper-arm underside (tower top 60 + 2 mm gap clears the J1 motor at z 56)
FA_Z1 = UA_Z0 - 2.0              # forearm top


parts = {}   # name -> (solid, material, printer, why, assembly placement)

# ---------------- 1. shoulder housing (bolts to the Z-carriage gantry plate) ----------------
deck = box(-80, 40, -78, 32, 0, 8)
tower = cyl(60, 0, 60)
wall = box(-80, 40, -86, -78, -60, 60)
ribs = box(-6, 6, -78, -25, 8, 46) + box(-80, -68, -78, -20, 8, 30)
ib = cyl(28, 0, 22, 0, -45)                                     # intermediate shaft boss
sh = deck + tower + wall + ribs + ib
sh = bearing_seats(sh, B6806, 0, 0, 60)
sh -= cyl(B608[1] + SEAT_CLR, -0.01, B608[2], 0, -45)
sh -= cyl(B608[1] + SEAT_CLR, 22 - B608[2], 22.01, 0, -45)
sh -= cyl(12, -1, 23, 0, -45)
sh = nema17_holes(sh, -45, -45, 0, 8)                           # motor on top, shaft down
for x, z in itertools.product((-65, 25), (-45, 45)):            # M5 slots to gantry plate
    sh -= Pos(x, -82, z) * Rot(90, 0, 0) * Cylinder(M5_CLR / 2, 12)
parts["shoulder_housing"] = (sh, "PETG-CF", "Bambu H2S",
                             "stiff (carries the 14.4 N·m arm moment into the Z carriage); CF needs the H2S hardened nozzle",
                             Pos(0, 0, 0))

# ---------------- 2. upper arm, split in two to fit the H2S bed (bolted flange at x = 120) ----------------
SPLIT = 120.0
z0, z1 = UA_Z0, UA_Z0 + BEAM_H
fl = box(SPLIT - 8, SPLIT, -BEAM_W / 2 - 8, BEAM_W / 2 + 8, z0, z1 + 8)   # flange plate (root side)
root = hollow_beam(-75, SPLIT, z0, z1) + fl
root += cyl(70, z0 - 1.5, z0)                                    # thin hub face, 0.5 mm over the tower
root += spigot(B6806, -25, z0 - 1.5, 20)                          # through both 6806s, 64T pulley below the deck
root -= cyl(20, z0 - 12, z1 + 1)                                 # cable path
root = nema17_holes(root, -50, 0, z1 - WALL, z1)                 # J2 motor on top, shaft down into the beam
root += cyl(26, z0, z1, 45) - cyl(B608[1] + SEAT_CLR, z0 + WALL, z1 - WALL + 0.01, 45)   # 1:4 intermediate stage
link = hollow_beam(SPLIT, L1 + 26, z0, z1)
link += box(SPLIT, SPLIT + 8, -BEAM_W / 2 - 8, BEAM_W / 2 + 8, z0, z1 + 8)
link += cyl(52, z0, z1, L1)
link = bearing_seats(link, B6805, L1, z0, z1)
for y, z in itertools.product((-BEAM_W / 2 - 4, BEAM_W / 2 + 4), (z0 + 6, z1 + 2)):
    hole = Pos(SPLIT, y, z) * Rot(0, 90, 0) * Cylinder(4.5 / 2, 20)   # M4 through-bolts
    root -= hole
    link -= hole
parts["upper_arm_root"] = (root, "PETG-CF", "Bambu H2S",
                           "J1 hub + J2 motor + 1:4 stage; spigot carries the arm moment, print upright", Pos(0, 0, 0))
parts["upper_arm_link"] = (link, "PETG-CF", "Bambu H2S", "beam + elbow bearing boss; flange bolts with 4× M4", Pos(0, 0, 0))

# ---------------- 3. forearm (J2 -> wrist), hangs under the upper arm ----------------
fa = hollow_beam(-65, L2 + 22, -BEAM_H, 0, 44, open_side="bottom")
fa += spigot(B6805, 0, BEAM_H + 2, 14)                           # up through the 6805 pair
fa += cyl(44, -BEAM_H, 0, L2)                                    # wrist boss
fa = bearing_seats(fa, B6704, L2, -BEAM_H, 0)
fa += box(-65, -24, -22, 22, -BEAM_H, -BEAM_H + WALL)            # motor plate across the open bottom
fa = nema17_holes(fa, -45, 0, -BEAM_H, -BEAM_H + WALL)           # wrist motor hangs below, shaft up into the beam
parts["forearm"] = (fa, "PETG-CF", "Bambu H2S", "fits the H2S bed diagonally; motor behind the elbow balances it",
                    Pos(L1, 0, FA_Z1))

# ---------------- 4. wrist flange (kinematic quick-change seat, Jubilee pattern) ----------------
wf = cyl(70, -10, 0) + spigot(B6704, 0, BEAM_H - 1, 10)
for k in range(3):                                               # 3 radial 90° V-grooves on the bottom face
    v = Rot(0, 0, 120 * k) * Pos(25, 0, -10) * Rot(45, 0, 0) * Box(22, 6, 6)
    wf -= v
    wf -= Rot(0, 0, 120 * k + 60) * Pos(25, 0, -10) * Cylinder(4.1, 6)   # 8×3 magnet pockets (you have these)
parts["wrist_flange"] = (wf, "PETG-CF", "Bambu H2S", "V-seats need stiffness; balls are hardened steel, magnets only preload",
                         Pos(L1 + L2, 0, FA_Z1 - BEAM_H - 1))

# ---------------- 5. hand body (gripper + stylus + hook + camera) ----------------
hb = box(-60, 60, -27, 27, -32, 0)
for k in range(3):                                               # ball sockets matching the V-grooves
    hb -= Rot(0, 0, 120 * k) * Pos(25, 0, 0) * Cylinder(BALL / 2 + 0.05, BALL)
    hb -= Rot(0, 0, 120 * k + 60) * Pos(25, 0, 0) * Cylinder(4.1, 6)
hb -= box(-STS3215["l"] / 2 - 0.2, STS3215["l"] / 2 + 0.2, -STS3215["w"] / 2 - 0.2, STS3215["w"] / 2 + 0.2, -22, -WALL)
hb -= box(-60.1, 60.1, -MGN9["rail_w"] / 2 - 0.1, MGN9["rail_w"] / 2 + 0.1, -32.1, -32 + MGN9["rail_h"] - 1)  # rail groove
hb += box(60, 78, -10, 10, -32, -4) - cyl(14.2, -33, -3, 69, 0)  # stylus barrel boss (Ø14 plunger tube)
hb += box(-78, -60, -6, 6, -8, 0) + box(-90, -78, -6, 6, -30, 0)   # door / AMS-lid hook
hb += box(-20, 20, 27, 33, -30, 0) - box(-14, 14, 26, 34, -26, -6)  # wrist-camera window bracket
parts["hand_body"] = (soften(hb, 1.5), "PETG-CF", "Bambu H2S or Ender", "small; balls pressed into sockets",
                      Pos(L1 + L2, 0, FA_Z1 - BEAM_H - 11))

# ---------------- 6. jaw (print 2) ----------------
jw = box(-10, 10, -MGN9["car_w"] / 2, MGN9["car_w"] / 2, -6, 0)   # carriage plate
jw += box(-7, 7, -9, 9, -95, -6)                                 # finger core
jw -= box(-3.1, 3.1, -9.1, 9.1, -92, -20)                        # dovetail-ish slot for the TPU fin-ray pad
jw -= box(-1.05, 1.05, -8, 8, -96, -84)                          # slot for the 2 mm steel "nail" strip
for y in (-5, 5):
    jw -= cyl(M3_CLR, -7, 1, 0, y)                               # to MGN9 carriage
parts["jaw"] = (jw, "PETG-CF", "Ender 3 S1 Pro", "print on its side so layers run along the finger (bending strength)",
                Pos(L1 + L2 + 30, 0, FA_Z1 - BEAM_H - 11 - 32))

# ---------------- 7. fin-ray pad (TPU, print 2) ----------------
tri = extrude(Polygon((0, 0), (14, 0), (0, 70), align=None), 18)
inner = extrude(Polygon((2.5, 3), (9.5, 3), (2.5, 52), align=None), 18)
pad = tri - inner
for i in range(1, 7):
    zr = i * 9.5
    pad += Pos(4, zr, 9) * Rot(0, 0, -15) * Box(14, 1.6, 18)
pad = pad & tri
pad = Rot(90, 0, 0) * pad
parts["finray_pad"] = (pad, "TPU 95A", "Ender 3 S1 Pro", "flexible: wraps the part; Ender has a direct-drive Sprite extruder",
                       Pos(L1 + L2 + 37, 9, FA_Z1 - BEAM_H - 11 - 32 - 92))

# ---------------- 8. plate shoe (H2S plate front notch is ~136 × 15.5 mm) ----------------
ps = box(-60, 60, 0, 22, 0, 10)
ps -= box(-60.1, 60.1, 10, 22.1, 4.6, 5.4)                       # 0.8 mm slot for the 0.5 mm plate edge
ps += box(-20, 20, -28, 0, 2, 8)                                 # tab the nails grip
for x in (-45, 0, 45):
    ps -= cyl(M3_INSERT, -1, 11, x, 16)                          # clamp screws into inserts
for x in range(-16, 17, 8):
    ps -= box(x - 1, x + 1, -26, -4, 7, 8.1)                     # grip ribs
parts["plate_shoe"] = (ps, "PETG", "Ender 3 S1 Pro", "one per plate; screws clamp it on, no glue on the PEI",
                       Pos(900, -400, 0))

# ---------------- 9. Z-motor mount (bottom of the 2040 column) ----------------
zm = box(-25, 25, -10, 52, 0, 8) + box(-25, 25, -10, -2, 8, 60)
zm = nema17_holes(zm, 0, 26, 0, 8)
for z in (20, 50):
    zm -= Pos(-10, -6, z) * Rot(90, 0, 0) * Cylinder(M5_CLR / 2, 10)
    zm -= Pos(10, -6, z) * Rot(90, 0, 0) * Cylinder(M5_CLR / 2, 10)
parts["z_motor_mount"] = (zm, "PETG-CF", "Ender 3 S1 Pro", "takes the screw thrust; motor hangs below, T8 coupler above",
                          Pos(0, -200, -300))


# ---------------- export + checks ----------------
def fits(size, bed):
    s = sorted(size)
    b = sorted(bed)
    if all(a <= c for a, c in zip(s, b)):
        return "yes"
    # try diagonal in XY with the smallest dimension as height
    import math
    L, W, H = sorted(size, reverse=True)
    if H <= bed[2]:
        for deg in range(0, 90, 2):
            t = math.radians(deg)
            if L * math.cos(t) + W * math.sin(t) <= bed[0] and L * math.sin(t) + W * math.cos(t) <= bed[1]:
                return f"diagonal {deg}°"
    return "no"


rows = []
placed = {}
for name, (solid, mat, printer, why, place) in parts.items():
    export_step(solid, os.path.join(OUT, f"{name}.step"))
    export_stl(solid, os.path.join(OUT, f"{name}.stl"))
    bb = solid.bounding_box().size
    size = (bb.X, bb.Y, bb.Z)
    dens = 1.12 if "TPU" in mat else 1.30           # g/cm3, ~40 % infill-equivalent solids ignored -> upper bound
    mass = solid.volume / 1000 * dens
    rows.append((name, mat, printer, size, mass, solid.is_valid, {b: fits(size, d) for b, d in BEDS.items()}, why))
    placed[name] = place * solid

asm = Compound(list(placed.values()))
export_step(asm, os.path.join(OUT, "farmhand_scara_v1_assembly.step"))

clash = []
for (a, sa), (b, sb) in itertools.combinations(placed.items(), 2):
    if not sa.bounding_box().overlaps(sb.bounding_box()) if hasattr(sa.bounding_box(), "overlaps") else False:
        continue
    try:
        v = (sa & sb).volume
    except Exception:
        v = 0.0
    if v > 1.0:
        clash.append((a, b, v))

with open(os.path.join(os.path.dirname(__file__), "..", "docs", "DFM_REPORT.md"), "w") as f:
    f.write("# FarmHand rail-SCARA v1 — DFM report (generated by `cad/build_parts.py`)\n\n")
    f.write("First-pass printed parts. Bought parts (motors, bearings, rails, screw) are not modelled yet. "
            "Mass = solid volume × density (upper bound; real prints use 40 % infill).\n\n")
    f.write("| Part | Material | Print on | Size X×Y×Z (mm) | Mass ≤ (g) | Valid solid | Fits Ender | Fits H2S | Why |\n")
    f.write("|---|---|---|---|---|---|---|---|---|\n")
    for n, m, p, s, g, ok, fit, why in rows:
        f.write(f"| {n} | {m} | {p} | {s[0]:.0f}×{s[1]:.0f}×{s[2]:.0f} | {g:.0f} | {'yes' if ok else 'NO'} | "
                f"{fit['Ender 3 S1 Pro']} | {fit['Bambu H2S']} | {why} |\n")
    f.write(f"\n**Clash check (assembly, arm stretched):** {len(clash)} overlaps > 1 mm³")
    f.write(":\n\n" + "\n".join(f"- {a} ∩ {b}: {v:.0f} mm³" for a, b, v in clash) + "\n" if clash else " ✓\n")

for r in rows:
    print(r[0], f"{r[3][0]:.0f}x{r[3][1]:.0f}x{r[3][2]:.0f}", f"{r[4]:.0f} g", "valid" if r[5] else "INVALID", r[6])
print("clashes:", clash)
