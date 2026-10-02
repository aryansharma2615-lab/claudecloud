"""FarmHand robot - Phase 1 first torque pass (before any CAD).

Run:  python design/phase1_torque_pass.py  > design/phase1_torque_pass.md

Every input below is either SOURCED (docs/research/*.md, grade in comment) or ASSUMED
(to be replaced by Shawarma's measurements / CAD masses in Phase 2). Rules from Prompt A:
hold <= 50 % of rating, move <= 70 % of rating. Stepper ratings are derated for speed at 24 V
(ASSUMED 50 % of holding torque at working speed until the 24 V pull-out curve is read).
Pure Python on purpose: no numpy in this container, and the maths is short.
"""
from math import pi

G = 9.81
HOLD_MAX, MOVE_MAX = 0.50, 0.70

# ---------- motors and reducers (docs/research/motion_hardware.md, grade C unless noted) ----------
NEMA23_HOLD = 3.0           # N*m, 23HS45-4204-ME1K
NEMA17_HOLD = 0.59          # N*m, 17HS19-2004-ME1K class
PULLOUT_FRACTION = 0.50     # ASSUMED: torque left at working speed on 24 V (open question Q1 in research)
HHT25_RATED = 39.0          # N*m strain-wave 50:1, rated at 2000 rpm input
HHT14_RATED = 5.4           # N*m strain-wave 50:1
EG23_MAX = 30.0             # N*m planetary 20:1 "max permissible" (continuous rating not documented)
ETA_STRAINWAVE = 0.70       # ASSUMED conservative
ETA_PLANETARY = 0.90        # vendor says 94 %; use 90
ETA_BELT_STAGE = 0.95       # ASSUMED per belt stage
DYN_FACTOR = 1.30           # ASSUMED: acceleration adds 30 % on gravity joints (checked in Phase 2 sim)

# ---------- payloads ----------
SPOOL = 1.2                 # kg, R3/R4
SPOOL_TOOL = 0.3            # kg, what R4 leaves for the tool (end_effectors.md)
PAYLOAD = SPOOL + SPOOL_TOOL  # 1.5 kg at the farthest pose (R4)
# H2S plate: 0.5 mm stainless steel (printer_specifics.md, grade C/D), outline 355.0 x 346.5 mm (grade C code)
PLATE_MASS = 0.355 * 0.3465 * 0.0005 * 7900  # kg, steel only; WEIGH IT on arrival day
PARTS_ON_PLATE = 0.5        # kg, ASSUMED until Q4 (what SP prints)
HAND = 0.45                 # kg, ASSUMED multi-mode hand
PLATE_CG_FROM_GRIP = 0.3465 / 2  # m, plate gripped at its front edge


def pct(x, cap):
    return 100.0 * x / cap


def rule(p, limit):
    return "OK" if p <= 100 * limit else "FAIL"


rows = []


def add(arch, joint, case, need, cap, kind, note):
    p = pct(need, cap)
    limit = HOLD_MAX if kind == "hold" else MOVE_MAX
    rows.append((arch, joint, case, need, cap, p, kind, rule(p, limit), note))


# =====================================================================================
# A / B: 6-axis arm, shoulder (J2) and elbow (J3) gravity torque with the arm horizontal
# =====================================================================================
def six_axis(reach):
    """Static gravity torque at J2 and J3 for a 6-axis arm whose payload CG is `reach` from J2.
    Mass model ASSUMED (scaled from PAROL6/AR4 class arms, docs/research/open_arms.md):
    upper arm L1 = 0.5*reach, forearm+wrist = 0.5*reach; wrist group 1.0 kg at reach-0.08;
    forearm shell 0.8 kg*(reach/0.5) at mid-forearm; J3 actuator 1.8 kg at 0.3*L1 (belt-driven elbow);
    upper arm shell 0.8 kg*(reach/0.5) at L1/2."""
    L1 = 0.5 * reach
    L2 = reach - L1
    s = reach / 0.5
    wrist, fore, j3act, upper = 1.0, 0.8 * s, 1.8, 0.8 * s
    t_j2 = G * (PAYLOAD * reach + wrist * (reach - 0.08) + fore * (L1 + L2 / 2)
                + j3act * 0.3 * L1 + upper * L1 / 2)
    t_j3 = G * (PAYLOAD * L2 + wrist * (L2 - 0.08) + fore * L2 / 2)
    return t_j2, t_j3


for arch, reach in (("A fixed 6-axis (base between printers)", 0.65),
                    ("B 6-axis on rail", 0.45)):
    j2, j3 = six_axis(reach)
    add(arch, "J2 shoulder", f"1.5 kg at {reach:.2f} m, hold", j2, HHT25_RATED, "hold",
        "NEMA 23 + HHT-25-50 strain wave + brake")
    add(arch, "J2 shoulder", "same, moving (x1.3)", j2 * DYN_FACTOR, HHT25_RATED, "move", "")
    add(arch, "J3 elbow", "hold", j3, EG23_MAX, "hold",
        "NEMA 23 + EG23 20:1 (20 arcmin needs output encoder) + brake")
    add(arch, "J3 elbow", "moving (x1.3)", j3 * DYN_FACTOR, EG23_MAX, "move", "")
    # wrist pitch J5 holding the H2S plate by its front edge (plate cantilevers off the hand)
    j5 = G * ((PLATE_MASS + PARTS_ON_PLATE) * PLATE_CG_FROM_GRIP + HAND * 0.06)
    add(arch, "J5 wrist pitch", "H2S plate + parts held by front edge", j5, HHT14_RATED, "hold",
        "NEMA 17 + HHT-14-50 + brake")

# =====================================================================================
# D: SCARA on a Z column on an X rail. Revolute joints are vertical axes -> no gravity torque.
# =====================================================================================
L1, L2, MANDREL = 0.30, 0.25, 0.06          # m, ASSUMED link lengths (sized from reach study below)
R_PAY = L1 + L2 + MANDREL                   # payload CG radius from J1 at full stretch
m_wrist, m_fore, m_elbow, m_upper = 0.45, 0.35, 0.30, 0.45   # kg, ASSUMED

# J1 inertia about its own vertical axis, arm fully stretched (worst case)
I_J1 = (PAYLOAD * R_PAY ** 2 + m_wrist * (L1 + L2) ** 2
        + m_fore * (L1 ** 2 + L1 * (L1 + L2) + (L1 + L2) ** 2) / 3
        + m_elbow * L1 ** 2 + m_upper * L1 ** 2 / 3)
theta, t = pi, 1.5                          # 180 deg in 1.5 s, triangular velocity profile (ASSUMED)
alpha_j1 = 4 * theta / t ** 2
tau_j1 = I_J1 * alpha_j1 + 0.5              # + 0.5 N*m bearing/belt friction (ASSUMED)
cap_j1 = NEMA23_HOLD * PULLOUT_FRACTION * 10 * ETA_BELT_STAGE ** 2   # 2-stage belt 1:10
add("D rail-SCARA", "J1 shoulder (vertical axis)", f"1.5 kg at {R_PAY:.2f} m, 180 deg in 1.5 s",
    tau_j1, cap_j1, "move", "NEMA 23 closed loop + 2-stage HTD belt 1:10 + 14-bit output encoder")
add("D rail-SCARA", "J1 shoulder (vertical axis)", "gravity hold", 0.0, cap_j1, "hold",
    "vertical axis: gravity goes into the bearing, not the motor")

I_J2 = PAYLOAD * (L2 + MANDREL) ** 2 + m_wrist * L2 ** 2 + m_fore * L2 ** 2 / 3
alpha_j2 = 4 * pi / 1.2 ** 2                # 180 deg in 1.2 s
tau_j2 = I_J2 * alpha_j2 + 0.3
cap_j2 = NEMA23_HOLD * PULLOUT_FRACTION * 6 * ETA_BELT_STAGE ** 2    # motor sits at J1, belt 1:6
add("D rail-SCARA", "J2 elbow (vertical axis)", "1.5 kg, 180 deg in 1.2 s", tau_j2, cap_j2, "move",
    "NEMA 23 mounted at J1 (keeps J1 inertia low), belt up the upper arm 1:6")

plate_tot = PLATE_MASS + PARTS_ON_PLATE
I_W = (plate_tot * PLATE_CG_FROM_GRIP ** 2 + PLATE_MASS * (0.355 ** 2 + 0.3465 ** 2) / 12)
alpha_w = 4 * (pi / 2) / 0.8 ** 2           # 90 deg in 0.8 s
tau_w = I_W * alpha_w + 0.1
cap_w = NEMA17_HOLD * PULLOUT_FRACTION * 4 * ETA_BELT_STAGE   # belt 1:4
add("D rail-SCARA", "W wrist yaw", "H2S plate + parts, 90 deg in 0.8 s", tau_w, cap_w, "move",
    "NEMA 17 closed loop + belt 1:4")

# Z column: carries everything above it. Ball screw SFU1605 (5 mm lead) + power-off brake.
m_j1_drive, m_j2_motor, m_zcar = 1.8, 1.0, 0.6
m_z = PAYLOAD + m_wrist + m_fore + m_elbow + m_upper + m_j1_drive + m_j2_motor + m_zcar
F_z = m_z * (G + 1.5)                       # 1.5 m/s^2 up
tau_z = F_z * 0.005 / (2 * pi * 0.90) + 0.10   # + screw/bearing drag (ASSUMED)
cap_z = NEMA23_HOLD * PULLOUT_FRACTION
add("D rail-SCARA", "Z lift (ball screw 5 mm lead)", f"{m_z:.2f} kg moving up at 1.5 m/s^2",
    tau_z, cap_z, "move", "NEMA 23 closed loop + SFU1605 + 24 V power-off brake (screw back-drives)")
tau_z_hold = m_z * G * 0.005 / (2 * pi)     # what the brake must hold (no efficiency credit)
add("D rail-SCARA", "Z lift", "power off: brake holds, motor 0 %", tau_z_hold, 1.0, "hold",
    "vs a 1.0 N*m class NEMA 23 brake (price/rating to verify)")

# X rail: moves the whole column + arm horizontally
m_x = m_z + 1.8 + 1.2 + 1.3 + 1.0 + 0.5     # column 4040 1.1 m, Z rails+screw, Z motor+brake, carriage, chain
F_x = m_x * 1.0 + 0.01 * m_x * G + 5.0       # 1 m/s^2 + rail friction + cable chain drag (ASSUMED)
tau_x = F_x * (20 * 0.005 / (2 * pi))        # HTD 5M 20-tooth pulley
add("D rail-SCARA", "X rail (belt)", f"{m_x:.1f} kg at 1 m/s^2", tau_x,
    NEMA23_HOLD * PULLOUT_FRACTION, "move", "NEMA 23 closed loop + HTD 5M belt on HGR20 rail")

# bending moment the SCARA puts into J1 bearings and the column (gravity, arm stretched)
M_j1 = G * (PAYLOAD * R_PAY + m_wrist * (L1 + L2) + m_fore * (L1 + L2 / 2) + m_elbow * L1
            + m_upper * L1 / 2)

# column + link compliance (first pass): 4040 extrusion, Ix ~ 7e-8 m^4 (ASSUMED, check profile sheet)
E_AL, I_4040 = 69e9, 7e-8
def tool_drop(h):
    theta_c = M_j1 * h / (E_AL * I_4040)
    return theta_c * R_PAY * 1000          # mm vertical drop at the tool from column tilt

# =====================================================================================
# C: cartesian X rail + Z column + telescoping Y fork (0.45 m into the printer)
# =====================================================================================
M_y_carriage = G * (PAYLOAD * 0.45 + 1.0 * 0.25)

# ---------- print ----------
print("# FarmHand robot — Phase 1 torque pass (generated by `design/phase1_torque_pass.py`)\n")
print("Rules: hold ≤ 50 % of rating, move ≤ 70 %. Stepper capacity = holding torque × "
      f"{PULLOUT_FRACTION:.0%} (ASSUMED 24 V pull-out at working speed) × ratio × efficiency.\n")
print(f"Inputs: payload {PAYLOAD:.1f} kg (1.2 kg spool + 0.3 kg tool); H2S plate steel "
      f"{PLATE_MASS*1000:.0f} g (computed, weigh it) + parts {PARTS_ON_PLATE} kg (assumed).\n")
print("| Architecture | Joint | Case | Need (N·m) | Capacity (N·m) | % | Rule | Verdict | Drive |")
print("|---|---|---|---|---|---|---|---|---|")
for a, j, c, need, cap, p, kind, v, note in rows:
    lim = "≤50 %" if kind == "hold" else "≤70 %"
    print(f"| {a} | {j} | {c} | {need:.2f} | {cap:.1f} | {p:.0f} % | {kind} {lim} | {v} | {note} |")
print()
print(f"- D: J1 inertia at full stretch {I_J1:.3f} kg·m², α {alpha_j1:.1f} rad/s²; "
      f"J2 inertia {I_J2:.3f} kg·m²; wrist inertia with plate {I_W:.3f} kg·m².")
print(f"- D: gravity bending moment into the J1 bearing and column: **{M_j1:.1f} N·m** "
      "(carried by a bearing pair, never by a motor).")
print(f"- D: column tilt drop at the tool (4040, assumed Ix): {tool_drop(0.35):.1f} mm at plate "
      f"height (0.35 m), {tool_drop(1.0):.1f} mm at AMS height (1.0 m). Static and repeatable: "
      "calibrate per payload, stiffen column in Phase 2.")
print(f"- C: cantilever moment on the telescoping Y carriage {M_y_carriage:.1f} N·m at 0.45 m extension.")
print(f"- Scale check from the brief: 1.2 kg held 0.5 m out = {SPOOL*G*0.5:.1f} N·m = "
      f"{SPOOL*0.5*100:.0f} kg·cm ≈ {SPOOL*0.5*100/1.8:.0f} SG90s at stall.")

# ---------- architecture scoring (1-5, weights sum 20) ----------
crit = [("Payload at reach / gravity load on motors", 3), ("Stiffness + accuracy at the tool", 2),
        ("Straight entry through the H2S door", 3), ("Footprint / clutter", 1),
        ("Phase-1 cost", 2), ("Build difficulty (axes, parts)", 2),
        ("Safety (falls, pinch, force limit)", 2), ("Serviceability", 1),
        ("Job coverage v1+v2", 3), ("Look", 1)]
scores = {
    "A fixed 6-axis": [1, 2, 2, 4, 2, 2, 2, 2, 4, 4],
    "B 6-axis on rail": [3, 3, 4, 3, 2, 1, 2, 2, 5, 4],
    "C cartesian + telescoping Y": [4, 3, 4, 2, 4, 3, 3, 3, 3, 2],
    "D rail-SCARA": [5, 4, 5, 3, 4, 4, 4, 4, 4, 4],
    "E add-ons + small arm": [2, 3, 3, 5, 5, 4, 5, 3, 1, 2],
}
print("\n## Architecture score (1 = bad, 5 = best)\n")
print("| Criterion | Weight | " + " | ".join(scores) + " |")
print("|---|---|" + "---|" * len(scores))
for i, (c, w) in enumerate(crit):
    print(f"| {c} | {w} | " + " | ".join(str(s[i]) for s in scores.values()) + " |")
wsum = sum(w for _, w in crit)
tot = {k: sum(s[i] * crit[i][1] for i in range(len(crit))) / wsum for k, s in scores.items()}
print("| **Weighted total (/5)** | | " + " | ".join(f"**{v:.2f}**" for v in tot.values()) + " |")

# =====================================================================================
# LEAN variant (docs/BOM.md): NEMA 17 + TMC2209 everywhere, GT2 belts, T8x2 self-locking Z
# =====================================================================================
cap17 = NEMA17_HOLD * PULLOUT_FRACTION
lean = []
a1 = 4 * pi / 2.2 ** 2                                  # J1 180 deg in 2.2 s
lean.append(("J1 (GT2 1:16)", I_J1 * a1 + 0.5, cap17 * 16 * ETA_BELT_STAGE ** 2))
a2 = 4 * pi / 1.6 ** 2                                  # J2 180 deg in 1.6 s
lean.append(("J2 (GT2 1:8)", I_J2 * a2 + 0.3, cap17 * 8 * ETA_BELT_STAGE ** 2))
lean.append(("W (GT2 1:4)", tau_w, cap17 * 4 * ETA_BELT_STAGE))
m_zl = m_z - 1.0 - 1.2 + 0.6                            # NEMA 17s instead of NEMA 23s
lead_eta = 0.30                                         # T8x2 trapezoid screw, ASSUMED
lean.append(("Z (T8x2 lead screw)", m_zl * (G + 1.0) * 0.002 / (2 * pi * lead_eta) + 0.05, cap17))
m_xl = m_zl + 3.5
lean.append(("X (GT2 20T, 0.5 m/s^2)", (m_xl * 0.5 + 0.02 * m_xl * G + 5.0) * 0.00637, cap17))
lead_angle = __import__("math").degrees(__import__("math").atan(2 / (pi * 8)))
print("\n## Lean variant (docs/BOM.md: NEMA 17 + TMC2209, GT2 belts, T8x2 Z)\n")
print("| Joint | Need (N·m) | Capacity (N·m) | % | ≤70 % |")
print("|---|---|---|---|---|")
for j, need, cap in lean:
    print(f"| {j} | {need:.2f} | {cap:.2f} | {pct(need, cap):.0f} % | {rule(pct(need, cap), MOVE_MAX)} |")
print(f"\nT8x2 lead angle {lead_angle:.1f}° < friction angle ~8.5° (μ≈0.15): self-locking, Z holds with power off (verify on the bench).")
