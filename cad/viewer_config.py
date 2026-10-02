"""Write the assembly-viewer config for cad/out/asm/*.stl (placed in assembly frame, so no transforms)."""
import json, os
D = os.path.join(os.path.dirname(__file__), "out", "asm")
G = {"frame": "Frame + lift — bought extrusion, rails, screw", "arm": "Printed arm structure",
     "hand": "Printed hand + tools", "drive": "Bought motors, bearings, pulleys", "grip": "Bought hand parts"}
C = {"frame": "#8a94a6", "arm": "#2f7fd1", "hand": "#e0782d", "drive": "#3a3f47", "grip": "#c9a227"}
# id: (label, group, step, explode, note)
P = {
 "x_beam": ("X rail beam", "frame", 1, [0, 0, -1.5], "2040 V-slot, 1.5 m along the table front. The whole robot rides on it so it can park square in front of either printer — no long reach needed."),
 "x_motor": ("X motor", "drive", 1, [1.5, 0, -1], "NEMA 17 + GT2 20T pulley. Belt moves the carriage; an AprilTag at each printer re-references X so belt stretch never adds up."),
 "x_plate": ("X carriage", "frame", 1, [0, 0, -1], "Gantry plate on 4 V-wheels. The Z column bolts to it."),
 "z_column": ("Z column", "frame", 2, [0, -1.5, 0], "2040 V-slot, 1 m tall. The only part of the robot that fights gravity is what slides up this."),
 "z_screw": ("Lead screw T8×2", "frame", 2, [0, -2.5, 0], "2 mm per turn = self-locking: thread friction beats the weight, so the arm cannot fall when power is cut. That is why there is no brake."),
 "z_motor": ("Z motor", "drive", 2, [0, -2, -1.5], "NEMA 17 turning the lead screw. Needs only 36 % of its torque to lift the whole arm + 1.5 kg."),
 "z_motor_mount": ("Z motor mount", "arm", 2, [0, -2, -1], "Printed bracket, takes the screw thrust. Bolts to the column with M5 T-nuts."),
 "z_nut": ("Brass nut", "frame", 3, [0, -2, 0], "Rides the lead screw; bolted to the Z plate so turning the screw lifts the carriage."),
 "z_plate": ("Z carriage plate", "frame", 3, [0, -1.5, 0], "Bought gantry plate on V-wheels around the column. The shoulder housing bolts flat to it with 4 × M5."),
 "shoulder_housing": ("Shoulder housing", "arm", 3, [0, -0.8, 0], "Holds the two J1 bearings 60 mm apart — that spacing turns the arm's 14.4 N·m moment into ~240 N per bearing, easy for 6806s. Ribs carry it back to the plate."),
 "j1_motor": ("J1 motor", "drive", 3, [-1, -1, 1], "NEMA 17 on the deck, shaft down. Two GT2 1:4 stages under the deck give 1:16 — 60 % of capacity for a 180° swing in 2.2 s."),
 "j1_brg_bottom": ("J1 bearing low", "drive", 3, [0, 0, -1.2], "6806 (30×42×7) pressed in the bottom of the tower."),
 "j1_brg_top": ("J1 bearing top", "drive", 3, [0, 0, 1.2], "6806 in the top of the tower. The upper-arm spigot runs through both."),
 "j1_pulley_mid": ("J1 intermediate", "drive", 3, [0, -1, -1.5], "64T + 16T on an 8 mm shaft in two 608s: the middle of the 1:16 reduction."),
 "j1_pulley_out": ("J1 output pulley", "drive", 4, [0, 0, -2], "64T clamped on the bottom of the spigot (clamp hub, no set screw — set screws loosened on PAROL6)."),
 "upper_arm_root": ("Upper arm — root", "arm", 4, [0, 0, 1], "J1 spigot + J2 motor seat + the first 1:4 stage. Hollow so cables go down the middle of J1."),
 "upper_arm_link": ("Upper arm — link", "arm", 4, [0.6, 0, 1], "Split at x = 120 so each half fits the H2S bed; 4 × M4 through the flanges. Open underside gets a snap-on cover over the belt."),
 "j2_motor": ("J2 motor", "drive", 4, [-0.5, 0, 2], "Sits behind J1, not at the elbow, so J1 doesn't have to swing its mass at full reach."),
 "j2_brg_bottom": ("Elbow bearing low", "drive", 5, [0, 0, -1], "6805 (25×37×7)."),
 "j2_brg_top": ("Elbow bearing top", "drive", 5, [0, 0, 1.6], "6805. Forearm spigot runs up through both."),
 "forearm": ("Forearm", "arm", 5, [0.5, 0, -1], "Hangs under the upper arm so the hand reaches low into the printers. Belt to the wrist runs inside."),
 "w_motor": ("Wrist motor", "drive", 5, [-0.5, 0, -2], "NEMA 17 behind the elbow (balances the forearm), 1:4 belt to the wrist."),
 "w_brg_bottom": ("Wrist bearing low", "drive", 6, [0, 0, -1.2], "6704 (20×27×4)."),
 "w_brg_top": ("Wrist bearing top", "drive", 6, [0, 0, 1.2], "6704."),
 "wrist_flange": ("Quick-change flange", "hand", 6, [0, 0, -0.6], "Three V-grooves underneath. Three steel balls on the hand drop into them: one exact position every time (~40 µm, Jubilee pattern). Magnets only pull it together; the balls carry the load."),
 "ball_0": ("Steel ball", "grip", 7, [0, 0, -1.2], "Ø10 hardened ball, pressed into the hand. Sits 2.8 mm proud so the faces never touch — only the 6 ball/groove contacts do."),
 "ball_1": ("Steel ball", "grip", 7, [0, 0, -1.2], "Kinematic coupling ball (2 of 3)."),
 "ball_2": ("Steel ball", "grip", 7, [0, 0, -1.2], "Kinematic coupling ball (3 of 3)."),
 "hand_body": ("Hand body", "hand", 7, [0, 0, -1.6], "Holds the gripper servo, jaw rail, the stylus barrel (right end) and the door hook (left end). Camera window on the side."),
 "servo": ("Gripper servo", "grip", 7, [0, 1.8, -1.6], "Feetech STS3215. Reports its load, so the robot knows how hard it is squeezing."),
 "mgn9_rail": ("Jaw rail", "grip", 8, [0, 0, -2.2], "MGN9. Both jaws on one rail, driven opposite ways: the part always ends up centred."),
 "mgn9_car_l": ("Jaw carriage", "grip", 8, [-0.6, 0, -2.4], "MGN9 carriage, left jaw."),
 "mgn9_car_r": ("Jaw carriage", "grip", 8, [0.6, 0, -2.4], "MGN9 carriage, right jaw."),
 "jaw_left": ("Jaw", "hand", 8, [-1.2, 0, -2.6], "Rigid core + slot for a 2 mm steel 'nail' at the tip (fin-ray tips lose force on edges and thin plates)."),
 "jaw_right": ("Jaw", "hand", 8, [1.2, 0, -2.6], "Same STL as the left jaw, turned 180°."),
 "finray_pad": ("Fin-ray pad", "hand", 8, [2.2, 0, -2.6], "TPU. Ribs fold toward the object when squeezed, so the pad wraps odd shapes instead of pushing them away."),
 "plate_shoe": ("Plate shoe", "hand", 9, [0, 0, 1], "Clamps on the front notch of every build plate. The robot always grabs this tab, never the bare plate."),
 "upper_arm_cover_root": ("Upper-arm cover", "arm", 4, [0, 0, -1.2], "Screwed + glued on: turns the U-channel into a closed box (sag 22.8 → 0.44 mm with the tubes)."),
 "upper_arm_cover_link": ("Upper-arm cover", "arm", 4, [0.4, 0, -1.2], "Second half of the closing cover."),
 "forearm_cover": ("Forearm cover", "arm", 5, [0.4, 0, -1.6], "Closes the forearm box; unscrew it to reach the wrist belt."),
 "ua_tube_top": ("Spine tube", "frame", 4, [0, -1.5, 0.6], "Aluminium 25×25×2. Two stacked tubes are the real beam; the print just holds them and the bearings."),
 "ua_tube_bot": ("Spine tube", "frame", 4, [0, -1.5, 0.3], "Second 25×25 tube. Spacing the two apart vertically is what multiplies the stiffness."),
 "fa_tube": ("Forearm spine", "frame", 5, [0, -1.5, 0], "Aluminium 20×20×1.5 inside the forearm."),
}
STEPS = [[1, "X rail", "Beam on the table front, X carriage on its wheels, X motor + belt."],
 [2, "Z column", "Column on the X carriage, lead screw + Z motor at the bottom."],
 [3, "Shoulder", "Z plate + nut, then the shoulder housing; press the two 6806s, J1 motor + intermediate shaft."],
 [4, "Upper arm", "Spigot down through the bearings, clamp the 64T pulley under the deck; bolt the link to the root; J2 motor on top."],
 [5, "Forearm", "Elbow bearings, forearm spigot up through them; wrist motor underneath."],
 [6, "Wrist", "Wrist bearings and the quick-change flange."],
 [7, "Hand", "Press the 3 balls, drop in the servo, offer the hand up to the flange (magnets pull it home)."],
 [8, "Jaws", "MGN9 rail, carriages, jaws, TPU pads."],
 [9, "Plates", "Clamp a shoe on every build plate."]]
# ---------- pose: the plate-grip moment of the H2S plate swap (from sim/paths.py, rail stop X = 560) ----------
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "sim"))
import paths as SIMP  # noqa: E402
X_STOP = 600.0
ZS = SIMP.Z_PLATE - SIMP.GRIP_DZ + 3
T1, T2 = SIMP.ik(X_STOP, SIMP.PLATE["cx"], SIMP.PLATE["front_y"] - 14, +1)
PHI1, PHI12 = 90 - T1, 90 - (T1 + T2)
DZ = ZS - 480.0                                     # CAD shoulder sits 480 mm above the table
L1, L2 = 300.0, 250.0
CARRIAGE = {"z_plate", "z_nut", "shoulder_housing", "j1_motor", "j1_brg_bottom", "j1_brg_top", "j1_pulley_mid", "j1_pulley_out"}
UPPER = {"upper_arm_root", "upper_arm_link", "upper_arm_cover_root", "upper_arm_cover_link", "ua_tube_top", "ua_tube_bot",
         "j2_motor", "j2_brg_bottom", "j2_brg_top"}
FORE = {"forearm", "forearm_cover", "fa_tube", "w_motor", "w_brg_bottom", "w_brg_top"}
HANDG = {"wrist_flange", "hand_body", "ball_0", "ball_1", "ball_2", "servo", "mgn9_rail", "mgn9_car_l", "mgn9_car_r",
         "jaw_left", "jaw_right", "finray_pad", "plate_shoe", "h2s_plate"}


def pose(pid):
    t = []
    if pid in HANDG:
        t += [{"t": [-(L1 + L2), 0, 0]}, {"rz": 0.0 - PHI12}, {"t": [L1 + L2, 0, 0]}]
    if pid in HANDG | FORE:
        t += [{"t": [-L1, 0, 0]}, {"rz": -T2}, {"t": [L1, 0, 0]}]
    if pid in HANDG | FORE | UPPER:
        t += [{"rz": PHI1}]
    if pid in HANDG | FORE | UPPER | CARRIAGE:
        t += [{"t": [0, 0, DZ]}]
    return t + [{"scale": 0.5}]


def W(xw, yw, zw):                                   # world (sim/paths.py) -> CAD frame with the robot at X_STOP
    return [xw - X_STOP, yw, zw - 480.0]


def prim(pid, label, size, centre, note, rz=None, color="#c9ced6"):
    tr = ([{"rz": rz}] if rz is not None else []) + [{"t": centre}, {"scale": 0.5}]
    return {"id": pid, "label": label, "primitive": {"type": "box", "size": size}, "transform": tr, "color": color,
            "group": "station", "step": 10, "explode": [0, 0, 0], "note": note}


F, H = SIMP.FACE, SIMP.H2S
hx0, hx1 = SIMP.H2S_X0, SIMP.H2S_X1
cx = (hx0 + hx1) / 2
ex0, ex1 = SIMP.ENDER_X0, SIMP.ENDER_X1
import math  # noqa: E402
dphi = 170.0
dux, duy = math.cos(math.radians(dphi)), -math.sin(math.radians(dphi))
STATION = [
    prim("table", "Table (assumed 1500×750)", [1500, 750, 20], W(600, 235, -10), "ASSUMED size until measured.", color="#e6dccb"),
    prim("h2s_left", "H2S side", [15, H["d"], H["h"]], W(hx0 + 7, F + H["d"] / 2, H["h"] / 2), "Bambu H2S envelope (492×514×626, vendor)."),
    prim("h2s_right", "H2S side", [15, H["d"], H["h"]], W(hx1 - 7, F + H["d"] / 2, H["h"] / 2), "H2S right side."),
    prim("h2s_back", "H2S back", [H["w"], 15, H["h"]], W(cx, F + H["d"] - 7, H["h"] / 2), "H2S back."),
    prim("h2s_top", "H2S top", [H["w"], H["d"], 15], W(cx, F + H["d"] / 2, H["h"] - 7), "H2S top glass."),
    prim("ams", "AMS 2 Pro", [372, 280, 226], W(cx, F + 230, H["h"] + 113), "AMS 2 Pro on top (372×280×226). v2 spool loading reaches up here."),
    prim("h2s_header", "H2S front header", [H["w"], 15, H["h"] - 560], W(cx, F + 7, (560 + H["h"]) / 2), "Above the door: the 5-inch touchscreen is at the top-left of the front."),
    prim("h2s_bed", "H2S bed (lowered)", [340, 400, 38], W(cx, F + 64 + 200, SIMP.Z_PLATE - 21), "Bed commanded down to the hand-off height (gcode_line)."),
    prim("h2s_door", "H2S door (open 170°)", [SIMP.DOOR_W, 12, 520], W(hx0 + dux * SIMP.DOOR_W / 2, F + duy * SIMP.DOOR_W / 2, 300),
         "Opened by pulling the handle to 40°, then pushing the inside face to 170° (D246).", rz=-dphi, color="#a9c6e8"),
    prim("ender_base", "Ender base", [ENDER_W := ex1 - ex0, 340, 80], W((ex0 + ex1) / 2, F + 230, 40), "Ender 3 S1 Pro envelope (assumed)."),
    prim("ender_up_l", "Ender upright", [40, 40, 625], W(ex0 + 20, F + 220, 312), "Ender frame."),
    prim("ender_up_r", "Ender upright", [40, 40, 625], W(ex1 - 20, F + 220, 312), "Ender frame."),
    prim("ender_top", "Ender top bar", [ENDER_W, 40, 40], W((ex0 + ex1) / 2, F + 220, 605), "Ender frame."),
    prim("ender_bed", "Ender bed (slung forward)", [235, 235, 8], W((ex0 + ex1) / 2, F - 10 + 117, 96), "Bed brought forward by OctoPrint for the sheet swap."),
]
PLATE_PART = {"id": "h2s_plate", "label": "H2S build plate", "primitive": {"type": "box", "size": [355, 346.5, 1.0]},
              "transform": [{"t": [L1 + L2, 28 + 173.25, -134]}] + pose("h2s_plate"), "color": "#3d4a5c", "group": "hand",
              "step": 9, "explode": [0, 0, 0],
              "note": "Held by its shoe at the front edge, just peeled off the magnets. Next: pulled straight out, 48 mm clear of everything (sim/PATHS_REPORT.md)."}
G["station"] = "Station — printers, door, table (assumed sizes, ghost shapes)"

cfg = {"title": "FarmHand rail-SCARA v1", "home": {"yaw": -0.45, "pitch": 0.42}, "explode_scale": 20, "subtitle": "posed mid plate-swap inside the H2S · 1:2 scale · tap a part", "groups": G, "steps": STEPS,
       "parts": [{"id": k, "label": v[0], "stl": f"{k}.stl", "color": C[v[1]], "group": v[1], "step": v[2],
                  "explode": v[3], "note": v[4], "transform": pose(k)} for k, v in P.items()] + [PLATE_PART] + STATION}
missing = set(os.path.splitext(f)[0] for f in os.listdir(D) if f.endswith(".stl")) - set(P) - {"fit_coupon"}
assert not missing, missing
json.dump(cfg, open(os.path.join(D, "assembly.json"), "w"), indent=1)
print(len(P), "parts")
