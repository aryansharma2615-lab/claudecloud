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
cfg = {"title": "FarmHand rail-SCARA v1", "explode_scale": 20, "subtitle": "37 parts · shown at 1:2 scale (viewer far-clip is 2 m) · tap a part", "groups": G, "steps": STEPS,
       "parts": [{"id": k, "label": v[0], "stl": f"{k}.stl", "color": C[v[1]], "group": v[1], "step": v[2],
                  "explode": v[3], "note": v[4], "transform": [{"scale": 0.5}]} for k, v in P.items()]}
missing = set(os.path.splitext(f)[0] for f in os.listdir(D) if f.endswith(".stl")) - set(P)
assert not missing, missing
json.dump(cfg, open(os.path.join(D, "assembly.json"), "w"), indent=1)
print(len(P), "parts")
