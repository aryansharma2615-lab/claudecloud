"""FarmHand rail-SCARA v1 — single source of truth for every dimension (mm).

ASSUMED values wait on Shawarma's station measurements (ARCHITECTURE_ROBOT.md questions).
Print fits are for the Bambu H2S (bearing seats tuned for it); re-tune SEAT_CLR for the Ender.
"""

# ---------------- station (ASSUMED until measured) ----------------
TABLE = dict(w=1500, d=750, h=750)
H2S = dict(w=492, d=514, h=626)          # vendor exterior, orientation unconfirmed
ENDER = dict(w=455, d=490, h=625)
PRINTER_GAP = 100
FRONT_STRIP = TABLE["d"] - H2S["d"]      # 236 mm free in front of the H2S for the rail

# ---------------- kinematics (from design/phase1_torque_pass.py) ----------------
L1 = 300.0      # J1 -> J2 (upper arm)
L2 = 250.0      # J2 -> wrist (forearm)
X_TRAVEL = 1300.0
Z_TRAVEL = 900.0

# ---------------- bought parts ----------------
B6806 = (30.0, 42.0, 7.0)   # J1 bearing pair (ID, OD, width)
B6805 = (25.0, 37.0, 7.0)   # J2 bearing pair
B6704 = (20.0, 27.0, 4.0)   # wrist bearing pair
B608 = (8.0, 22.0, 7.0)     # idler / intermediate shafts
NEMA17 = dict(side=42.3, holes=31.0, pilot=22.5, shaft=5.0, len=48.0)
STS3215 = dict(l=45.2, w=24.7, h=35.0)
MGN9 = dict(rail_w=9.0, rail_h=6.5, car_w=20.0, car_l=29.7, car_h=10.0)
BALL = 10.0                 # hardened balls of the kinematic flange
GT2_PD = {16: 10.19, 20: 12.73, 40: 25.46, 64: 40.74, 80: 50.93}  # pitch diameters

# ---------------- print rules (sp-print-dfm defaults, PETG-CF / ASA on the H2S) ----------------
WALL = 3.2                  # min wall (4 perimeters @ 0.4)
SEAT_CLR = 0.15             # bearing OD seat: bore = OD + SEAT_CLR (light press, H2S)
SPIGOT_CLR = -0.05          # spigot into bearing ID: diameter = ID + SPIGOT_CLR (snug)
M3_CLR, M3_INSERT, M5_CLR = 3.4, 4.0, 5.5
BEAM_W, BEAM_H = 50.0, 36.0  # arm beam section (hollow box, cables + belt inside)

BEDS = {"Ender 3 S1 Pro": (220, 220, 270), "Bambu H2S": (340, 320, 340)}
